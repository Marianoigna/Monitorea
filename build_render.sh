#!/usr/bin/env bash
set -e

pip install -r requirements.txt

export DJANGO_SETTINGS_MODULE=MONITOREA.settings

cd CORE
python manage.py collectstatic --noinput
