#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "==> Upgrading pip and installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Collecting static assets..."
python manage.py collectstatic --noinput

echo "==> Running database migrations..."
python manage.py migrate --noinput

echo "==> Ensuring admin user account exists..."
python manage.py ensure_admin
