release: python manage.py migrate --noinput
web: gunicorn parcelles_veto.wsgi:application --bind 0.0.0.0:$PORT --workers 3