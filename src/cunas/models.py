"""
Modelos de base de datos para la aplicación 'cunas'.

Define las entidades principales del sistema de monitoreo neonatal:
- Medico: el profesional de salud a cargo de uno o más bebés.
- Bebe: el paciente (recién nacido) que ocupa la cuna.
- Cuna: la unidad física de monitoreo con sus signos vitales en tiempo real.
- Medicamento: fármacos asignados a un bebé para control de administración.
"""

import datetime

from django.db import models
from django.utils import timezone


class Medico(models.Model):
    """
    Representa a un médico o profesional de salud que puede tener
    bebés asignados a su cargo.
    """
    nombre_completo = models.CharField(
        max_length=150,
        help_text="Ej: Dra. María López"
    )
    turno = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Turno de trabajo del médico (ej: Mañana, Tarde, Noche)"
    )

    def __str__(self):
        return self.nombre_completo

    class Meta:
        verbose_name = "Médico"
        verbose_name_plural = "Médicos"


class Bebe(models.Model):
    """
    Representa al paciente recién nacido. Está vinculado con un médico
    a cargo y, a través de la relación inversa con Cuna, a su unidad
    de monitoreo.
    """
    SEXO_CHOICES = [
        ('F', 'Femenino'),
        ('M', 'Masculino'),
    ]

    nombre_completo = models.CharField(
        max_length=200,
        help_text="Ej: Sofía García"
    )
    edad_meses = models.IntegerField(
        help_text="Edad del bebé expresada en meses"
    )
    sexo = models.CharField(
        max_length=1,
        choices=SEXO_CHOICES
    )
    peso = models.FloatField(
        null=True,
        blank=True,
        help_text="Peso del bebé en kilogramos (debe ser mayor a 0)"
    )
    fecha_nacimiento = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de nacimiento del bebé (no puede ser futura)"
    )
    fecha_ingreso = models.DateTimeField(
        default=timezone.now,
        help_text="Fecha y hora de ingreso del bebé a la unidad neonatal"
    )
    diagnostico = models.TextField(
        null=True,
        blank=True,
        help_text="Diagnóstico médico principal o motivo de ingreso"
    )
    plan_cuidados = models.TextField(
        null=True,
        blank=True,
        help_text="Plan de cuidados médicos y de enfermería asignado"
    )
    # Si el médico es eliminado del sistema, el campo queda vacío (SET_NULL)
    # en lugar de borrar también al bebé (CASCADE)
    medico_a_cargo = models.ForeignKey(
        Medico,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pacientes',
        help_text="Médico responsable del seguimiento de este bebé"
    )

    def __str__(self):
        return self.nombre_completo

    class Meta:
        verbose_name = "Bebé"
        verbose_name_plural = "Bebés"


class Cuna(models.Model):
    """
    Representa la cuna física y sus datos de monitoreo en tiempo real.
    Contiene los signos vitales del bebé y el estado de los dispositivos
    conectados (cánula, vía IV).

    La relación OneToOne con Bebe garantiza que un bebé solo puede estar
    asignado a una cuna a la vez.
    """
    ESTADO_SUENO_CHOICES = [
        ('Dormido', 'Dormido'),
        ('Despierto', 'Despierto'),
    ]

    identificador = models.CharField(
        max_length=20,
        unique=True,
        help_text="Identificador único de la cuna, ej: 'C01'"
    )
    # OneToOneField: un bebé solo puede ocupar una cuna a la vez
    paciente = models.OneToOneField(
        Bebe,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cuna_asignada',
        help_text="Bebé actualmente asignado a esta cuna"
    )

    # --- Signos vitales ---
    ritmo_cardiaco = models.IntegerField(
        null=True,
        blank=True,
        help_text="Frecuencia cardíaca en latidos por minuto (bpm)"
    )
    spo2 = models.IntegerField(
        null=True,
        blank=True,
        help_text="Saturación de oxígeno en sangre (%)"
    )
    temperatura = models.FloatField(
        null=True,
        blank=True,
        help_text="Temperatura corporal en grados Celsius (°C)"
    )

    # --- Estado de sensores y dispositivos ---
    estado_sueno = models.CharField(
        max_length=20,
        choices=ESTADO_SUENO_CHOICES,
        default='Despierto',
        help_text="Estado de sueño detectado por el sensor"
    )
    canula_ok = models.BooleanField(
        default=True,
        help_text="True si la cánula de oxígeno está funcionando correctamente"
    )
    via_iv_activa = models.BooleanField(
        default=False,
        help_text="True si la vía intravenosa está activa"
    )

    # Se actualiza automáticamente cada vez que se guarda un cambio en la cuna
    ultima_actualizacion = models.DateTimeField(
        auto_now=True,
        help_text="Fecha y hora de la última actualización de datos"
    )

    def __str__(self):
        # Muestra "C01 - Sofía García" si hay bebé, o "C01 - Vacía"
        nombre_bebe = self.paciente.nombre_completo if self.paciente else 'Vacía'
        return f"{self.identificador} - {nombre_bebe}"

    class Meta:
        verbose_name = "Cuna"
        verbose_name_plural = "Cunas"


class Medicamento(models.Model):
    """
    Representa el control de administración de fármacos para un paciente específico.
    """
    ESTADO_CHOICES = [
        ('Administrado', 'Administrado'),
        ('Pendiente', 'Pendiente'),
    ]

    VIA_CHOICES = [
        ('IV', 'Intravenosa (IV)'),
        ('IM', 'Intramuscular (IM)'),
        ('ET', 'Endotraqueal (ET)'),
        ('VO', 'Vía Oral (VO)'),
    ]

    # Relacionado al paciente. Usamos CASCADE porque si se elimina el bebé, 
    # probablemente se deban borrar sus registros médicos asociados a la internación actual.
    paciente = models.ForeignKey(
        Bebe,
        on_delete=models.CASCADE,
        related_name='medicamentos',
        help_text="Paciente al que se le administra el fármaco"
    )

    nombre = models.CharField(
        max_length=150,
        help_text="Nombre del medicamento (ej: Fenobarbital, Vitamina K)"
    )
    dosis = models.CharField(
        max_length=50,
        help_text="Cantidad y unidad de la dosis (ej: 5 mg/kg)"
    )
    via = models.CharField(
        max_length=2,
        choices=VIA_CHOICES,
        help_text="Vía de administración del fármaco"
    )
    hora = models.TimeField(
        help_text="Hora programada o en la que se administró el medicamento"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='Pendiente',
        help_text="Estado actual de la administración"
    )

    def __str__(self):
        return f"{self.nombre} - {self.paciente.nombre_completo} ({self.estado})"

    class Meta:
        verbose_name = "Medicamento"
        verbose_name_plural = "Medicamentos"


class Alerta(models.Model):
    """
    Representa una alerta o evento registrado en el historial de monitoreo
    de los signos vitales de un recién nacido.
    """
    NIVEL_CHOICES = [
        ('Info', 'Información'),
        ('Advertencia', 'Advertencia'),
        ('Critica', 'Crítica'),
    ]

    TIPO_CHOICES = [
        ('ritmo_cardiaco', 'Frecuencia Cardíaca'),
        ('spo2', 'Saturación de Oxígeno (SPO2)'),
        ('temperatura', 'Temperatura'),
        ('canula', 'Desconexión de Cánula'),
        ('otra', 'Otra Alerta'),
    ]

    paciente = models.ForeignKey(
        Bebe,
        on_delete=models.CASCADE,
        related_name='alertas',
        help_text="Bebé al que pertenece la alerta"
    )
    tipo = models.CharField(
        max_length=30,
        choices=TIPO_CHOICES,
        default='otra',
        help_text="Tipo de signo vital o sensor comprometido"
    )
    mensaje = models.CharField(
        max_length=255,
        help_text="Descripción o mensaje detallado de la alerta"
    )
    nivel = models.CharField(
        max_length=20,
        choices=NIVEL_CHOICES,
        default='Info',
        help_text="Severidad de la alerta"
    )
    fecha_hora = models.DateTimeField(
        default=timezone.now,
        help_text="Fecha y hora en que se generó la alerta"
    )

    def __str__(self):
        return f"[{self.nivel}] {self.paciente.nombre_completo}: {self.mensaje}"

    class Meta:
        verbose_name = "Alerta"
        verbose_name_plural = "Alertas"

