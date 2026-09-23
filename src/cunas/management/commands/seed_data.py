"""
Comando de gestión para sembrar datos clínicos de prueba en Poki Koa.

Puebla la base de datos con un entorno hospitalario neonatal realista:
- 4 Médicos en turnos Mañana, Tarde, Noche y Rotativo.
- 8 Cunas (6 con pacientes neonatales ingresados, 2 disponibles/vacías).
- Casos clínicos variados: estables, en observación y críticos (con alertas activas).
- Prescripciones de medicamentos (pendientes y administrados).
- Protocolos y planes de cuidado por área médica.
- Historial temporal de telemetría para alimentar gráficos en el frontend (US-06).

Uso:
    uv run poki_koa seed_data
    uv run poki_koa seed_data --reset
"""

import random
import sys
from datetime import time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from cunas.models import (
    Alerta,
    Bebe,
    Cuna,
    HistorialSignosVitales,
    Medicamento,
    Medico,
    PlanCuidado,
)


class Command(BaseCommand):
    help = "Siembra datos clínicos realistas para desarrollo del frontend web"

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-reset",
            action="store_true",
            help="Conserva los datos previos en lugar de reiniciar la base de datos",
        )

    def handle(self, *args, **options):
        no_reset = options.get("no_reset", False)
        self.stdout.write(self.style.MIGRATE_HEADING("Iniciando siembra de datos de prueba para Poki Koa..."))

        if not no_reset:
            self.stdout.write("Limpiando datos clínicos antiguos...")
            HistorialSignosVitales.objects.all().delete()
            Alerta.objects.all().delete()
            PlanCuidado.objects.all().delete()
            Medicamento.objects.all().delete()
            Cuna.objects.all().delete()
            Bebe.objects.all().delete()
            Medico.objects.all().delete()

        # 1. Crear Médicos
        self.stdout.write("Creando equipo médico...")
        medicos_data = [
            ("Dra. María López", "Mañana"),
            ("Dr. Juan Pérez", "Tarde"),
            ("Dra. Valentina Silva", "Noche"),
            ("Dr. Carlos Muñoz", "Rotativo"),
        ]
        medicos = []
        for nombre, turno in medicos_data:
            medico, _ = Medico.objects.get_or_create(nombre_completo=nombre, defaults={"turno": turno})
            medicos.append(medico)

        # 2. Pacientes (Bebés) y Cunas
        self.stdout.write("Creando pacientes neonatales y cunas de monitoreo...")
        ahora = timezone.now()
        hoy = ahora.date()

        casos_clinicos = [
            {
                "cuna": "C01",
                "bebe": {
                    "nombre_completo": "Sofía García",
                    "edad_meses": 1,
                    "sexo": "F",
                    "peso": 3.2,
                    "fecha_nacimiento": hoy - timedelta(days=28),
                    "diagnostico": "Prematurez moderada (33 semanas) en recuperación nutricional",
                    "plan_cuidados": "Alimentación enteral mínima con leche materna fortificada c/3h",
                    "medico": medicos[0],
                },
                "signos": {
                    "ritmo_cardiaco": 132,
                    "spo2": 98,
                    "temperatura": 36.8,
                    "estado_sueno": "Dormido",
                    "canula_ok": True,
                    "via_iv_activa": False,
                },
                "perfil_historico": "normal",
            },
            {
                "cuna": "C02",
                "bebe": {
                    "nombre_completo": "Mateo Rodríguez",
                    "edad_meses": 2,
                    "sexo": "M",
                    "peso": 4.1,
                    "fecha_nacimiento": hoy - timedelta(days=55),
                    "diagnostico": "Síndrome de Dificultad Respiratoria leve en fase de resolución",
                    "plan_cuidados": "Soporte con oxígeno suplementario por cánula nasal a 0.5 L/min",
                    "medico": medicos[1],
                },
                "signos": {
                    "ritmo_cardiaco": 172,  # Taquicardia moderada
                    "spo2": 96,
                    "temperatura": 37.1,
                    "estado_sueno": "Despierto",
                    "canula_ok": True,
                    "via_iv_activa": True,
                },
                "perfil_historico": "taquicardia",
            },
            {
                "cuna": "C03",
                "bebe": {
                    "nombre_completo": "Lucas Silva",
                    "edad_meses": 1,
                    "sexo": "M",
                    "peso": 2.8,
                    "fecha_nacimiento": hoy - timedelta(days=14),
                    "diagnostico": "Hiperbilirrubinemia neonatal no hemolítica en fototerapia",
                    "plan_cuidados": "Fototerapia continua en cuna radiante, hidratación parenteral",
                    "medico": medicos[0],
                },
                "signos": {
                    "ritmo_cardiaco": 128,
                    "spo2": 99,
                    "temperatura": 38.1,  # Fiebre / Hipertermia
                    "estado_sueno": "Dormido",
                    "canula_ok": True,
                    "via_iv_activa": True,
                },
                "perfil_historico": "fiebre",
            },
            {
                "cuna": "C04",
                "bebe": {
                    "nombre_completo": "Camila Valenzuela",
                    "edad_meses": 1,
                    "sexo": "F",
                    "peso": 2.5,
                    "fecha_nacimiento": hoy - timedelta(days=20),
                    "diagnostico": "Post-operatorio enterocolitis necrotizante tratada",
                    "plan_cuidados": "Monitoreo invasivo estricto, analgesia continua y reposo gástrico",
                    "medico": medicos[2],
                },
                "signos": {
                    "ritmo_cardiaco": 72,  # Bradicardia crítica
                    "spo2": 87,  # Desaturación crítica
                    "temperatura": 35.8,  # Hipotermia
                    "estado_sueno": "Despierto",
                    "canula_ok": False,  # Cánula desconectada
                    "via_iv_activa": True,
                },
                "perfil_historico": "critico",
            },
            {
                "cuna": "C05",
                "bebe": {
                    "nombre_completo": "Benjamín Morales",
                    "edad_meses": 3,
                    "sexo": "M",
                    "peso": 4.6,
                    "fecha_nacimiento": hoy - timedelta(days=80),
                    "diagnostico": "Bronquiolitis aguda viral en evolución favorable",
                    "plan_cuidados": "Kinesioterapia respiratoria suave, control de ingesta oral",
                    "medico": medicos[3],
                },
                "signos": {
                    "ritmo_cardiaco": 136,
                    "spo2": 95,
                    "temperatura": 36.7,
                    "estado_sueno": "Dormido",
                    "canula_ok": True,
                    "via_iv_activa": False,
                },
                "perfil_historico": "normal",
            },
            {
                "cuna": "C06",
                "bebe": {
                    "nombre_completo": "Isabella Torres",
                    "edad_meses": 2,
                    "sexo": "F",
                    "peso": 3.7,
                    "fecha_nacimiento": hoy - timedelta(days=45),
                    "diagnostico": "Observación preventiva cardiopatía funcional",
                    "plan_cuidados": "Monitoreo electrocardiográfico continuo y balance hídrico",
                    "medico": medicos[1],
                },
                "signos": {
                    "ritmo_cardiaco": 142,
                    "spo2": 97,
                    "temperatura": 36.6,
                    "estado_sueno": "Despierto",
                    "canula_ok": True,
                    "via_iv_activa": False,
                },
                "perfil_historico": "normal",
            },
        ]

        cunas_creadas = []
        bebes_creados = []

        for caso in casos_clinicos:
            b_info = caso["bebe"]
            bebe = Bebe.objects.create(
                nombre_completo=b_info["nombre_completo"],
                edad_meses=b_info["edad_meses"],
                sexo=b_info["sexo"],
                peso=b_info["peso"],
                fecha_nacimiento=b_info["fecha_nacimiento"],
                fecha_ingreso=ahora - timedelta(days=b_info["edad_meses"] * 7),
                diagnostico=b_info["diagnostico"],
                plan_cuidados=b_info["plan_cuidados"],
                medico_a_cargo=b_info["medico"],
            )
            bebes_creados.append(bebe)

            s_info = caso["signos"]
            cuna = Cuna.objects.create(
                identificador=caso["cuna"],
                paciente=bebe,
                ritmo_cardiaco=s_info["ritmo_cardiaco"],
                spo2=s_info["spo2"],
                temperatura=s_info["temperatura"],
                estado_sueno=s_info["estado_sueno"],
                canula_ok=s_info["canula_ok"],
                via_iv_activa=s_info["via_iv_activa"],
            )
            cunas_creadas.append(cuna)

            # Generar historial temporal de las últimas 12 horas (lecturas cada 30 min)
            base_fc = s_info["ritmo_cardiaco"] or 130
            base_spo2 = s_info["spo2"] or 98
            base_temp = s_info["temperatura"] or 36.7

            for minutos in range(720, 0, -30):
                timestamp = ahora - timedelta(minutes=minutos)
                # Variación leve realista
                fc_val = int(max(60, min(210, base_fc + random.randint(-4, 4))))
                spo2_val = int(max(80, min(100, base_spo2 + random.randint(-1, 1))))
                temp_val = round(max(35.0, min(40.0, base_temp + random.uniform(-0.15, 0.15))), 1)

                HistorialSignosVitales.objects.create(
                    cuna=cuna,
                    ritmo_cardiaco=fc_val,
                    spo2=spo2_val,
                    temperatura=temp_val,
                    fecha_hora=timestamp,
                )

        # Cunas adicionales disponibles (sin bebé asignado)
        cuna_c07 = Cuna.objects.create(identificador="C07", paciente=None)
        cuna_c08 = Cuna.objects.create(identificador="C08", paciente=None)
        cunas_creadas.extend([cuna_c07, cuna_c08])

        # 3. Medicamentos Prescritos
        self.stdout.write("Prescribiendo medicamentos y asignando estados...")
        medicamentos_data = [
            (bebes_creados[0], "Vitamina D3 gotas", "400 UI", "VO", time(9, 0), "Administrado"),
            (bebes_creados[0], "Sulfato Ferroso gotas", "2 mg/kg", "VO", time(14, 0), "Pendiente"),
            (bebes_creados[1], "Salbutamol nebulización", "0.5 ml", "ET", time(10, 0), "Administrado"),
            (bebes_creados[1], "Ampicilina sódica", "50 mg/kg", "IV", time(18, 0), "Pendiente"),
            (bebes_creados[2], "Suero Glucosado al 5%", "15 ml/h", "IV", time(8, 0), "Administrado"),
            (bebes_creados[2], "Paracetamol suspensión", "10 mg/kg", "VO", time(13, 0), "Pendiente"),
            (bebes_creados[3], "Fentanilo infusión continua", "1 mcg/kg/h", "IV", time(6, 0), "Administrado"),
            (bebes_creados[3], "Cefotaxima sódica", "50 mg/kg", "IV", time(16, 0), "Pendiente"),
            (bebes_creados[3], "Fenobarbital", "5 mg/kg", "IV", time(20, 0), "Pendiente"),
            (bebes_creados[4], "Amoxicilina", "40 mg/kg", "VO", time(12, 0), "Administrado"),
            (bebes_creados[5], "Furosemida", "1 mg/kg", "IV", time(15, 0), "Pendiente"),
        ]
        for bebe, nombre, dosis, via, hora, estado in medicamentos_data:
            Medicamento.objects.create(
                paciente=bebe,
                nombre=nombre,
                dosis=dosis,
                via=via,
                hora=hora,
                estado=estado,
            )

        # 4. Protocolos y Planes de Cuidado
        self.stdout.write("Registrando planes de cuidado clínico...")
        planes_data = [
            (bebes_creados[0], "Nutricional", "Alimentación por gavage c/3h con LM fortificada", "c/3h", "Activo"),
            (bebes_creados[0], "Desarrollo", "Terapia de contención y método canguro con madre", "c/24h", "Activo"),
            (bebes_creados[1], "Respiratorio", "Kinesioterapia respiratoria y monitorización de apnea", "c/6h", "Activo"),
            (bebes_creados[2], "Monitoreo", "Protección ocular y control de radiación fototerapia", "Continuo", "Activo"),
            (bebes_creados[3], "Farmacológico", "Control estricto de infusión IV y analgesia post-quirúrgica", "Continuo", "Activo"),
            (bebes_creados[3], "Respiratorio", "Inspección de permeabilidad y posición de cánula nasal", "c/2h", "Activo"),
            (bebes_creados[4], "Monitoreo", "Registro de curva térmica y frecuencia respiratoria", "c/4h", "Activo"),
            (bebes_creados[5], "Cardiovascular", "Control de pulsos periféricos y presión arterial media", "c/8h", "Activo"),
        ]
        for bebe, area, intervencion, frecuencia, estado in planes_data:
            PlanCuidado.objects.create(
                bebe=bebe,
                area_cuidado=area,
                intervencion=intervencion,
                frecuencia=frecuencia,
                estado=estado,
            )

        # Resumen en consola
        self.stdout.write(self.style.SUCCESS("\n✓ ¡Siembra de datos completada con éxito!"))
        self.stdout.write(f"• Médicos: {Medico.objects.count()}")
        self.stdout.write(f"• Pacientes (Bebés): {Bebe.objects.count()}")
        self.stdout.write(f"• Cunas totales: {Cuna.objects.count()} (6 ocupadas, 2 vacías)")
        self.stdout.write(f"• Medicamentos: {Medicamento.objects.count()} ({Medicamento.objects.filter(estado='Pendiente').count()} pendientes)")
        self.stdout.write(f"• Planes de cuidado: {PlanCuidado.objects.count()}")
        self.stdout.write(f"• Alertas clínicas generadas: {Alerta.objects.count()} ({Alerta.objects.filter(activa=True).count()} activas)")
        self.stdout.write(f"• Lecturas de telemetría histórica: {HistorialSignosVitales.objects.count()}")
        self.stdout.write(self.style.NOTICE("El backend está listo para el desarrollo web en http://127.0.0.1:8000/\n"))


def main():
    """Función de entrada para script directo."""
    from django.core.management import execute_from_command_line
    execute_from_command_line(["manage.py", "seed_data", *sys.argv[1:]])


if __name__ == "__main__":
    main()
