#!/bin/bash
set -e

echo ">>> Collecting static files..."
python manage.py collectstatic --noinput

echo ">>> Running migrations..."
python manage.py migrate

echo ">>> Starting services..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf