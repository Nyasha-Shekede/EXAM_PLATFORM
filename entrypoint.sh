#!/bin/sh
set -eu

# Explicit one-off commands must not trigger unrelated migrations or account changes.
if [ "$#" -gt 0 ]; then
    exec "$@"
fi

# Suitable for one web instance. For multiple replicas use a single pre-deploy migration job.
if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    python manage.py migrate --noinput
fi
python manage.py ensure_admin
exec gunicorn config.wsgi:application     --bind "0.0.0.0:${PORT:-8000}"     --workers "${WEB_CONCURRENCY:-3}"     --timeout 60     --access-logfile -     --error-logfile -
