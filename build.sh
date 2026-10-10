#!/usr/bin/env bash
set -euo pipefail
# Optional native-Python Render build. No database or administrator writes during build.
python -m pip install -r requirements.txt
python manage.py collectstatic --noinput
