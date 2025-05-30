# staff/management/commands/archive_logs.py
import os
import zipfile
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Archive audit logs and remove text files'

    def handle(self, *args, **kwargs):
        log_dir = os.path.join(settings.BASE_DIR, 'logs', 'audit')
        date_str = datetime.now().strftime('%Y-%m-%d')
        zip_file = os.path.join(log_dir, f'audit_{date_str}.zip')

        with zipfile.ZipFile(zip_file, 'w') as archive:
            for filename in os.listdir(log_dir):
                if filename.endswith('.txt') and date_str in filename:
                    file_path = os.path.join(log_dir, filename)
                    archive.write(file_path, arcname=filename)
                    os.remove(file_path)

        self.stdout.write(self.style.SUCCESS(f'Archived logs to {zip_file}'))
