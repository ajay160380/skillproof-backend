#!/usr/bin/env bash
# exit on error
set -o errexit

# Apply database migrations
python manage.py migrate --no-input

# Collect static files
python manage.py collectstatic --no-input

# Start Celery worker in the background only if eager mode is explicitly disabled
if [ "${CELERY_TASK_ALWAYS_EAGER}" = "False" ] || [ "${CELERY_TASK_ALWAYS_EAGER}" = "false" ]; then
    celery -A config worker --loglevel=info --concurrency=1 --pool=solo &
fi

# Start Gunicorn in the foreground
# Render automatically injects the PORT environment variable
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 120
