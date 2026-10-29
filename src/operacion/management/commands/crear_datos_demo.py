"""
Comando de gestión para poblar la unidad neonatal con datos de demostración.

Uso::

    python manage.py crear_datos_demo
    python manage.py crear_datos_demo --cunas 40 --pacientes 12

Genera un escenario coherente con el prototipo de Figma:

- 40 cunas (``C01`` … ``C40``), de las cuales una queda en mantenimiento.
- 3 turnos (Mañana, Tarde, Noche).
- 3 médicos y hasta 12 pacientes con cuna asignada.
- Prescripciones, planes de cuidado y alertas históricas (resueltas).
- Asignaciones de turno para los usuarios demo creados por
  ``crear_usuarios_demo`` (si existen).

El comando es **idempotente**: usa ``get_or_create`` sobre identificadores
estables, por lo que puede ejecutarse varias veces sin duplicar datos.

Seguridad
---------
Solo debe ejecutarse en desarrollo (o con ``--forzar`` de forma explícita).
"""

import random
from datetime import time, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from cunas.models import (
    Alerta,
    Bebe,
    Cuna,
    Medicamento,
    MedicamentoCatalogo,
    Medico,
    PlanCuidado,
)
from operacion.models import AsignacionTurno, Turno

Usuario = get_user_model()

NOMBRES = [
    ("Sofía", "García", "F"),
    ("Mateo", "Rojas", "M"),
    ("Emilia", "Fuentes", "F"),
    ("Benjamín", "Silva", "M"),
    ("Isidora", "Morales", "F"),
    ("Tomás", "Navarro", "M"),
    ("Florencia", "Castillo", "F"),
    ("Agustín", "Vergara", "M"),
    ("Amanda", "Herrera", "F"),
    ("Martín", "Araya", "M"),
    ("Josefa", "Pizarro", "F"),
    ("Vicente", "Sepúlveda", "M"),
]

MEDICOS = [
    ("Dra. Ana López", "Mañana"),
    ("Dr. Carlos Ramírez", "Tarde"),
    ("Dra. Paula Contreras", "Noche"),
]

MEDICAMENTOS = [
    ("Fenobarbital", "5 mg/kg", "IV"),
    ("Vitamina K", "1 mg", "IM"),
    ("Cafeína citrato", "20 mg/kg", "IV"),
    ("Ampicilina", "50 mg/kg", "IV"),
    ("Surfactante", "200 mg/kg", "ET"),
]

PLANES = [
    ("Respiratorio", "Monitoreo continuo de SpO2", "Continuo"),
    ("Nutricional", "Alimentación trófica por sonda", "c/3h"),
    ("Farmacológico", "Control de antibioticoterapia", "c/12h"),
    ("Monitoreo", "Registro de signos vitales", "c/1h"),
]

CATALOGO = [
    ("Fenobarbital 200 mg", "Fenobarbital", 200, 12),
    ("Vitamina K 10 mg", "Fitomenadiona", 10, 4),
    ("Cafeína citrato 20 mg", "Cafeína citrato", 20, 30),
    ("Ampicilina 500 mg", "Ampicilina", 500, 18),
    ("Surfactante 200 mg", "Poractant alfa", 200, 3),
]

TURNOS = [
    ("Mañana", "08:00", "16:00"),
    ("Tarde", "16:00", "00:00"),
    ("Noche", "00:00", "08:00"),
]


def _hora(texto):
    """Convierte ``"HH:MM"`` en un ``datetime.time``."""
    return time.fromisoformat(texto)


class Command(BaseCommand):
    """Crea un escenario de demostración completo y reproducible."""

    help = "Puebla la base de datos con cunas, pacientes, turnos y medicamentos demo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--cunas",
            type=int,
            default=40,
            help="Cantidad de cunas a crear (por defecto 40).",
        )
        parser.add_argument(
            "--pacientes",
            type=int,
            default=10,
            help="Cantidad de pacientes a crear (por defecto 10).",
        )
        parser.add_argument(
            "--forzar",
            action="store_true",
            help="Ejecuta el comando aunque DEBUG sea False.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["forzar"]:
            raise CommandError(
                "Este comando solo debe ejecutarse en desarrollo. Usa --forzar "
                "de forma explícita si realmente lo necesitas."
            )

        total_cunas = max(1, min(options["cunas"], 100))
        total_pacientes = max(0, min(options["pacientes"], 40))
        random.seed(2026)  # Resultados reproducibles entre ejecuciones.

        with transaction.atomic():
            cunas = self._crear_cunas(total_cunas)
            medicos = self._crear_medicos()
            self._crear_catalogo()
            turnos = self._crear_turnos()
            pacientes = self._crear_pacientes(total_pacientes, cunas, medicos)
            self._crear_medicamentos(pacientes)
            self._crear_planes(pacientes)
            self._crear_alertas_historicas(cunas)
            self._crear_asignaciones(turnos, cunas)

        self.stdout.write(
            self.style.SUCCESS(
                f"Datos demo listos: {len(cunas)} cunas, {len(pacientes)} pacientes, "
                f"{len(medicos)} médicos y {len(turnos)} turnos."
            )
        )
        self.stdout.write(
            "Siguiente paso sugerido: python manage.py crear_usuarios_demo"
        )

    # ------------------------------------------------------------------
    # Constructores privados
    # ------------------------------------------------------------------
    def _crear_cunas(self, total):
        """Crea las cunas ``C01..Cnn`` y marca la última en mantenimiento."""
        cunas = []
        for indice in range(1, total + 1):
            identificador = f"C{indice:02d}"
            cuna, _ = Cuna.objects.get_or_create(
                identificador=identificador,
                defaults={
                    "ritmo_cardiaco": random.randint(120, 158),
                    "spo2": random.randint(94, 100),
                    "temperatura": round(random.uniform(36.4, 37.4), 1),
                    "estado_sueno": random.choice(["Dormido", "Despierto"]),
                },
            )
            cunas.append(cuna)

        if total > 1:
            mantenimiento = cunas[-1]
            mantenimiento.en_mantenimiento = True
            mantenimiento._omitir_auditoria = True
            mantenimiento.save(update_fields=["en_mantenimiento", "ultima_actualizacion"])

        return cunas

    def _crear_medicos(self):
        """Crea el cuerpo médico de referencia."""
        return [
            Medico.objects.get_or_create(nombre_completo=nombre, defaults={"turno": turno})[0]
            for nombre, turno in MEDICOS
        ]

    def _crear_catalogo(self):
        """Crea productos del catálogo farmacéutico."""
        for nombre, principio, dosis, stock in CATALOGO:
            MedicamentoCatalogo.objects.get_or_create(
                nombre=nombre,
                defaults={
                    "principio_activo": principio,
                    "dosis_mg": dosis,
                    "stock": stock,
                },
            )

    def _crear_turnos(self):
        """Crea los tres turnos clásicos si no existen."""
        turnos = []
        for nombre, inicio, fin in TURNOS:
            turno, _ = Turno.objects.get_or_create(
                nombre=nombre,
                defaults={"hora_inicio": _hora(inicio), "hora_fin": _hora(fin)},
            )
            turnos.append(turno)
        return turnos

    def _crear_pacientes(self, total, cunas, medicos):
        """Crea pacientes y los asigna a las primeras cunas disponibles."""
        pacientes = []
        hoy = timezone.localdate()
        disponibles = [cuna for cuna in cunas if not cuna.en_mantenimiento]

        for indice in range(total):
            nombre, apellido, sexo = NOMBRES[indice % len(NOMBRES)]
            identificador = f"BEB-{indice + 1:04d}"
            dias_ingreso = min(indice, 13)

            bebe, creado = Bebe.objects.get_or_create(
                identificador=identificador,
                defaults={
                    "nombre_completo": f"{nombre} {apellido}",
                    "edad_meses": 0,
                    "edad_gestacional": round(random.uniform(27.0, 40.0), 1),
                    "sexo": sexo,
                    "peso": round(random.uniform(0.9, 3.8), 2),
                    "fecha_nacimiento": hoy - timedelta(days=random.randint(1, 45)),
                    "fecha_ingreso": timezone.now() - timedelta(days=dias_ingreso, hours=random.randint(0, 8)),
                    "diagnostico": random.choice(
                        [
                            "Prematuridad extrema",
                            "Síndrome de dificultad respiratoria",
                            "Ictericia neonatal",
                            "Sepsis neonatal temprana",
                            "Bajo peso al nacer",
                        ]
                    ),
                    "medico_a_cargo": medicos[indice % len(medicos)],
                },
            )
            pacientes.append(bebe)

            # Asignación de cuna (solo si el bebé está activo y la cuna libre).
            if creado and indice < len(disponibles):
                cuna = disponibles[indice]
                if cuna.paciente_id is None:
                    cuna.paciente = bebe
                    cuna._omitir_auditoria = True
                    cuna.save(update_fields=["paciente", "ultima_actualizacion"])

        return pacientes

    def _crear_medicamentos(self, pacientes):
        """Crea prescripciones pendientes y administradas."""
        for indice, bebe in enumerate(pacientes):
            for posicion, (nombre, dosis, via) in enumerate(MEDICAMENTOS[:3]):
                Medicamento.objects.get_or_create(
                    paciente=bebe,
                    nombre=nombre,
                    defaults={
                        "dosis": dosis,
                        "via": via,
                        "hora": _hora(f"{(8 + posicion * 4) % 24:02d}:00"),
                        "estado": "Administrado" if (indice + posicion) % 2 == 0 else "Pendiente",
                    },
                )

    def _crear_planes(self, pacientes):
        """Crea planes de cuidado activos por paciente."""
        for bebe in pacientes:
            for area, intervencion, frecuencia in PLANES:
                PlanCuidado.objects.get_or_create(
                    bebe=bebe,
                    area_cuidado=area,
                    defaults={
                        "intervencion": intervencion,
                        "frecuencia": frecuencia,
                        "estado": "Activo",
                    },
                )

    def _crear_alertas_historicas(self, cunas):
        """Genera alertas resueltas para que la serie temporal tenga datos."""
        ahora = timezone.now()
        for indice, cuna in enumerate(cunas[:8]):
            Alerta.objects.get_or_create(
                cuna=cuna,
                mensaje="Desaturación transitoria resuelta",
                defaults={
                    "paciente": cuna.paciente,
                    "tipo": "spo2",
                    "nivel": "Advertencia",
                    "fecha_hora": ahora - timedelta(days=indice % 7, hours=indice),
                    "activa": False,
                    "valor_leido": 93,
                },
            )

    def _crear_asignaciones(self, turnos, cunas):
        """Asigna los usuarios demo a los turnos y cunas del día."""
        hoy = timezone.localdate()
        usuarios = list(Usuario.objects.filter(is_active=True).order_by("username")[:3])
        if not usuarios:
            return

        ocupadas = [cuna for cuna in cunas if cuna.paciente_id][:3]
        for indice, usuario in enumerate(usuarios):
            turno = turnos[indice % len(turnos)]
            cuna = ocupadas[indice] if indice < len(ocupadas) else None
            AsignacionTurno.objects.get_or_create(
                usuario=usuario,
                turno=turno,
                cuna=cuna,
                fecha=hoy,
            )
