#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

import os
import certifi
import os
os.environ['SSL_CERT_FILE'] = r'C:\Users\DELL\AppData\Local\Programs\Python\Python313\Lib\site-packages\certifi\cacert.pem'


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newproject.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
