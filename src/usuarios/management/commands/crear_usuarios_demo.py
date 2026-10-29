"""
Comando de gestión para crear el personal de demostración.

Uso::

    python manage.py crear_usuarios_demo
    python manage.py crear_usuarios_demo --password "OtraClave123"

El comando es **idempotente**: si el usuario ya existe, actualiza su rol y
turno, pero no cambia la contraseña salvo que se pase ``--resetear-claves``.

Seguridad
---------
- Solo está pensado para entornos de desarrollo. Si ``DEBUG`` es ``False``
  y no se indica ``--forzar``, el comando se niega a ejecutarse.
- La contraseña por defecto es pública a propósito; debe cambiarse en
  cualquier despliegue real.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from usuarios.models import PerfilUsuario

Usuario = get_user_model()

PASSWORD_POR_DEFECTO = "PokiKoa2026!"


class Command(BaseCommand):
    """Crea administradores, médicos y enfermeras de demostración."""

    help = "Crea usuarios de demostración con perfiles clínicos (solo desarrollo)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default=PASSWORD_POR_DEFECTO,
            help="Contraseña a asignar a los usuarios nuevos.",
        )
        parser.add_argument(
            "--resetear-claves",
            action="store_true",
            help="Sobrescribe la contraseña de los usuarios que ya existen.",
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

        password = options["password"]
        resetear = options["resetear_claves"]

        usuarios = [
            {
                "username": "ana.lopez",
                "email": "ana.lopez@poki-koa.cl",
                "first_name": "Ana",
                "last_name": "López",
                "rol": PerfilUsuario.ROL_ADMINISTRADOR,
                "turno": "Mañana",
            },
            {
                "username": "carlos.ramirez",
                "email": "carlos.ramirez@poki-koa.cl",
                "first_name": "Carlos",
                "last_name": "Ramírez",
                "rol": PerfilUsuario.ROL_MEDICO,
                "turno": "Tarde",
            },
            {
                "username": "rosa.perez",
                "email": "rosa.perez@poki-koa.cl",
                "first_name": "Rosa",
                "last_name": "Pérez",
                "rol": PerfilUsuario.ROL_ENFERMERIA,
                "turno": "Noche",
            },
        ]

        with transaction.atomic():
            for datos in usuarios:
                rol = datos.pop("rol")
                turno = datos.pop("turno")
                username = datos["username"]

                usuario, creado = Usuario.objects.get_or_create(
                    username=username,
                    defaults=datos,
                )

                if creado or resetear:
                    usuario.set_password(password)
                    usuario.save(update_fields=["password"])

                perfil, _ = PerfilUsuario.objects.get_or_create(usuario=usuario)
                perfil.rol = rol
                perfil.turno = turno
                perfil.save(update_fields=["rol", "turno", "actualizado_en"])

                estado = "creado" if creado else "actualizado"
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Usuario '{username}' {estado} con rol '{rol}'."
                    )
                )

        if not resetear:
            self.stdout.write(
                self.style.WARNING(
                    "Las contraseñas existentes no se modificaron. Usa "
                    "--resetear-claves si necesitas restaurarlas."
                )
            )
