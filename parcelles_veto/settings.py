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
    'rest_framework',
    'corsheaders',
    'accounts',
    'clients',
    'animaux',
    'consultations',
    'pharmacie',
    'fournisseurs',
    'ventes',
    'caisse',
    'dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Servir les fichiers statiques
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if os.getenv("CORS_ALLOWED_ORIGINS") else []

ROOT_URLCONF = 'parcelles_veto.urls'

WSGI_APPLICATION = 'parcelles_veto.wsgi.application'
ASGI_APPLICATION = 'parcelles_veto.asgi.application'

# ============================
# Base de données PostgreSQL
# ============================


# ============================
# Base de données (Fallback SQLite pour le dev local)
# ============================
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# ============================
# Static files (CSS, JS, Images)
# ============================
STATIC_URL = '/static/'

# Dossiers statiques globaux (s'il existe un dossier 'static' à la racine)
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
] if os.path.exists(os.path.join(BASE_DIR, 'static')) else []

# Dossier cible du collectstatic
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Configuration WhiteNoise assouplie (évite les erreurs 500)
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

AUTH_USER_MODEL = 'accounts.Utilisateur'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Redirection vers la page de login si l'utilisateur n'est pas connecté
LOGIN_URL = '/accounts/login/'

# Redirection vers le tableau de bord après une connexion réussie
LOGIN_REDIRECT_URL = '/'

# Redirection après la déconnexion
LOGOUT_REDIRECT_URL = '/accounts/login/'