web: cd hotel_project && python manage.py migrate --noinput && python manage.py collectstatic --noinput --clear && gunicorn -w 4 -b 0.0.0.0:${PORT} hotel_project.wsgi:application
release: echo "Release phase: skipping (migrations and collectstatic run in web process)"
