"""Generador automatizado de Model, Serializer, ViewSet y URL para un nuevo recurso CRUD.

Este script define un comando personalizado de Django que automatiza la creación
de componentes backend estándar a partir de un nombre de modelo en PascalCase.
"""

import os
import re
import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

"""
Retorna el slug plural y el identificador snake_case en español para rutas de API.

@param name - Nombre del modelo en formato PascalCase o texto base.
@returns tuple[str, str] - Una tupla con (plural_slug, plural_snake).
"""


def spanish_plural(name: str) -> tuple[str, str]:
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    snake = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    words = snake.split("_")
    last_word = words[-1]
    if last_word.endswith(("a", "e", "i", "o", "u")):
        words[-1] = last_word + "s"
    elif last_word.endswith("z"):
        words[-1] = last_word[:-1] + "ces"
    else:
        words[-1] = last_word + "es"

    plural_snake = "_".join(words)
    plural_slug = plural_snake.replace("_", "-")
    return plural_slug, plural_snake


"""
Añade un nuevo elemento a una sentencia de importación en el contenido de un archivo.

@param content - Contenido de texto actual del archivo de código fuente.
@param import_prefix - Prefijo de la importación (ej. 'from .models import').
@param new_item - Nombre del elemento o clase a importar.
@returns str - El contenido actualizado con la importación añadida.
"""


def add_to_import(content: str, import_prefix: str, new_item: str) -> str:
    if re.search(r"\b" + re.escape(new_item) + r"\b", content):
        return content

    # Patrón para importaciones multilínea: from .models import (\n ... \n)
    pattern_multi = re.escape(import_prefix) + r"\s*\(([^)]+)\)"
    match_multi = re.search(pattern_multi, content, re.DOTALL)
    if match_multi:
        existing = match_multi.group(1).rstrip()
        replacement = f"{import_prefix} ({existing},\n    {new_item}\n)"
        return (
            content[: match_multi.start()] + replacement + content[match_multi.end() :]
        )

    # Patrón para importaciones en una sola línea: from .models import A, B
    pattern_single = re.escape(import_prefix) + r"([^\n]+)"
    match_single = re.search(pattern_single, content)
    if match_single:
        existing = match_single.group(1).strip()
        replacement = f"{import_prefix} {existing}, {new_item}"
        return (
            content[: match_single.start()]
            + replacement
            + content[match_single.end() :]
        )

    # Si no existe la sentencia, agregamos la importación al inicio
    return f"{import_prefix} {new_item}\n" + content


class Command(BaseCommand):
    """Comando de gestión de Django para generar la estructura CRUD de un recurso."""

    help = "Genera automáticamente el Model, Serializer, ViewSet y la URL para un nuevo recurso CRUD."

    """
    Configura los argumentos requeridos y opcionales para la ejecución del comando CLI.

    @param parser - Instancia del analizador de argumentos de Django.
    @returns None - Registra los argumentos en el parser.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "model_name",
            type=str,
            help="Nombre del modelo en PascalCase (ej: Diagnostico, ExamenMedico)",
        )
        parser.add_argument(
            "--app",
            type=str,
            default="cunas",
            help="Nombre de la aplicación Django (por defecto: cunas)",
        )

    """
    Función de ejecución principal del comando CRUD.

    @param args - Argumentos posicionales adicionales.
    @param options - Opciones y parámetros de la línea de comandos.
    @returns None - Escribe archivos de código y notificaciones en consola.
    """

    def handle(self, *args, **options):
        raw_name = options["model_name"].strip()
        model_name = raw_name[0].upper() + raw_name[1:]
        app_name = options["app"]

        # Encontrar directorio del proyecto
        from django.conf import settings

        base_dir = Path(settings.BASE_DIR)
        app_dir = base_dir / app_name

        if not app_dir.exists():
            raise CommandError(
                f"No se encontró la aplicación '{app_name}' en {base_dir}"
            )

        plural_slug, _ = spanish_plural(model_name)

        self.stdout.write(
            self.style.NOTICE(
                f"⚡ Automatizando CRUD para '{model_name}' en '{app_name}'..."
            )
        )

        # 1. Actualizar models.py
        models_file = app_dir / "models.py"
        self._process_models(models_file, model_name)

        # 2. Actualizar serializers.py
        serializers_file = app_dir / "serializers.py"
        self._process_serializers(serializers_file, model_name)

        # 3. Actualizar views.py
        views_file = app_dir / "views.py"
        self._process_views(views_file, model_name)

        # 4. Actualizar urls.py
        urls_file = app_dir / "urls.py"
        self._process_urls(urls_file, model_name, plural_slug)

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ ¡CRUD completado con éxito!\n"
                f"    - Modelo: {model_name}\n"
                f"    - Serializer: {model_name}Serializer\n"
                f"    - ViewSet: {model_name}ViewSet\n"
                f"    - Ruta API: /api/{plural_slug}/"
            )
        )

    """
    Procesa y añade el modelo de datos correspondiente a models.py si no existe.

    @param file_path - Ruta al archivo models.py de la aplicación.
    @param model_name - Nombre del modelo en PascalCase.
    @returns None - Modifica y guarda el archivo en disco.
    """

    def _process_models(self, file_path: Path, model_name: str):
        content = file_path.read_text(encoding="utf-8")
        if f"class {model_name}(" in content:
            self.stdout.write(
                f"  [models.py] La clase '{model_name}' ya existe. (Omitiendo creación de modelo)"
            )
            return

        model_code = f"""

class {model_name}(models.Model):
    \"\"\"
    Representa la entidad {model_name}.
    \"\"\"
    nombre = models.CharField(
        max_length=150,
        help_text="Nombre o identificador representativo"
    )
    descripcion = models.TextField(
        null=True,
        blank=True,
        help_text="Descripción o detalles adicionales"
    )
    creado_en = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora de creación"
    )

    def __str__(self):
        return str(self.nombre)

    class Meta:
        verbose_name = "{model_name}"
        verbose_name_plural = "{model_name}s"
"""
        content += model_code
        file_path.write_text(content, encoding="utf-8")
        self.stdout.write(
            self.style.SUCCESS(f"  [models.py] Modelo '{model_name}' añadido.")
        )

    """
    Procesa y añade el serializer correspondiente a serializers.py.

    @param file_path - Ruta al archivo serializers.py de la aplicación.
    @param model_name - Nombre del modelo asociado.
    @returns None - Modifica y guarda el archivo en disco.
    """

    def _process_serializers(self, file_path: Path, model_name: str):
        content = file_path.read_text(encoding="utf-8")
        serializer_name = f"{model_name}Serializer"

        content = add_to_import(content, "from .models import", model_name)

        if f"class {serializer_name}(" not in content:
            serializer_code = f"""

class {serializer_name}(serializers.ModelSerializer):
    \"\"\"Serializa todos los campos del modelo {model_name}.\"\"\"

    class Meta:
        model = {model_name}
        fields = '__all__'
"""
            content += serializer_code
            self.stdout.write(
                self.style.SUCCESS(f"  [serializers.py] '{serializer_name}' añadido.")
            )
        else:
            self.stdout.write(f"  [serializers.py] '{serializer_name}' ya existe.")

        file_path.write_text(content, encoding="utf-8")

    """
    Procesa y añade el ViewSet correspondiente a views.py.

    @param file_path - Ruta al archivo views.py de la aplicación.
    @param model_name - Nombre del modelo asociado.
    @returns None - Modifica y guarda el archivo en disco.
    """

    def _process_views(self, file_path: Path, model_name: str):
        content = file_path.read_text(encoding="utf-8")
        viewset_name = f"{model_name}ViewSet"
        serializer_name = f"{model_name}Serializer"

        content = add_to_import(content, "from .models import", model_name)
        content = add_to_import(content, "from .serializers import", serializer_name)

        if f"class {viewset_name}(" not in content:
            viewset_code = f"""

class {viewset_name}(viewsets.ModelViewSet):
    \"\"\"
    ViewSet para el modelo {model_name}.
    Proporciona operaciones CRUD completas.
    \"\"\"
    queryset = {model_name}.objects.all()
    serializer_class = {serializer_name}
"""
            content += viewset_code
            self.stdout.write(
                self.style.SUCCESS(f"  [views.py] '{viewset_name}' añadido.")
            )
        else:
            self.stdout.write(f"  [views.py] '{viewset_name}' ya existe.")

        file_path.write_text(content, encoding="utf-8")

    """
    Registra la ruta del ViewSet en el enrutador dentro de urls.py.

    @param file_path - Ruta al archivo urls.py de la aplicación.
    @param model_name - Nombre del modelo asociado.
    @param plural_slug - Ruta URL en formato slug plural.
    @returns None - Modifica y guarda el archivo en disco.
    """

    def _process_urls(self, file_path: Path, model_name: str, plural_slug: str):
        content = file_path.read_text(encoding="utf-8")
        viewset_name = f"{model_name}ViewSet"

        content = add_to_import(content, "from .views import", viewset_name)

        route_register = f"router.register(r'{plural_slug}', {viewset_name})"

        if route_register not in content:
            pattern = r"(router\.register\([^\n]+\)\n)"
            matches = list(re.finditer(pattern, content))
            if matches:
                last_match = matches[-1]
                insert_pos = last_match.end()
                content = (
                    content[:insert_pos] + f"{route_register}\n" + content[insert_pos:]
                )
            else:
                if "urlpatterns = [" in content:
                    content = content.replace(
                        "urlpatterns = [", f"{route_register}\n\nurlpatterns = ["
                    )
                else:
                    content += f"\n{route_register}\n"
            self.stdout.write(
                self.style.SUCCESS(
                    f"  [urls.py] Ruta '/api/{plural_slug}/' registrada."
                )
            )
        else:
            self.stdout.write(f"  [urls.py] Ruta '/api/{plural_slug}/' ya registrada.")

        file_path.write_text(content, encoding="utf-8")


"""
Punto de entrada ejecutable desde CLI para invocar el comando make_crud.

@param - No recibe parámetros directos.
@returns None - Configura el entorno de Django y ejecuta el comando.
"""


def main():
    src_dir = Path(__file__).resolve().parent.parent.parent.parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "poki_koa.settings")
    from django.core.management import execute_from_command_line

    sys.argv = [sys.argv[0], "make_crud"] + sys.argv[1:]
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
