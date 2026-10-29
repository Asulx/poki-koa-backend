"""
Pruebas de la aplicación 'usuarios'.

Cubre el ciclo de autenticación por token, la creación automática de
perfiles, los permisos por rol y el comando de usuarios de demostración.
"""

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import PerfilUsuario

Usuario = get_user_model()


def crear_usuario(username="tester", password="ClaveSegura123", rol=PerfilUsuario.ROL_ENFERMERIA):
    """
    Crea un usuario con perfil y contraseña conocidas.

    Parameters
    ----------
    username : str
        Nombre de usuario único.
    password : str
        Contraseña en texto plano (solo para pruebas).
    rol : str
        Rol clínico a asignar al perfil.

    Returns
    -------
    User
        Usuario persistido con su perfil actualizado.
    """
    usuario = Usuario.objects.create_user(
        username=username,
        password=password,
        first_name="Test",
        last_name="User",
    )
    perfil = usuario.perfil
    perfil.rol = rol
    perfil.save(update_fields=["rol"])
    return usuario


class PerfilUsuarioModeloTests(TestCase):
    """Pruebas del modelo ``PerfilUsuario`` y su señal de creación."""

    def test_la_senal_crea_el_perfil_al_registrar_un_usuario(self):
        """Todo usuario nuevo debe tener perfil sin intervención manual."""
        usuario = Usuario.objects.create_user(username="nuevo", password="ClaveSegura123")

        self.assertTrue(PerfilUsuario.objects.filter(usuario=usuario).exists())
        self.assertEqual(usuario.perfil.rol, PerfilUsuario.ROL_ENFERMERIA)

    def test_superusuario_recibe_rol_administrador(self):
        """Un superusuario debe nacer con el rol de mayor privilegio."""
        usuario = Usuario.objects.create_superuser(
            username="root", password="ClaveSegura123", email="root@poki.cl"
        )

        self.assertEqual(usuario.perfil.rol, PerfilUsuario.ROL_ADMINISTRADOR)

    def test_iniciales_y_nombre_completo(self):
        """Las iniciales se calculan con la primera y última palabra."""
        usuario = Usuario.objects.create_user(
            username="ana", password="ClaveSegura123", first_name="Ana", last_name="López"
        )

        self.assertEqual(usuario.perfil.nombre_completo, "Ana López")
        self.assertEqual(usuario.perfil.iniciales, "AL")

    def test_iniciales_con_una_sola_palabra(self):
        """Con un solo nombre se usan sus dos primeras letras."""
        usuario = Usuario.objects.create_user(username="x", password="ClaveSegura123")
        perfil = usuario.perfil
        perfil.usuario.first_name = ""
        perfil.usuario.save(update_fields=["first_name"])

        self.assertEqual(perfil.iniciales, "X")

    def test_es_administrador(self):
        """La propiedad ``es_administrador`` refleja el rol."""
        usuario = crear_usuario(rol=PerfilUsuario.ROL_ADMINISTRADOR)
        self.assertTrue(usuario.perfil.es_administrador)


class AutenticacionTests(APITestCase):
    """Pruebas del contrato ``/api/auth/*``."""

    def setUp(self):
        cache.clear()  # Evita que el throttle de login interfiera entre pruebas.

    def test_login_correcto_entrega_token_y_usuario(self):
        """El login válido devuelve token, usuario y perfil."""
        crear_usuario()

        respuesta = self.client.post(
            reverse("auth-login"),
            {"username": "tester", "password": "ClaveSegura123"},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("token", respuesta.data)
        self.assertEqual(respuesta.data["usuario"]["username"], "tester")
        self.assertEqual(respuesta.data["perfil"]["rol"], PerfilUsuario.ROL_ENFERMERIA)

    def test_login_con_password_incorrecta_no_revela_si_el_usuario_existe(self):
        """El mensaje de error es genérico para evitar enumeración de cuentas."""
        crear_usuario()

        respuesta = self.client.post(
            reverse("auth-login"),
            {"username": "tester", "password": "incorrecta"},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(
            respuesta.data["detail"], "Usuario o contraseña incorrectos."
        )

    def test_login_sin_datos_devuelve_400(self):
        """El serializador exige ambos campos."""
        respuesta = self.client.post(reverse("auth-login"), {}, format="json")

        self.assertEqual(respuesta.status_code, 400)

    def test_login_de_usuario_inactivo_devuelve_400(self):
        """Un usuario desactivado no debe poder iniciar sesión."""
        usuario = crear_usuario()
        usuario.is_active = False
        usuario.save(update_fields=["is_active"])

        respuesta = self.client.post(
            reverse("auth-login"),
            {"username": "tester", "password": "ClaveSegura123"},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 400)

    def test_me_requiere_autenticacion(self):
        """Sin token, ``/api/auth/me/`` responde 401."""
        respuesta = self.client.get(reverse("auth-me"))
        self.assertEqual(respuesta.status_code, 401)

    def test_me_devuelve_el_usuario_autenticado(self):
        """Con token, ``/api/auth/me/`` devuelve usuario y perfil."""
        usuario = crear_usuario()
        token = Token.objects.create(user=usuario)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        respuesta = self.client.get(reverse("auth-me"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["usuario"]["username"], "tester")
        self.assertEqual(respuesta.data["perfil"]["rol"], PerfilUsuario.ROL_ENFERMERIA)

    def test_logout_elimina_el_token(self):
        """El cierre de sesión invalida el token del usuario."""
        usuario = crear_usuario()
        token = Token.objects.create(user=usuario)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        respuesta = self.client.post(reverse("auth-logout"))

        self.assertEqual(respuesta.status_code, 204)
        self.assertFalse(Token.objects.filter(user=usuario).exists())

    def test_logout_es_idempotente_sin_token(self):
        """Sin token, el cierre de sesión exige autenticación."""
        respuesta = self.client.post(reverse("auth-logout"))
        self.assertEqual(respuesta.status_code, 401)


class PersonalPermisosTests(APITestCase):
    """Pruebas de autorización del endpoint ``/api/personal/``."""

    def setUp(self):
        cache.clear()
        self.admin = crear_usuario("admin", rol=PerfilUsuario.ROL_ADMINISTRADOR)
        self.enfermera = crear_usuario("enfermera", rol=PerfilUsuario.ROL_ENFERMERIA)

    def _autenticar(self, usuario):
        token, _ = Token.objects.get_or_create(user=usuario)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_enfermeria_puede_listar_personal(self):
        """La lectura del personal está disponible para el personal clínico."""
        self._autenticar(self.enfermera)

        respuesta = self.client.get(reverse("personal-list"))

        self.assertEqual(respuesta.status_code, 200)

    def test_enfermeria_no_puede_crear_personal(self):
        """Solo administradores pueden dar de alta usuarios."""
        self._autenticar(self.enfermera)

        respuesta = self.client.post(
            reverse("personal-list"),
            {
                "username": "nuevo.user",
                "password": "ClaveSegura123",
                "rol": PerfilUsuario.ROL_MEDICO,
            },
            format="json",
        )

        self.assertEqual(respuesta.status_code, 403)

    def test_administrador_puede_crear_personal(self):
        """El administrador crea usuario, perfil y rol en una sola llamada."""
        self._autenticar(self.admin)

        respuesta = self.client.post(
            reverse("personal-list"),
            {
                "username": "nuevo.user",
                "password": "ClaveSegura123",
                "first_name": "Nuevo",
                "last_name": "User",
                "rol": PerfilUsuario.ROL_MEDICO,
                "turno": "Tarde",
            },
            format="json",
        )

        self.assertEqual(respuesta.status_code, 201)
        creado = Usuario.objects.get(username="nuevo.user")
        self.assertEqual(creado.perfil.rol, PerfilUsuario.ROL_MEDICO)
        self.assertEqual(creado.perfil.turno, "Tarde")

    def test_no_se_puede_desactivar_a_si_mismo(self):
        """El administrador no puede dejar el sistema sin acceso."""
        self._autenticar(self.admin)

        respuesta = self.client.post(
            reverse("personal-desactivar", args=[self.admin.pk])
        )

        self.assertEqual(respuesta.status_code, 400)

    def test_administrador_desactiva_y_reactiva(self):
        """La desactivación es reversible y no borra el historial."""
        self._autenticar(self.admin)

        desactivar = self.client.post(
            reverse("personal-desactivar", args=[self.enfermera.pk])
        )
        self.assertEqual(desactivar.status_code, 200)

        self.enfermera.refresh_from_db()
        self.assertFalse(self.enfermera.is_active)

        activar = self.client.post(reverse("personal-activar", args=[self.enfermera.pk]))
        self.assertEqual(activar.status_code, 200)

        self.enfermera.refresh_from_db()
        self.assertTrue(self.enfermera.is_active)

    def test_filtro_por_rol(self):
        """``?rol=`` acota el listado al rol solicitado."""
        self._autenticar(self.admin)

        respuesta = self.client.get(reverse("personal-list"), {"rol": "administrador"})

        self.assertEqual(respuesta.status_code, 200)
        usernames = [fila["username"] for fila in respuesta.data]
        self.assertIn("admin", usernames)
        self.assertNotIn("enfermera", usernames)


class CrearUsuariosDemoTests(TestCase):
    """Pruebas del comando ``crear_usuarios_demo``."""

    def test_crea_los_tres_usuarios_y_es_idempotente(self):
        """Dos ejecuciones no duplican usuarios ni perfiles."""
        call_command("crear_usuarios_demo", verbosity=0, forzar=True)
        call_command("crear_usuarios_demo", verbosity=0, forzar=True)

        self.assertEqual(Usuario.objects.count(), 3)
        self.assertEqual(PerfilUsuario.objects.count(), 3)
        self.assertTrue(Usuario.objects.get(username="ana.lopez").perfil.es_administrador)

    def test_resetear_claves_cambia_la_password(self):
        """``--resetear-claves`` restablece la contraseña de usuarios existentes."""
        call_command("crear_usuarios_demo", password="PrimeraClave123", verbosity=0, forzar=True)
        call_command(
            "crear_usuarios_demo",
            password="SegundaClave123",
            resetear_claves=True,
            verbosity=0,
            forzar=True,
        )

        usuario = Usuario.objects.get(username="rosa.perez")
        self.assertTrue(usuario.check_password("SegundaClave123"))
