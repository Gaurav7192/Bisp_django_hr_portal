"""
ASGI config for newproject project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
import os
import certifi
os.environ['SSL_CERT_FILE'] = certifi.where()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newproject.settings')

application = get_asgi_application()
