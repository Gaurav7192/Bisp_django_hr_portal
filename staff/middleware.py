import os
import zipfile
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Compress and delete old audit log files'

    def handle(self, *args, **kwargs):
        log_dir = os.path.join(settings.BASE_DIR, 'audit_logs')
        if not os.path.exists(log_dir):
            self.stdout.write(self.style.WARNING('No log directory found.'))
            return

        # Get yesterday's date
        yesterday = datetime.now() - timedelta(days=1)
        date_str = yesterday.strftime('%Y-%m-%d')

        # Loop through all log files for users
        for log_file in os.listdir(log_dir):
            if log_file.endswith(f'_{date_str}.log'):
                log_file_path = os.path.join(log_dir, log_file)
                zip_file_path = os.path.join(log_dir, f'{log_file[:-4]}_{date_str}.zip')

                # Compress the log file
                with zipfile.ZipFile(zip_file_path, 'w') as zip_file:
                    zip_file.write(log_file_path, os.path.basename(log_file_path))

                # Delete the old log file
                os.remove(log_file_path)
                self.stdout.write(self.style.SUCCESS(f'Compressed and deleted: {log_file}'))
