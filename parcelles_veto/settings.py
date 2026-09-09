import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ============================
# General Settings
# ============================
SECRET_KEY = os.getenv('SECRET_KEY', 'mfc@ne*-pvr^sn8u-kd6&tva%x=+(a^og%7kjylq8zf-p%l&mf')
DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "parcelleveto-thies.up.railway.app,localhost,127.0.0.1").split(",")

CSRF_TRUSTED_ORIGINS = [
    'https://parcelleveto-thies.up.railway.app',
]

# ============================
# Application definition
# ============================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Vos applications personnalisées ici
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Ligne essentielle manquante :
ROOT_URLCONF = 'parcelles_veto.urls'

WSGI_APPLICATION = 'parcelles_veto.wsgi.application'
ASGI_APPLICATION = 'parcelles_veto.asgi.application'

# ============================
# Base de données PostgreSQL
# ============================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'parcelles_veto'),
        'USER': os.getenv('DB_USER', 'parcelles_veto_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'FV3OqvCeevjU5A1GDZatNoaU6MGdLkNr'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# Static files
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')