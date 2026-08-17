"""
Modelos de base de datos para la aplicación 'cunas'.

Define las tres entidades principales del sistema de monitoreo neonatal:
- Medico: el profesional de salud a cargo de uno o más bebés.
- Bebe: el paciente (recién nacido) que ocupa la cuna.
- Cuna: la unidad física de monitoreo con sus signos vitales en tiempo real.
"""

from django.db import models


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
        help_text="Identificador único de la cuna, ej: 'Cuna 01'"
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
        # Muestra "Cuna 01 - Sofía García" si hay bebé, o "Cuna 01 - Vacía"
        nombre_bebe = self.paciente.nombre_completo if self.paciente else 'Vacía'
        return f"{self.identificador} - {nombre_bebe}"

    class Meta:
        verbose_name = "Cuna"
        verbose_name_plural = "Cunas"