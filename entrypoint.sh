#!/bin/bash
set -e

echo ">>> Collecting static files..."
python manage.py collectstatic --noinput

echo ">>> Running migrations..."
python manage.py migrate

echo ">>> Creating superuser if not exists..."
python manage.py shell << 'EOF'
import os
from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
email    = os.environ.get('DJANGO_SUPERUSER_EMAIL')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

if username and not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print("Superuser created.")
else:
    print("Superuser already exists or USERNAME not set, skipping.")
EOF

echo ">>> Starting services..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf