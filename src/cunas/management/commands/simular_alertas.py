"""
Comando de gestión de Django para simular lecturas de signos vitales
y probar el sistema de alertas neonatal en Poki Koa.

Uso:
    # Ejecutar una batería completa de pruebas diagnósticas con todos los casos:
    python src/manage.py simular_alertas --ejecutar-todos

    # Listar los casos de prueba clínicos disponibles:
    python src/manage.py simular_alertas --listar-casos

    # Probar un caso específico en una cuna:
    python src/manage.py simular_alertas --caso bradicardia_critica --cuna C01
    python src/manage.py simular_alertas --caso fiebre --cuna C01
    python src/manage.py simular_alertas --caso canula_desconectada --cuna C01
    python src/manage.py simular_alertas --caso normal --cuna C01

    # Inyectar lecturas personalizadas:
    python src/manage.py simular_alertas --custom --fc 65 --spo2 88 --temp 39.1 --canula-ok false
"""

from typing import Any

from django.core.management.base import BaseCommand

from cunas.alertas import evaluar_signos_vitales, procesar_alertas_cuna
from cunas.models import Alerta, Bebe, Cuna, Medico

CASOS_PRUEBA: dict[str, dict[str, Any]] = {
    "normal": {
        "descripcion": "Signos vitales normales (reposo neonatal estable)",
        "ritmo_cardiaco": 130,
        "spo2": 98,
        "temperatura": 36.8,
        "canula_ok": True,
        "alertas_esperadas": 0,
    },
    "bradicardia_moderada": {
        "descripcion": "Bradicardia leve/moderada (FC 80-99 bpm)",
        "ritmo_cardiaco": 90,
        "spo2": 97,
        "temperatura": 36.7,
        "canula_ok": True,
        "alertas_esperadas": 1,
    },
    "bradicardia_critica": {
        "descripcion": "Bradicardia severa de alto riesgo vital (FC < 80 bpm)",
        "ritmo_cardiaco": 68,
        "spo2": 96,
        "temperatura": 36.6,
        "canula_ok": True,
        "alertas_esperadas": 1,
    },
    "taquicardia_moderada": {
        "descripcion": "Taquicardia moderada (FC 161-180 bpm)",
        "ritmo_cardiaco": 172,
        "spo2": 98,
        "temperatura": 36.8,
        "canula_ok": True,
        "alertas_esperadas": 1,
    },
    "taquicardia_critica": {
        "descripcion": "Taquicardia severa (FC > 180 bpm)",
        "ritmo_cardiaco": 195,
        "spo2": 97,
        "temperatura": 37.1,
        "canula_ok": True,
        "alertas_esperadas": 1,
    },
    "hipoxia_moderada": {
        "descripcion": "Hipoxemia / Saturación de oxígeno baja (SpO2 90-94%)",
        "ritmo_cardiaco": 140,
        "spo2": 92,
        "temperatura": 36.8,
        "canula_ok": True,
        "alertas_esperadas": 1,
    },
    "hipoxia_critica": {
        "descripcion": "Desaturación de oxígeno crítica (SpO2 < 90%)",
        "ritmo_cardiaco": 135,
        "spo2": 85,
        "temperatura": 36.7,
        "canula_ok": True,
        "alertas_esperadas": 1,
    },
    "hipotermia_moderada": {
        "descripcion": "Hipotermia leve (Temp 36.0 - 36.4 °C)",
        "ritmo_cardiaco": 125,
        "spo2": 98,
        "temperatura": 36.2,
        "canula_ok": True,
        "alertas_esperadas": 1,
    },
    "hipotermia_critica": {
        "descripcion": "Hipotermia severa (Temp < 36.0 °C)",
        "ritmo_cardiaco": 115,
        "spo2": 96,
        "temperatura": 35.3,
        "canula_ok": True,
        "alertas_esperadas": 1,
    },
    "fiebre": {
        "descripcion": "Fiebre / hipertermia leve (Temp 37.6 - 38.5 °C)",
        "ritmo_cardiaco": 148,
        "spo2": 97,
        "temperatura": 38.2,
        "canula_ok": True,
        "alertas_esperadas": 1,
    },
    "hipertermia_critica": {
        "descripcion": "Hipertermia crítica (Temp > 38.5 °C)",
        "ritmo_cardiaco": 145,
        "spo2": 96,
        "temperatura": 39.2,
        "canula_ok": True,
        "alertas_esperadas": 1,
    },
    "canula_desconectada": {
        "descripcion": "Desconexión de cánula de oxígeno con leve caída de SpO2",
        "ritmo_cardiaco": 132,
        "spo2": 93,
        "temperatura": 36.8,
        "canula_ok": False,
        "alertas_esperadas": 2,  # canula + hipoxia moderada
    },
    "colapso_multiorganico": {
        "descripcion": "Falla múltiple simultánea (bradicardia crítica + desaturación + hipotermia + cánula)",
        "ritmo_cardiaco": 62,
        "spo2": 82,
        "temperatura": 35.1,
        "canula_ok": False,
        "alertas_esperadas": 4,
    },
}


class Command(BaseCommand):
    help = "Simulador de signos vitales y evaluador de pruebas para el motor de alertas."

    def add_arguments(self, parser):
        parser.add_argument(
            "--cuna",
            type=str,
            default=None,
            help="Identificador o ID de la cuna (ej: 'C01' o '1'). Si no se indica, usa la primera disponible o crea una de prueba.",
        )
        parser.add_argument(
            "--caso",
            type=str,
            choices=list(CASOS_PRUEBA.keys()),
            help="Nombre del caso de prueba predefinido a simular.",
        )
        parser.add_argument(
            "--listar-casos",
            action="store_true",
            help="Muestra todos los casos clínicos predefinidos disponibles.",
        )
        parser.add_argument(
            "--ejecutar-todos",
            action="store_true",
            help="Ejecuta secuencialmente todos los casos de prueba y valida las alertas.",
        )
        parser.add_argument(
            "--custom",
            action="store_true",
            help="Habilita la simulación con valores libres pasados por CLI.",
        )
        parser.add_argument(
            "--fc",
            type=int,
            help="Frecuencia cardíaca en bpm (para modo --custom).",
        )
        parser.add_argument(
            "--spo2",
            type=int,
            help="Saturación de oxígeno SpO2 en %% (para modo --custom).",
        )
        parser.add_argument(
            "--temp",
            type=float,
            help="Temperatura corporal en °C (para modo --custom).",
        )
        parser.add_argument(
            "--canula-ok",
            type=lambda v: v.lower() in ("true", "1", "yes", "si"),
            default=None,
            help="Estado de la cánula: true o false (para modo --custom).",
        )

    def _obtener_o_crear_cuna(self, identificador: str | None) -> Cuna:
        """Obtiene una cuna existente o crea una para pruebas."""
        if identificador:
            cuna = Cuna.objects.filter(identificador=identificador).first()
            if not cuna:
                try:
                    cuna = Cuna.objects.get(pk=int(identificador))
                except (ValueError, Cuna.DoesNotExist):
                    cuna = None

            if not cuna:
                # Crear cuna con el identificador solicitado
                bebe, _ = Bebe.objects.get_or_create(
                    nombre_completo=f"Bebé de prueba ({identificador})",
                    defaults={"edad_meses": 1, "sexo": "M"},
                )
                cuna = Cuna.objects.create(identificador=identificador, paciente=bebe)
                self.stdout.write(
                    self.style.WARNING(
                        f"Se creó una cuna de prueba '{identificador}' asociada al paciente '{bebe.nombre_completo}'."
                    )
                )
            return cuna

        cuna = Cuna.objects.first()
        if not cuna:
            medico, _ = Medico.objects.get_or_create(
                nombre_completo="Dra. Neonatóloga Pruebas", defaults={"turno": "24h"}
            )
            bebe = Bebe.objects.create(
                nombre_completo="Paciente Simulado",
                edad_meses=2,
                sexo="F",
                medico_a_cargo=medico,
            )
            cuna = Cuna.objects.create(
                identificador="C-SIM",
                paciente=bebe,
                ritmo_cardiaco=130,
                spo2=98,
                temperatura=36.8,
                canula_ok=True,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "Base de datos sin cunas: se creó automáticamente la cuna 'C-SIM' con paciente de prueba."
                )
            )
        return cuna

    def handle(self, *args, **options):
        # 1. Listar casos
        if options["listar_casos"]:
            self.stdout.write(self.style.MIGRATE_HEADING("\n=== Casos de Prueba Clínicos Predefinidos ==="))
            for nombre, datos in CASOS_PRUEBA.items():
                self.stdout.write(
                    f"  • {self.style.SUCCESS(nombre.ljust(22))}: {datos['descripcion']}"
                )
                self.stdout.write(
                    f"    FC: {datos['ritmo_cardiaco']} bpm | SpO2: {datos['spo2']}% | "
                    f"Temp: {datos['temperatura']} °C | Cánula: {'OK' if datos['canula_ok'] else 'Falla/Desconectada'}"
                )
            self.stdout.write("")
            return

        # 2. Ejecutar todos los casos en modo batería de pruebas
        if options["ejecutar_todos"]:
            self._ejecutar_bateria_completa()
            return

        # 3. Caso personalizado o específico
        cuna = self._obtener_o_crear_cuna(options["cuna"])

        if options["custom"]:
            fc = options["fc"]
            spo2 = options["spo2"]
            temp = options["temp"]
            canula = options["canula_ok"] if options["canula_ok"] is not None else True
            self._aplicar_y_mostrar(
                cuna=cuna,
                nombre_caso="Lectura Personalizada (CLI Custom)",
                descripcion="Valores pasados directamente por consola",
                fc=fc,
                spo2=spo2,
                temp=temp,
                canula_ok=canula,
            )
            return

        caso_nombre = options["caso"]
        if not caso_nombre:
            self.stdout.write(
                self.style.ERROR(
                    "Debes especificar --caso <nombre>, --custom o --ejecutar-todos.\n"
                    "Usa --listar-casos para ver las opciones disponibles."
                )
            )
            return

        caso = CASOS_PRUEBA[caso_nombre]
        self._aplicar_y_mostrar(
            cuna=cuna,
            nombre_caso=caso_nombre,
            descripcion=caso["descripcion"],
            fc=caso["ritmo_cardiaco"],
            spo2=caso["spo2"],
            temp=caso["temperatura"],
            canula_ok=caso["canula_ok"],
        )

    def _aplicar_y_mostrar(
        self,
        cuna: Cuna,
        nombre_caso: str,
        descripcion: str,
        fc: int | None,
        spo2: int | None,
        temp: float | None,
        canula_ok: bool | None,
    ):
        """Aplica los signos a la cuna, procesa las alertas y muestra el reporte."""
        cuna.ritmo_cardiaco = fc
        cuna.spo2 = spo2
        cuna.temperatura = temp
        cuna.canula_ok = canula_ok if canula_ok is not None else True
        cuna.save()

        procesar_alertas_cuna(cuna)
        alertas_activas = Alerta.objects.filter(cuna=cuna, activa=True).order_by(
            "-fecha_hora"
        )

        paciente_nombre = cuna.paciente.nombre_completo if cuna.paciente else "Sin paciente asignado"

        self.stdout.write(self.style.MIGRATE_HEADING(f"\n[+] Simulación en Cuna '{cuna.identificador}' ({paciente_nombre})"))
        self.stdout.write(f"    Caso: {self.style.SUCCESS(nombre_caso)} — {descripcion}")
        self.stdout.write(
            f"    Valores inyectados: FC={fc} bpm, SpO2={spo2}%, Temp={temp} °C, Cánula={'OK' if canula_ok else 'DESCONECTADA'}"
        )

        if not alertas_activas.exists():
            self.stdout.write(self.style.SUCCESS("    [✓] Estado normal: No hay alertas activas en esta cuna."))
        else:
            self.stdout.write(self.style.WARNING(f"    [!] Alertas activas ({alertas_activas.count()}):"))
            for al in alertas_activas:
                estilo = self.style.ERROR if al.nivel == "Critica" else self.style.WARNING
                self.stdout.write(f"        {estilo(f'[{al.nivel.upper()}]')} ({al.tipo}): {al.mensaje}")

        self.stdout.write("")

    def _ejecutar_bateria_completa(self):
        """Ejecuta una batería diagnóstica completa probando cada caso contra el motor de alertas."""
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Ejecutando Batería de Pruebas del Motor de Alertas ==="))
        total_casos = len(CASOS_PRUEBA)
        exitos = 0

        for nombre, caso in CASOS_PRUEBA.items():
            anomalias = evaluar_signos_vitales(
                ritmo_cardiaco=caso["ritmo_cardiaco"],
                spo2=caso["spo2"],
                temperatura=caso["temperatura"],
                canula_ok=caso["canula_ok"],
            )

            conteo_detectado = len(anomalias)
            conteo_esperado = caso["alertas_esperadas"]

            if conteo_detectado == conteo_esperado:
                exitos += 1
                icono = self.style.SUCCESS("[PASS]")
            else:
                icono = self.style.ERROR("[FAIL]")

            self.stdout.write(
                f"  {icono} {nombre.ljust(24)} -> Detectadas: {conteo_detectado} / Esperadas: {conteo_esperado}"
            )
            for a in anomalias:
                nivel = a["nivel"]
                estilo = self.style.ERROR if nivel == "Critica" else self.style.WARNING
                etiqueta = estilo(f"[{nivel}]")
                mensaje = a["mensaje"]
                self.stdout.write(f"         └─ {etiqueta} {mensaje}")

        self.stdout.write(self.style.MIGRATE_HEADING("---------------------------------------------------------"))
        resumen = f"Resultado: {exitos}/{total_casos} casos pasaron exitosamente."
        if exitos == total_casos:
            self.stdout.write(self.style.SUCCESS(f"[✓] {resumen} Todas las pruebas fueron satisfactorias!\n"))
        else:
            self.stdout.write(self.style.ERROR(f"[x] {resumen} Se detectaron discrepancias.\n"))
