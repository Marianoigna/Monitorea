"""
WSGI config for CONTROL_TEMPERATURA project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CONTROL_TEMPERATURA.settings')

application = get_wsgi_application()
