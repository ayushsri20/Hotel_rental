web: gunicorn -w 4 -b 0.0.0.0:${PORT} hotel_project.wsgi:application
release: python manage.py migrate --noinput && python manage.py collectstatic --noinput
