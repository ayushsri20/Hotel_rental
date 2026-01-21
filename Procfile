web: cd hotel_project && python manage.py migrate --noinput --verbosity 2 && python manage.py collectstatic --noinput --clear --verbosity 2 && gunicorn -w 4 -b 0.0.0.0:${PORT} hotel_project.wsgi:application
release: echo "Migrations and collectstatic run in web process - no release phase needed"
