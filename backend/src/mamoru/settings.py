from pathlib import Path
import os
import sys

# Ruta base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# Agrega la carpeta src al PYTHONPATH
sys.path.append(str(BASE_DIR))

SECRET_KEY = 'django-insecure-mamoru-clave-de-desarrollo-local'

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Librerías de terceros
    'rest_framework',
    'corsheaders',
    # Tus aplicaciones
    'cunas',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Debe ir al inicio
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Permitir conexiones desde React (Vite)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

ROOT_URLCONF = 'mamoru.urls'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}