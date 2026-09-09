import os

# ============================
# Django - Configuration générale
# ============================
SECRET_KEY = os.getenv('SECRET_KEY', 'mfc@ne*-pvr^sn8u-kd6&tva%x=+(a^og%7kjylq8zf-p%l&mf')
DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "parcelleveto-thies.up.railway.app,localhost,127.0.0.1").split(",")

CSRF_TRUSTED_ORIGINS = [
    'https://parcelleveto-thies.up.railway.app',
]

# ============================
# Base de données PostgreSQL
# ============================
DB_NAME = os.getenv('DB_NAME', 'parcelles_veto')
DB_USER = os.getenv('DB_USER', 'parcelles_veto_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'FV3OqvCeevjU5A1GDZatNoaU6MGdLkNr')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')

# ============================
# CORS
# ============================
CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]