"""
Comando de gestión Django para inicializar la base de datos con el escenario
institucional a escala (Issue CR-402 #42):
- 40 cunas de monitoreo (C01 a C40).
- 12 profesionales clínicos (médicos / matronas) en turnos rotativos.
- 3 turnos rotativos (Mañana, Tarde, Noche) con subconjuntos de cunas asignadas.
- Pacientes neonatales (matriculados y con matrícula inactiva).
- Apoderados vinculados para verificar las reglas de visibilidad y acceso por rol.
"""

from datetime import time
from django.core.management.base import BaseCommand
from django.utils import timezone

from cunas.models import (
    Apoderado,
    AsignacionTurno,
    Bebe,
    Cuna,
    Medico,
    Turno,
)


class Command(BaseCommand):
    help = "Puebla la base de datos con 40 cunas, 12 profesionales en turnos rotativos y apoderados."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limpiar",
            action="store_true",
            help="Elimina registros previos de escala antes de poblar la base de datos.",
        )

    def handle(self, *args, **options):
        limpiar = options.get("limpiar", False)

        if limpiar:
            self.stdout.write(self.style.WARNING("Limpiando datos previos..."))
            AsignacionTurno.objects.all().delete()
            Apoderado.objects.all().delete()
            Cuna.objects.all().delete()
            Bebe.objects.all().delete()
            Medico.objects.all().delete()
            Turno.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Datos previos eliminados."))

        self.stdout.write(self.style.NOTICE("🚀 Inicializando escenario a escala institucional (CR-402)..."))

        # 1. Crear Turnos
        turnos_data = [
            {"nombre": "Mañana", "inicio": time(8, 0), "fin": time(16, 0)},
            {"nombre": "Tarde", "inicio": time(16, 0), "fin": time(0, 0)},
            {"nombre": "Noche", "inicio": time(0, 0), "fin": time(8, 0)},
        ]
        turnos = {}
        for td in turnos_data:
            turno_obj, _ = Turno.objects.get_or_create(
                nombre=td["nombre"],
                defaults={"hora_inicio": td["inicio"], "hora_fin": td["fin"], "activo": True},
            )
            turnos[td["nombre"]] = turno_obj

        # 2. Crear 12 Profesionales (Médicos / Matronas)
        nombres_profesionales = [
            # 4 para Mañana
            "Dra. Camila Soto",
            "Matr. Rodrigo Vega",
            "Dr. Esteban Morales",
            "Matr. Valeria Rojas",
            # 4 para Tarde
            "Dra. Paula Henríquez",
            "Matr. Ignacio Silva",
            "Dr. Matías Castro",
            "Matr. Constanza Navarrete",
            # 4 para Noche
            "Dra. Andrea Vidal",
            "Matr. Gabriel Fuentes",
            "Dr. Felipe Bravo",
            "Matr. Daniela Paredes",
        ]

        profesionales = []
        for i, nombre in enumerate(nombres_profesionales):
            turno_nombre = "Mañana" if i < 4 else ("Tarde" if i < 8 else "Noche")
            prof, _ = Medico.objects.get_or_create(
                nombre_completo=nombre,
                defaults={"turno": turno_nombre},
            )
            profesionales.append((prof, turno_nombre))

        # 3. Crear 40 Cunas (C01 a C40)
        cunas = []
        for i in range(1, 41):
            identificador = f"C{i:02d}"
            # Variaciones fisiológicas normales
            fc = 120 + (i % 25)
            spo2 = 95 + (i % 5)
            temp = round(36.4 + (i % 7) * 0.1, 1)
            sueno = "Dormido" if i % 2 == 0 else "Despierto"

            cuna, _ = Cuna.objects.get_or_create(
                identificador=identificador,
                defaults={
                    "ritmo_cardiaco": fc,
                    "spo2": spo2,
                    "temperatura": temp,
                    "estado_sueno": sueno,
                    "canula_ok": True,
                    "via_iv_activa": (i % 3 == 0),
                },
            )
            cunas.append(cuna)

        # 4. Asignar subconjuntos de cunas según turno rotativo
        # Para cada turno (4 profesionales), cada profesional recibe 10 cunas (4 * 10 = 40)
        hoy = timezone.now().date()
        AsignacionTurno.objects.filter(fecha=hoy).delete()

        for turno_nombre, turno_obj in turnos.items():
            profs_del_turno = [p for p, t in profesionales if t == turno_nombre]
            # Si es rotativo, se puede rotar el offset de cunas
            offset = 0 if turno_nombre == "Mañana" else (10 if turno_nombre == "Tarde" else 20)
            for idx, prof in enumerate(profs_del_turno):
                # 10 cunas por profesional en este turno
                indices_cunas = [(offset + idx * 10 + k) % 40 for k in range(10)]
                cunas_asignadas = [cunas[k] for k in indices_cunas]

                asig = AsignacionTurno.objects.create(
                    medico=prof,
                    turno=turno_obj,
                    fecha=hoy,
                    activo=True,
                )
                asig.cunas.set(cunas_asignadas)

        # 5. Crear Bebés asignados a cunas (30 activos matriculados, 1 con matrícula inactiva para pruebas)
        bebes_creados = []
        for i in range(1, 31):
            cuna = cunas[i - 1]
            medico_asignado = profesionales[(i - 1) % len(profesionales)][0]
            es_matriculado = (i != 2)  # El bebé 2 tiene matrícula cancelada/egresado para pruebas de regla de apoderado

            bebe, _ = Bebe.objects.get_or_create(
                nombre_completo=f"Paciente Recién Nacido {i:02d}",
                defaults={
                    "edad_meses": 1 + (i % 6),
                    "sexo": "F" if i % 2 == 0 else "M",
                    "peso": round(2.8 + (i % 12) * 0.15, 2),
                    "diagnostico": "Cuidado intensivo neonatal" if i % 4 == 0 else "Observación y desarrollo",
                    "medico_a_cargo": medico_asignado,
                    "matriculado": es_matriculado,
                },
            )
            cuna.paciente = bebe
            cuna.save()
            bebes_creados.append(bebe)

        # 6. Crear Apoderados vinculados
        # Apoderado 1: vinculado a Bebe 1 (cuna C01, matriculado=True) -> Puede ver cuna C01
        Apoderado.objects.get_or_create(
            rut="15.111.222-3",
            defaults={
                "nombre_completo": "Carlos González (Apoderado Activo)",
                "email": "carlos.gonzalez@example.com",
                "telefono": "+56911223344",
                "bebe": bebes_creados[0],
            },
        )

        # Apoderado 2: vinculado a Bebe 2 (cuna C02, matriculado=False) -> No puede ver la cuna (matrícula inactiva)
        Apoderado.objects.get_or_create(
            rut="16.333.444-5",
            defaults={
                "nombre_completo": "Marcela Torres (Apoderado Matrícula Inactiva)",
                "email": "marcela.torres@example.com",
                "telefono": "+56955667788",
                "bebe": bebes_creados[1],
            },
        )

        self.stdout.write(self.style.SUCCESS("✅ Escala institucional inicializada exitosamente:"))
        self.stdout.write(f"   • {Cuna.objects.count()} cunas registradas (C01 a C40).")
        self.stdout.write(f"   • {Medico.objects.count()} profesionales clínicos en {Turno.objects.count()} turnos.")
        self.stdout.write(f"   • {AsignacionTurno.objects.count()} asignaciones de subconjuntos de cunas rotativas.")
        self.stdout.write(f"   • {Bebe.objects.count()} pacientes registrados ({Bebe.objects.filter(matriculado=True).count()} matriculados activos).")
        self.stdout.write(f"   • {Apoderado.objects.count()} apoderados vinculados (1 activo, 1 inactivo para verificación).")
