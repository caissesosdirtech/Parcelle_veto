import os
from pathlib import Path
import dj_database_url


BASE_DIR = Path(__file__).resolve().parent.parent


FIREBASE_SERVICE_ACCOUNT_PATH = os.path.join(BASE_DIR, "firebase-service-account.json")

# ============================
# General Settings
# ============================
# DEBUG : activé par défaut en local. En production (Railway), créez la
# variable DEBUG=False pour ne jamais afficher le détail des erreurs.
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# Clé secrète : OBLIGATOIRE en production (variable SECRET_KEY sur Railway).
# Plus aucune clé n'est écrite dans le code ; en local (DEBUG) une clé de
# développement est utilisée.
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-uniquement-cle-locale-non-secrete"
    else:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured("La variable d'environnement SECRET_KEY est obligatoire.")

# Domaines autorisés : l'adresse Railway est conservée pour les anciennes
# versions de l'app, le domaine personnalisé est ajouté.
DOMAINES = [
    "parcellesveto-thies.vet",
    "www.parcellesveto-thies.vet",
    "parcelleveto-thies.up.railway.app",
    "parcelleveto-production.up.railway.app",
]

ALLOWED_HOSTS = os.getenv(
    "ALLOWED_HOSTS", ",".join(DOMAINES + ["localhost", "127.0.0.1"])
).split(",")

CSRF_TRUSTED_ORIGINS = [f"https://{d}" for d in DOMAINES]

# ============================
# Sécurité HTTPS (production uniquement)
# ============================
# Railway reçoit le HTTPS et transmet la requête en HTTP à Django en
# indiquant le protocole d'origine dans X-Forwarded-Proto.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
if not DEBUG:
    # Toute adresse http:// est redirigée vers https://
    SECURE_SSL_REDIRECT = True
    # Les cookies de session et CSRF ne circulent qu'en HTTPS
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # Le navigateur retient d'utiliser uniquement HTTPS pendant 1 an
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", 31536000))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# ============================
# Cache des tentatives de connexion
# ============================
# Stocké dans la base pour être partagé entre les processus gunicorn
# (table créée par « python manage.py createcachetable » dans le Procfile).
CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "connexions": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "cache_connexions",
    },
}

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
    'notifications',
    'parametres',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Servir les fichiers statiques
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # Connexion obligatoire partout (session web ou jeton JWT de l'app) ;
    # bloque réellement quand la variable REQUIRE_LOGIN=True est définie.
    'parcelles_veto.middleware.ConnexionObligatoireMiddleware',
    # Blocage temporaire après trop d'essais de mot de passe (site et app)
    'parcelles_veto.middleware.LimiteConnexionMiddleware',
    # Refus des requêtes API envoyées depuis un autre site (sans jeton JWT)
    'parcelles_veto.middleware.ProtectionOrigineMiddleware',
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

# ============================
# Django REST Framework
# ============================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
}

# Durée de vie des jetons de l'app mobile : 1 jour (rafraîchi automatiquement
# au lancement de l'app), reconnexion obligatoire au bout de 30 jours.
from datetime import timedelta
SIMPLE_JWT = {
    # Date de dernière connexion à jour aussi pour les connexions depuis l'app
    "UPDATE_LAST_LOGIN": True,
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
}

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
                'parametres.context_processors.clinique',
                'dashboard.context_processors.menu',
            ],
        },
    },
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# settings.py

# URL où l'utilisateur est redirigé après connexion réussie
LOGIN_REDIRECT_URL = '/'  # Ou le nom de la route du dashboard, ex: 'consultations_list'

# URL de la page de connexion
LOGIN_URL = '/accounts/login/'

# URL après déconnexion
LOGOUT_REDIRECT_URL = '/accounts/login/'

TIME_ZONE = "Africa/Dakar"