# Mamoru - Lectura y manejo de datos
## Requisitos

- Git
- Python 3.14
- `uv` para manejar el entorno del backend
- Node.js 20 o superior con `npm`

Si `uv` no está instalado, puedes obtenerlo desde https://docs.astral.sh/uv/getting-started/installation/.

## Clonar el repositorio

```bash
git clone https://github.com/Asulx/sistema-monitoreo-cuna-inteligente
cd sistema-monitoreo-cuna-inteligente
```

## Inicializar el backend

1. Verifica la versión de Python instalada.

```bash
python --version
```

2. Sincroniza las dependencias del proyecto.

```bash
uv sync
```

3. Ejecuta el punto de entrada del backend.

```bash
uv run mamoru
```