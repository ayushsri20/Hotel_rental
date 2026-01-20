web: gunicorn hotel_project.wsgi:application --workers 4 --worker-class sync --bind 0.0.0.0:${PORT:-8000} --timeout 60 --access-logfile - --error-logfile -
release: python manage.py migrate --noinput && python manage.py collectstatic --noinput
