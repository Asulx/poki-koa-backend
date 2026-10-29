"""
Pruebas de la aplicación 'operacion'.

Cubre turnos, asignaciones, "mis cunas", reportes, auditoría automática y
las reglas de permisos de cada endpoint.
"""

from datetime import time

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from cunas.models import Alerta, Bebe, Cuna, Medicamento, MedicamentoCatalogo
from usuarios.models import PerfilUsuario

from .models import AsignacionTurno, RegistroActividad, Turno
from .reportes import (
    calcular_resumen,
    distribucion_cunas,
    distribucion_medicamentos,
    personal_por_turno,
    serie_actividad,
)

Usuario = get_user_model()


def crear_usuario(username="tester", rol=PerfilUsuario.ROL_ENFERMERIA):
    """Crea un usuario con perfil y contraseña de prueba."""
    usuario = Usuario.objects.create_user(
        username=username,
        password="ClaveSegura123",
        first_name="Test",
        last_name="User",
    )
    perfil = usuario.perfil
    perfil.rol = rol
    perfil.save(update_fields=["rol"])
    return usuario


def crear_bebe(identificador="BEB-0001", activo=True):
    """Crea un paciente mínimo válido para las pruebas."""
    return Bebe.objects.create(
        identificador=identificador,
        nombre_completo="Sofía García",
        edad_meses=0,
        sexo="F",
        activo=activo,
    )


class TurnoModeloTests(TestCase):
    """Reglas de dominio del catálogo de turnos."""

    def test_duracion_de_un_turno_diurno(self):
        """Un turno 08:00-16:00 dura 8 horas."""
        turno = Turno(nombre="Mañana", hora_inicio=time(8, 0), hora_fin=time(16, 0))
        self.assertEqual(turno.duracion_horas, 8.0)

    def test_duracion_de_un_turno_que_cruza_la_medianoche(self):
        """Un turno 20:00-08:00 dura 12 horas."""
        turno = Turno(nombre="Noche", hora_inicio=time(20, 0), hora_fin=time(8, 0))
        self.assertEqual(turno.duracion_horas, 12.0)

    def test_horas_iguales_son_invalidas(self):
        """Inicio y fin iguales no representan un turno real."""
        turno = Turno(nombre="Roto", hora_inicio=time(8, 0), hora_fin=time(8, 0))

        with self.assertRaises(ValidationError):
            turno.clean()


class TurnoAPITests(APITestCase):
    """Contrato y permisos de ``/api/turnos/``."""

    def setUp(self):
        cache.clear()
        self.admin = crear_usuario("admin", PerfilUsuario.ROL_ADMINISTRADOR)
        self.enfermera = crear_usuario("enfermera", PerfilUsuario.ROL_ENFERMERIA)

    def _autenticar(self, usuario):
        token, _ = Token.objects.get_or_create(user=usuario)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_lectura_requiere_autenticacion(self):
        """Sin token, el catálogo no es público."""
        self.assertEqual(self.client.get(reverse("turno-list")).status_code, 401)

    def test_administrador_crea_turno(self):
        """El administrador puede crear turnos."""
        self._autenticar(self.admin)

        respuesta = self.client.post(
            reverse("turno-list"),
            {"nombre": "Mañana", "hora_inicio": "08:00", "hora_fin": "16:00"},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.data["duracion_horas"], 8.0)

    def test_enfermeria_no_crea_turnos(self):
        """La escritura del catálogo es exclusiva del administrador."""
        self._autenticar(self.enfermera)

        respuesta = self.client.post(
            reverse("turno-list"),
            {"nombre": "Mañana", "hora_inicio": "08:00", "hora_fin": "16:00"},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 403)

    def test_turno_actual_devuelve_el_turno_vigente(self):
        """``/api/turnos/actual/`` responde con el turno que cubre la hora."""
        self._autenticar(self.enfermera)
        ahora = timezone.localtime().time()
        Turno.objects.create(
            nombre="Todo el día",
            hora_inicio=time(0, 0),
            hora_fin=time(23, 59, 59),
        )

        respuesta = self.client.get(reverse("turno-actual"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertIsNotNone(respuesta.data["turno"], msg=f"Hora evaluada: {ahora}")


class AsignacionTurnoTests(APITestCase):
    """Reglas de asignación de personal a turnos y cunas."""

    def setUp(self):
        cache.clear()
        self.admin = crear_usuario("admin", PerfilUsuario.ROL_ADMINISTRADOR)
        self.enfermera = crear_usuario("enfermera", PerfilUsuario.ROL_ENFERMERIA)
        self.turno = Turno.objects.create(
            nombre="Mañana", hora_inicio=time(8, 0), hora_fin=time(16, 0)
        )
        self.cuna = Cuna.objects.create(identificador="C01")
        token, _ = Token.objects.get_or_create(user=self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def _payload(self, **extra):
        datos = {
            "usuario": self.enfermera.pk,
            "turno": self.turno.pk,
            "cuna": self.cuna.pk,
            "fecha": timezone.localdate().isoformat(),
        }
        datos.update(extra)
        return datos

    def test_crea_asignacion_y_registra_autor(self):
        """El autor de la asignación se toma del token, no del cuerpo."""
        respuesta = self.client.post(
            reverse("asignacionturno-list"), self._payload(), format="json"
        )

        self.assertEqual(respuesta.status_code, 201)
        asignacion = AsignacionTurno.objects.get()
        self.assertEqual(asignacion.creado_por, self.admin)
        self.assertEqual(respuesta.data["usuario_nombre"], "Test User")

    def test_no_permite_asignaciones_duplicadas(self):
        """Dos asignaciones idénticas se rechazan con 400."""
        self.client.post(reverse("asignacionturno-list"), self._payload(), format="json")

        respuesta = self.client.post(
            reverse("asignacionturno-list"), self._payload(), format="json"
        )

        self.assertEqual(respuesta.status_code, 400)

    def test_no_permite_dos_personas_en_la_misma_cuna_y_fecha(self):
        """La misma cuna no puede tener dos responsables en turnos distintos."""
        otro_turno = Turno.objects.create(
            nombre="Tarde", hora_inicio=time(16, 0), hora_fin=time(23, 59)
        )
        self.client.post(reverse("asignacionturno-list"), self._payload(), format="json")

        respuesta = self.client.post(
            reverse("asignacionturno-list"),
            self._payload(turno=otro_turno.pk),
            format="json",
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("cuna", respuesta.data)

    def test_enfermeria_no_puede_asignar(self):
        """Solo la jefatura (administrador) asigna turnos."""
        token, _ = Token.objects.get_or_create(user=self.enfermera)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        respuesta = self.client.post(
            reverse("asignacionturno-list"), self._payload(), format="json"
        )

        self.assertEqual(respuesta.status_code, 403)


class MisCunasTests(APITestCase):
    """Contrato de ``/api/mis-cunas/``."""

    def setUp(self):
        cache.clear()
        self.enfermera = crear_usuario("enfermera", PerfilUsuario.ROL_ENFERMERIA)
        token, _ = Token.objects.get_or_create(user=self.enfermera)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        self.turno = Turno.objects.create(
            nombre="Mañana", hora_inicio=time(8, 0), hora_fin=time(16, 0)
        )
        self.bebe = crear_bebe()
        self.cuna = Cuna.objects.create(
            identificador="C01",
            paciente=self.bebe,
            ritmo_cardiaco=140,
            spo2=97,
            temperatura=36.8,
        )

    def test_devuelve_solo_las_cunas_asignadas_hoy(self):
        """El personal ve únicamente sus cunas del día."""
        AsignacionTurno.objects.create(
            usuario=self.enfermera,
            turno=self.turno,
            cuna=self.cuna,
            fecha=timezone.localdate(),
        )
        Cuna.objects.create(identificador="C02")

        respuesta = self.client.get(reverse("mis-cunas"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["total"], 1)
        self.assertEqual(respuesta.data["cunas"][0]["cuna_identificador"], "C01")
        self.assertEqual(respuesta.data["cunas"][0]["paciente_nombre"], "Sofía García")

    def test_sin_asignaciones_devuelve_lista_vacia(self):
        """No tener cunas asignadas no es un error."""
        respuesta = self.client.get(reverse("mis-cunas"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["total"], 0)
        self.assertEqual(respuesta.data["cunas"], [])


class ReportesTests(APITestCase):
    """Contrato de los endpoints de reportes."""

    def setUp(self):
        cache.clear()
        self.admin = crear_usuario("admin", PerfilUsuario.ROL_ADMINISTRADOR)
        token, _ = Token.objects.get_or_create(user=self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        self.bebe = crear_bebe()
        self.cuna = Cuna.objects.create(identificador="C01", paciente=self.bebe)
        Cuna.objects.create(identificador="C02")
        Cuna.objects.create(identificador="C03", en_mantenimiento=True)
        MedicamentoCatalogo.objects.create(
            nombre="Fenobarbital 200 mg",
            principio_activo="Fenobarbital",
            dosis_mg=200,
            stock=3,
        )
        Alerta.objects.create(
            cuna=self.cuna,
            paciente=self.bebe,
            tipo="spo2",
            nivel="Critica",
            mensaje="Desaturación crítica",
            activa=True,
        )

    def test_resumen_calcula_metricas_coherentes(self):
        """Las métricas derivadas respetan las invariantes del servicio."""
        respuesta = self.client.get(reverse("reporte-resumen"))

        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.data
        self.assertEqual(datos["total_cunas"], 3)
        self.assertEqual(datos["cunas_ocupadas"], 1)
        self.assertEqual(datos["cunas_mantenimiento"], 1)
        self.assertEqual(datos["cunas_disponibles"], 1)
        self.assertEqual(
            datos["cunas_disponibles"]
            + datos["cunas_ocupadas"]
            + datos["cunas_mantenimiento"],
            datos["total_cunas"],
        )
        self.assertEqual(datos["alertas_activas"], 1)
        self.assertEqual(datos["alertas_criticas"], 1)
        self.assertEqual(datos["medicamentos_stock_critico"], 1)
        self.assertEqual(datos["pacientes_activos"], 1)

    def test_resumen_requiere_autenticacion(self):
        """Los reportes no son públicos."""
        self.client.credentials()
        self.assertEqual(self.client.get(reverse("reporte-resumen")).status_code, 401)

    def test_serie_rellena_dias_sin_datos(self):
        """La serie siempre devuelve exactamente ``dias`` elementos."""
        respuesta = self.client.get(reverse("reporte-serie"), {"dias": 7})

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.data["serie"]), 7)
        self.assertEqual(respuesta.data["serie"][-1]["fecha"], timezone.localdate().isoformat())

    def test_serie_valida_el_rango(self):
        """Valores fuera de 1..90 se rechazan con 400."""
        self.assertEqual(
            self.client.get(reverse("reporte-serie"), {"dias": 0}).status_code, 400
        )
        self.assertEqual(
            self.client.get(reverse("reporte-serie"), {"dias": 120}).status_code, 400
        )
        self.assertEqual(
            self.client.get(reverse("reporte-serie"), {"dias": "abc"}).status_code, 400
        )

    def test_distribucion_agrupa_por_estado(self):
        """La distribución de cunas y medicamentos es consistente."""
        respuesta = self.client.get(reverse("reporte-distribucion"))

        self.assertEqual(respuesta.status_code, 200)
        cunas = {fila["estado"]: fila["cantidad"] for fila in respuesta.data["cunas"]}
        self.assertEqual(cunas, {"ocupada": 1, "disponible": 1, "mantenimiento": 1})
        self.assertEqual(len(respuesta.data["alertas"]), 1)
        self.assertIn("personal", respuesta.data)

    def test_exportacion_csv(self):
        """El CSV se entrega con BOM y cabecera de descarga."""
        respuesta = self.client.get(reverse("reporte-exportar"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("text/csv", respuesta["Content-Type"])
        self.assertIn("attachment;", respuesta["Content-Disposition"])
        contenido = respuesta.content.decode("utf-8")
        self.assertTrue(contenido.startswith("\ufeff"))
        self.assertIn("total_cunas", contenido)

    def test_funciones_de_reporte_son_puras_y_reutilizables(self):
        """Las funciones del servicio devuelven las mismas cifras que la API."""
        self.assertEqual(calcular_resumen().total_cunas, 3)
        self.assertEqual(len(serie_actividad(3)), 3)
        self.assertEqual(distribucion_cunas()[0]["estado"], "ocupada")
        self.assertEqual(distribucion_medicamentos(), [])
        self.assertEqual(personal_por_turno(), [])


class AuditoriaTests(APITestCase):
    """Verifica que la bitácora capture las acciones reales."""

    def setUp(self):
        cache.clear()
        self.admin = crear_usuario("admin", PerfilUsuario.ROL_ADMINISTRADOR)
        token, _ = Token.objects.get_or_create(user=self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_crear_paciente_registra_el_usuario_responsable(self):
        """La señal de auditoría resuelve el usuario desde la petición."""
        respuesta = self.client.post(
            "/api/bebes/",
            {
                "identificador": "BEB-AUD-1",
                "nombre_completo": "Mateo Rojas",
                "edad_meses": 0,
                "sexo": "M",
            },
            format="json",
        )
        self.assertEqual(respuesta.status_code, 201)

        registro = RegistroActividad.objects.filter(
            entidad="Bebé", entidad_id=str(respuesta.data["id"])
        ).first()

        self.assertIsNotNone(registro)
        self.assertEqual(registro.accion, RegistroActividad.ACCION_CREAR)
        self.assertEqual(registro.usuario, self.admin)

    def test_eliminar_registra_la_accion(self):
        """Eliminar una entidad deja rastro en la bitácora."""
        bebe = crear_bebe("BEB-AUD-2")
        RegistroActividad.objects.all().delete()

        bebe.delete()

        registro = RegistroActividad.objects.get(entidad="Bebé")
        self.assertEqual(registro.accion, RegistroActividad.ACCION_ELIMINAR)

    def test_administrar_medicamento_registra_accion_especifica(self):
        """El cambio a ``Administrado`` uses el verbo ``administrar``."""
        bebe = crear_bebe("BEB-AUD-3")
        medicamento = Medicamento.objects.create(
            paciente=bebe,
            nombre="Vitamina K",
            dosis="1 mg",
            via="IM",
            hora=time(8, 0),
        )
        RegistroActividad.objects.all().delete()

        medicamento.estado = "Administrado"
        medicamento.save(update_fields=["estado"])

        registro = RegistroActividad.objects.get(entidad="Medicamento")
        self.assertEqual(registro.accion, RegistroActividad.ACCION_ADMINISTRAR)

    def test_telemetria_no_genera_ruido_de_auditoria(self):
        """Las muestras de sensores no crean una fila por cada actualización."""
        cuna = Cuna.objects.create(identificador="C-TEL")
        RegistroActividad.objects.all().delete()

        for _ in range(3):
            respuesta = self.client.post(
                f"/api/cunas/{cuna.pk}/telemetria/",
                {
                    "ritmo_cardiaco": 130,
                    "spo2": 98,
                    "temperatura": 36.8,
                    "estado_sueno": "Dormido",
                    "canula_ok": True,
                    "via_iv_activa": False,
                },
                format="json",
            )
            self.assertEqual(respuesta.status_code, 200)

        self.assertEqual(RegistroActividad.objects.count(), 0)

    def test_registros_solo_para_administradores(self):
        """La bitácora global no debe quedar expuesta a todo el personal."""
        enfermera = crear_usuario("enfermera", PerfilUsuario.ROL_ENFERMERIA)
        token, _ = Token.objects.get_or_create(user=enfermera)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        respuesta = self.client.get(reverse("registro-list"))

        self.assertEqual(respuesta.status_code, 403)

    def test_registros_lista_y_filtra(self):
        """El administrador puede filtrar la bitácora por acción."""
        crear_bebe("BEB-AUD-4")

        respuesta = self.client.get(reverse("registro-list"), {"accion": "crear"})

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(all(fila["accion"] == "crear" for fila in respuesta.data))

    def test_registros_resumen_agrupa_por_accion(self):
        """El resumen entrega conteos por acción."""
        crear_bebe("BEB-AUD-5")

        respuesta = self.client.get(reverse("registro-resumen"))

        self.assertEqual(respuesta.status_code, 200)
        acciones = {fila["accion"]: fila["total"] for fila in respuesta.data}
        self.assertIn("crear", acciones)
