web: cd hotel_project && gunicorn -w 4 -b 0.0.0.0:${PORT} hotel_project.wsgi:application
release: cd hotel_project && python manage.py migrate --noinput && python manage.py collectstatic --noinput --clear
