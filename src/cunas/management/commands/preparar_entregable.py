"""Datos ficticios reproducibles, restringidos a la base de demostración.

python scripts/verificar_entrega2.py --static
uv run python scripts/verificar_entrega2.py --run
No acepta servidores externos: siempre utiliza settings_entregable y datos ficticios.
"""

from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, CommandError, call_command


class Command(BaseCommand):
    """Comando personalizado de Django para cargar el escenario de pruebas aislado."""

    help = "Carga el escenario de pruebas de APIs en db_entregable.sqlite3."

    """
    Configura los argumentos permitidos para el comando de gestión.

    @param parser - Instancia del analizador de argumentos de Django.
    @returns None - Registra los argumentos permitidos en el parser.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Vacía únicamente la base de demostración antes de cargar los datos.",
        )

    """
    Ejecuta las validaciones de seguridad de base de datos y carga el fixture demo.

    @param args - Argumentos posicionales adicionales.
    @param options - Diccionario de opciones CLI (incluyendo --reset).
    @returns None - Carga los datos o lanza CommandError si no se cumple el entorno seguro.
    """

    def handle(self, *args, **options):
        expected = Path(settings.BASE_DIR) / "db_entregable.sqlite3"
        actual = Path(settings.DATABASES["default"]["NAME"])
        if (
            settings.SETTINGS_MODULE != "poki_koa.settings_entregable"
            or actual.resolve() != expected.resolve()
        ):
            raise CommandError(
                "Usar --settings=poki_koa.settings_entregable. "
                "Este comando nunca prepara la base habitual."
            )
        from cunas.models import Bebe, Medico

        if not options["reset"] and (Bebe.objects.exists() or Medico.objects.exists()):
            raise CommandError("El escenario ya tiene datos. Repetir con --reset.")
        if options["reset"]:
            call_command("flush", interactive=False, verbosity=0)
        fixture = Path(settings.BASE_DIR).parent / "qa" / "entrega2" / "datos_demo.json"
        call_command("loaddata", str(fixture), verbosity=1)
        self.stdout.write(
            self.style.SUCCESS(
                "Escenario cargado. Ejecutar B01…B22 y luego M01…M22, en orden."
            )
        )
