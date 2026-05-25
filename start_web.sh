#!/usr/bin/env bash
set -e

export DJANGO_SETTINGS_MODULE=CONTROL_TEMPERATURA.settings
export MQTT_AUTOSTART=1

cd CONTROL_HELADERAS
python manage.py collectstatic --noinput
python manage.py migrate --noinput
exec daphne -b 0.0.0.0 -p "$PORT" CONTROL_TEMPERATURA.asgi:application
