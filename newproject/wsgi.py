"""
WSGI config for newproject project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
import os
import certifi
os.environ['SSL_CERT_FILE'] = certifi.where()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newproject.settings')

application = get_wsgi_application()
