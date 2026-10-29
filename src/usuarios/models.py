"""
Modelos de la aplicación 'usuarios'.

Se utiliza el modelo ``django.contrib.auth.models.User`` como base de
autenticación y se le asocia un ``PerfilUsuario`` con la información
clínica necesaria para el control de acceso:

- ``rol``: define qué pantallas y acciones puede ejecutar la persona.
- ``turno``: turno habitual, usado como valor por defecto al asignar cunas.

Esta estrategia evita reemplazar ``AUTH_USER_MODEL`` (lo que obligaría a
rehacer todas las migraciones) y mantiene la compatibilidad con el panel
de administración de Django.
"""

from typing import ClassVar

from django.conf import settings
from django.db import models


class PerfilUsuario(models.Model):
    """
    Perfil clínico asociado a un usuario de Django.

    Invariantes:
    - Existe como máximo un perfil por usuario (``OneToOneField``).
    - Todo perfil referencia un usuario válido del sistema.
    """

    ROL_ADMINISTRADOR: ClassVar = "administrador"
    ROL_MEDICO: ClassVar = "medico"
    ROL_ENFERMERIA: ClassVar = "enfermeria"

    ROL_CHOICES: ClassVar = [
        (ROL_ADMINISTRADOR, "Administrador"),
        (ROL_MEDICO, "Médico"),
        (ROL_ENFERMERIA, "Enfermería"),
    ]

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil",
        help_text="Usuario de Django al que pertenece este perfil",
    )
    rol = models.CharField(
        max_length=20,
        choices=ROL_CHOICES,
        default=ROL_ENFERMERIA,
        help_text="Rol clínico que determina los permisos dentro del sistema",
    )
    turno = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Turno habitual de trabajo (ej: Mañana, Tarde, Noche)",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil de usuario"
        verbose_name_plural = "Perfiles de usuario"
        ordering = ["usuario__first_name", "usuario__username"]

    def __str__(self):
        return f"{self.nombre_completo} ({self.get_rol_display()})"

    @property
    def nombre_completo(self) -> str:
        """
        Nombre legible del usuario.

        Prioriza ``first_name`` + ``last_name`` y cae a ``username`` cuando
        el usuario no tiene nombre configurado. Nunca retorna ``None`` para
        simplificar el consumo desde el frontend.
        """
        nombre = self.usuario.get_full_name().strip()
        return nombre or self.usuario.username

    @property
    def iniciales(self) -> str:
        """
        Iniciales de hasta dos letras usadas en el avatar de la interfaz.

        Se calculan sobre ``nombre_completo``; si el nombre no aporta letras
        se usa la primera letra del ``username``.
        """
        partes = [parte for parte in self.nombre_completo.split() if parte]
        if not partes:
            return "?"
        if len(partes) == 1:
            return partes[0][:2].upper()
        return (partes[0][0] + partes[-1][0]).upper()

    @property
    def es_administrador(self) -> bool:
        """Indica si el perfil posee el rol de mayor privilegio."""
        return self.rol == self.ROL_ADMINISTRADOR
