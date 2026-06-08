#!/usr/bin/env bash
set -e

export DJANGO_SETTINGS_MODULE=MONITOREA.settings
export MQTT_AUTOSTART=1

cd CORE
python manage.py collectstatic --noinput
python manage.py migrate --noinput
exec daphne -b 0.0.0.0 -p "$PORT" MONITOREA.asgi:application
