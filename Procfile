web: ./scripts/railway_init.sh && gunicorn -w 4 -b 0.0.0.0:${PORT:-8000} hotel_project.wsgi:application
release: python manage.py migrate --noinput
