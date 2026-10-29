"""
Modelos de la aplicación 'operacion'.

Contiene tres entidades independientes del dato clínico puro:

- ``Turno``: catálogo de turnos de trabajo (Mañana, Tarde, Noche).
- ``AsignacionTurno``: vínculo entre un usuario, un turno, una fecha y,
  opcionalmente, una cuna.
- ``RegistroActividad``: bitácora append-only de acciones del sistema.

Notas de diseño
---------------
Las claves foráneas a ``cunas`` se declaran como cadena (``"cunas.Cuna"``)
para evitar importaciones circulares entre aplicaciones.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Turno(models.Model):
    """
    Catálogo de turnos de trabajo del personal.

    Invariantes:
    - ``nombre`` es único (no puede haber dos turnos "Mañana").
    - ``hora_inicio`` y ``hora_fin`` son obligatorias.
    - Un turno inactivo se conserva para no romper asignaciones históricas.
    """

    nombre = models.CharField(
        max_length=50,
        unique=True,
        help_text="Nombre del turno, ej: Mañana, Tarde, Noche",
    )
    hora_inicio = models.TimeField(help_text="Hora de inicio del turno")
    hora_fin = models.TimeField(help_text="Hora de término del turno")
    activo = models.BooleanField(
        default=True,
        help_text="Indica si el turno puede usarse en nuevas asignaciones",
    )

    class Meta:
        verbose_name = "Turno"
        verbose_name_plural = "Turnos"
        ordering = ["hora_inicio"]

    def __str__(self):
        return self.nombre

    def clean(self):
        """Valida que el turno tenga una duración positiva dentro del día."""
        super().clean()
        if self.hora_inicio and self.hora_fin and self.hora_inicio == self.hora_fin:
            raise ValidationError(
                {"hora_fin": "La hora de término debe ser distinta a la de inicio."}
            )

    @property
    def duracion_horas(self):
        """
        Duración del turno en horas.

        Si ``hora_fin`` es menor que ``hora_inicio`` se asume que el turno
        cruza la medianoche (por ejemplo, Noche de 20:00 a 08:00).
        """
        inicio = self.hora_inicio.hour * 60 + self.hora_inicio.minute
        fin = self.hora_fin.hour * 60 + self.hora_fin.minute
        if fin <= inicio:
            fin += 24 * 60
        return round((fin - inicio) / 60, 2)


class AsignacionTurno(models.Model):
    """
    Asignación de una persona a un turno, una fecha y opcionalmente una cuna.

    Invariantes:
    - Un usuario no puede tener dos asignaciones idénticas (mismo turno,
      fecha y cuna).
    - ``fecha`` no puede ser anterior a la fecha de creación menos un día
      (evita reescribir el pasado por error).
    - Eliminar un turno con asignaciones está prohibido (``PROTECT``).
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="asignaciones_turno",
        help_text="Persona asignada al turno",
    )
    turno = models.ForeignKey(
        Turno,
        on_delete=models.PROTECT,
        related_name="asignaciones",
        help_text="Turno que cubre la persona",
    )
    cuna = models.ForeignKey(
        "cunas.Cuna",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asignaciones",
        help_text="Cuna asignada (opcional: jefatura puede asignar solo el turno)",
    )
    fecha = models.DateField(
        default=timezone.localdate,
        db_index=True,
        help_text="Día en que se cubre el turno",
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="asignaciones_creadas",
        help_text="Usuario que registró la asignación",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Asignación de turno"
        verbose_name_plural = "Asignaciones de turno"
        ordering = ["-fecha", "turno__hora_inicio", "usuario__username"]
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "turno", "cuna", "fecha"],
                name="asignacion_turno_unica",
            ),
        ]

    def __str__(self):
        cuna = self.cuna.identificador if self.cuna else "sin cuna"
        return f"{self.usuario.username} · {self.turno.nombre} · {self.fecha} · {cuna}"

    def clean(self):
        """Comprueba que la cuna no esté asignada a otra persona el mismo día."""
        super().clean()
        if not self.cuna_id or not self.fecha:
            return
        conflicto = (
            AsignacionTurno.objects.filter(fecha=self.fecha, cuna=self.cuna)
            .exclude(pk=self.pk)
            .exclude(turno=self.turno)
            .select_related("usuario", "turno")
            .first()
        )
        if conflicto:
            raise ValidationError(
                {
                    "cuna": (
                        f"La cuna {self.cuna.identificador} ya está cubierta por "
                        f"{conflicto.usuario.get_full_name() or conflicto.usuario.username} "
                        f"en el turno {conflicto.turno.nombre}."
                    )
                }
            )


class RegistroActividad(models.Model):
    """
    Bitácora de auditoría del sistema.

    Es **append-only**: los registros no se modifican ni se eliminan desde
    la API (el ViewSet es de solo lectura). Se guarda:

    - ``usuario``: responsable de la acción (o ``None`` para procesos
      automáticos como la telemetría).
    - ``accion``: verbo normalizado (``crear``, ``actualizar``, ...).
    - ``entidad`` / ``entidad_id``: objeto afectado.
    - ``descripcion``: texto legible para el panel de registros.
    - ``metadata``: datos adicionales en JSON (cambios, valores, etc.).
    - ``ip_address``: origen de la petición HTTP, si existe.
    """

    ACCION_CREAR = "crear"
    ACCION_ACTUALIZAR = "actualizar"
    ACCION_ELIMINAR = "eliminar"
    ACCION_LOGIN = "login"
    ACCION_LOGOUT = "logout"
    ACCION_ASIGNAR = "asignar"
    ACCION_LIBERAR = "liberar"
    ACCION_ADMINISTRAR = "administrar"
    ACCION_ALTA = "alta"
    ACCION_RESOLVER = "resolver"

    ACCION_CHOICES = [
        (ACCION_CREAR, "Creación"),
        (ACCION_ACTUALIZAR, "Actualización"),
        (ACCION_ELIMINAR, "Eliminación"),
        (ACCION_LOGIN, "Inicio de sesión"),
        (ACCION_LOGOUT, "Cierre de sesión"),
        (ACCION_ASIGNAR, "Asignación"),
        (ACCION_LIBERAR, "Liberación"),
        (ACCION_ADMINISTRAR, "Administración de medicamento"),
        (ACCION_ALTA, "Alta clínica"),
        (ACCION_RESOLVER, "Resolución de alerta"),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registros_actividad",
        help_text="Usuario que ejecutó la acción (vacío si fue automático)",
    )
    accion = models.CharField(max_length=20, choices=ACCION_CHOICES)
    entidad = models.CharField(
        max_length=50,
        help_text="Nombre del modelo afectado, ej: Bebe, Cuna, Medicamento",
    )
    entidad_id = models.CharField(
        max_length=50,
        blank=True,
        help_text="Clave primaria del objeto afectado",
    )
    descripcion = models.CharField(
        max_length=255,
        help_text="Resumen legible de la acción para el panel de registros",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Datos adicionales de la acción (valores anteriores/nuevos)",
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Dirección IP desde la que se ejecutó la acción",
    )
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Registro de actividad"
        verbose_name_plural = "Registros de actividad"
        ordering = ["-creado_en"]
        indexes = [
            models.Index(fields=["entidad", "entidad_id"]),
            models.Index(fields=["accion", "-creado_en"]),
        ]

    def __str__(self):
        autor = self.usuario.username if self.usuario else "sistema"
        return f"{self.creado_en:%Y-%m-%d %H:%M} · {autor} · {self.accion} {self.entidad}"
