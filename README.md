# Poki Koa — Sistema de Monitoreo Neonatal

> **Poki** (niño/hijo) · **Koa** (alegría, estar contento) — Lengua Rapa Nui

Sistema de monitoreo inteligente de cunas neonatales. El nombre **Poki Koa** busca entregar una identidad nacional al proyecto usando palabras de la lengua Rapa Nui, mientras que el **Moai** como elemento visual refuerza conceptos de protección, cuidado y vigilancia permanente.

## Arquitectura

```
Backend (este repositorio)       Frontend (repositorio aparte)
┌─────────────────────────┐      ┌────────────────────────┐
│  Django REST Framework  │◄────►│  React + Vite          │
│  SQLite (desarrollo)    │      │  Puerto: 5173          │
│  Puerto: 8000           │      └────────────────────────┘
└─────────────────────────┘

API REST disponible en: http://127.0.0.1:8000/api/
  GET/POST  /api/medicos/
  GET/POST  /api/bebes/
  GET/POST  /api/cunas/
  (+ endpoints de detalle /{id}/ para cada uno)
```

## Requisitos

- [Git](https://git-scm.com/)
- Python 3.10 o superior
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) para gestionar el entorno virtual y las dependencias

> Si `uv` no está instalado, puedes obtenerlo con:
> ```bash
> curl -LsSf https://astral.sh/uv/install.sh | sh
> ```
- [`Django`] es un framework web de Python
- [`Django`](https://docs.astral.sh/uv/getting-started/installation/) ver las versiones de Python compatibles con cada versión de Django

> Si `Django` no está instalado, puedes obtenerlo para Linux / macOS con:
> ```bash
> python -m pip install Django==6.1
> ```
> Puedes obtenerlo para Windows con:
> ```bash
> py -m pip install Django==6.1
> ```
> Para verificar que Python puede ver Django, escribe python desde tu terminal. Luego, en el indicador de Python, intenta importar Django:
> ```bash
> >>> importar django
>>>> print(django.get_version())
>6.1
> ```

## Instalación y ejecución

### 1. Clonar el repositorio

```bash
git clone https://github.com/Asulx/poki-koa-backend.git
cd poki-koa-backend
```

### 2. Verificar la versión de Python

```bash
python --version
```

### 3. Sincronizar las dependencias del proyecto

Esto crea el entorno virtual `.venv/` e instala todas las dependencias automáticamente:

```bash
uv sync
```

### 4. Aplicar las migraciones de base de datos

Solo es necesario la primera vez o cuando se agregan nuevos modelos:

```bash
uv run mamoru migrate
```

### 5. Ejecutar el servidor de desarrollo

```bash
uv run mamoru
```

El servidor estará disponible en: **http://127.0.0.1:8000/**

## Otros comandos útiles

| Comando | Descripción |
|---|---|
| `uv run mamoru` | Inicia el servidor de desarrollo en el puerto 8000 |
| `uv run mamoru migrate` | Aplica migraciones pendientes a la base de datos |
| `uv run mamoru test` | Ejecuta la suite de pruebas unitarias |
| `uv run mamoru makemigrations` | Genera nuevas migraciones tras modificar modelos |
| `uv run mamoru createsuperuser` | Crea un usuario administrador para el panel `/admin/` |

## Estructura del proyecto

```
.
├── pyproject.toml          # Dependencias, versión del proyecto y comando `mamoru`
├── uv.lock                 # Versiones exactas de dependencias (no editar manualmente)
├── .python-version         # Versión de Python gestionada por uv
└── src/
    ├── manage.py           # CLI alternativa de Django (uso directo sin uv)
    ├── db.sqlite3          # Base de datos SQLite (desarrollo)
    ├── poki_koa/           # Configuración central del proyecto Django
    │   ├── settings.py     # Ajustes globales (BD, apps, CORS, etc.)
    │   ├── urls.py         # Rutas raíz: /admin/ y /api/
    │   ├── wsgi.py         # Punto de entrada para servidores WSGI (producción)
    │   └── main.py         # Función `main()` que activa el comando `mamoru`
    └── cunas/              # App principal del sistema
        ├── models.py       # Modelos: Medico, Bebe, Cuna
        ├── serializers.py  # Serializadores JSON para la API REST
        ├── views.py        # ViewSets: endpoints CRUD automáticos
        ├── urls.py         # Router con rutas /api/medicos/, /api/bebes/, /api/cunas/
        ├── admin.py        # Registro de modelos en el panel de administración
        ├── tests.py        # Pruebas unitarias de los modelos
        └── migrations/     # Migraciones de base de datos (generadas automáticamente)
```
