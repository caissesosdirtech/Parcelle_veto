"""
Django settings for parcelles_veto project.
Version production - lit la configuration depuis les variables d'environnement.
"""

from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

# Initialise django-environ et lit le fichier .env
env = environ.Env(
    DEBUG=(bool, False)
)
environ.Env.read_env(BASE_DIR / '.env')


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['127.0.0.1', 'localhost'])


# Application definition

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

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    )
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # doit être placé tôt, avant CommonMiddleware
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# CORS - en production, on restreint aux domaines connus (jamais ALLOW_ALL_ORIGINS)
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])

# Si ton app mobile Flutter appelle l'API directement (pas depuis un navigateur),
# CORS ne s'applique pas aux apps natives - seulement aux appels depuis un navigateur web.
# Donc CORS_ALLOWED_ORIGINS doit lister uniquement les origines de ton app WEB Flutter.


ROOT_URLCONF = 'parcelles_veto.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'parcelles_veto.wsgi.application'


# Database
# En production : PostgreSQL, configuré via variables d'environnement.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST', default='db'),  # 'db' = nom du service dans docker-compose
        'PORT': env('DB_PORT', default='5432'),
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTH_USER_MODEL = 'accounts.Utilisateur'


# Internationalization
LANGUAGE_CODE = 'fr-fr'  # ajusté au français, change si besoin
TIME_ZONE = 'Africa/Dakar'  # ajusté à ta timezone réelle - important pour les rendez-vous/horaires
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'  # requis en prod pour `collectstatic`

# Media files (photos d'animaux, documents uploadés par les utilisateurs)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# Sécurité additionnelle recommandée en production (actif seulement si DEBUG=False)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True