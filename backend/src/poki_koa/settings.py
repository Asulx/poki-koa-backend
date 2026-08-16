from pathlib import Path
import os
import sys

# Ruta base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# Agrega la carpeta src al PYTHONPATH
sys.path.append(str(BASE_DIR))

# CLAVE DE SEGURIDAD (Solo para desarrollo local)
SECRET_KEY = 'django-insecure-mamoru-clave-de-desarrollo-local'

# MODO DEBUG (True para desarrollo, False en producción)
DEBUG = True

ALLOWED_HOSTS = ['*']

# APLICACIONES INSTALADAS
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Aplicaciones de terceros
    'rest_framework',
    'corsheaders',
    # Tus aplicaciones
    'cunas', 
]

# MIDDLEWARES
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware', # <-- Permite la conexión con React
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# CONFIGURACIÓN DE CORS (Orígenes permitidos para Vite/React)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

ROOT_URLCONF = 'poki_koa.urls'

# CONFIGURACIÓN DE PLANTILLAS (Requerido por la app 'admin' de Django)
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'poki_koa.wsgi.application'

# BASE DE DATOS
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# CONTRASEÑAS Y VALIDACIÓN (Por defecto)
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# INTERNACIONALIZACIÓN (Idioma y zona horaria)
LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'America/Santiago' 
USE_I18N = True
USE_TZ = True

# ARCHIVOS ESTÁTICOS (CSS, JavaScript, Imágenes)
STATIC_URL = 'static/'

# TIPO DE CAMPO AUTOMÁTICO POR DEFECTO
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'