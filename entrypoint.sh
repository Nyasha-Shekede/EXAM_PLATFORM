#!/bin/sh
set -e

# Run migrations and ensure superuser on container startup
echo "==> Running database migrations..."
python manage.py migrate --noinput

echo "==> Ensuring admin user account..."
python manage.py ensure_admin

if [ "$#" -gt 0 ]; then
    echo "==> Executing command: $@"
    exec "$@"
else
    echo "==> Starting Gunicorn on port ${PORT:-8000}..."
    exec gunicorn config.wsgi:application \
        --bind "0.0.0.0:${PORT:-8000}" \
        --workers "${WEB_CONCURRENCY:-3}" \
        --timeout 60 \
        --access-logfile -
fi
