import os
from pathlib import Path
import dj_database_url


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

# Configuration dynamique de la base de données

DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Static files
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')