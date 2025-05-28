# staff/management/commands/daily_audit_cleanup.py
from django.core.management.base import BaseCommand
from django.conf import settings
import os, shutil, zipfile
from datetime import datetime

class Command(BaseCommand):
    help = "Zip and delete daily audit logs"

    def handle(self, *args, **kwargs):
        log_dir = os.path.join(settings.BASE_DIR, 'audit_logs')
        today = datetime.now().strftime('%Y-%m-%d')
        zip_path = os.path.join(log_dir, f"{today}.zip")

        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file_name in os.listdir(log_dir):
                if file_name.endswith('.txt'):
                    file_path = os.path.join(log_dir, file_name)
                    zipf.write(file_path, arcname=file_name)
                    os.remove(file_path)
        self.stdout.write(self.style.SUCCESS(f"Zipped and cleaned logs for {today}"))
