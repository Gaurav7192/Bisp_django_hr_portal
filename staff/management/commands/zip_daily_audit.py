import os
from datetime import datetime, timedelta
import pytz
import zipfile
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Zips yesterday's audit logs and deletes the txt files"

    def handle(self, *args, **kwargs):
        AUDIT_DIR = "audit_logs"
        ZIP_DIR = os.path.join(AUDIT_DIR, "zipped")
        os.makedirs(ZIP_DIR, exist_ok=True)

        ist = pytz.timezone("Asia/Kolkata")
        yesterday = (datetime.now(ist) - timedelta(days=1)).date()
        # Changed line for the desired zip file name format
        zip_file_name = yesterday.strftime("%d-%m-%Y") + " zipped audit.zip"
        zip_path = os.path.join(ZIP_DIR, zip_file_name)
        with zipfile.ZipFile(zip_path, "w") as zipf:
            for file in os.listdir(AUDIT_DIR):
                if file.endswith(f"{yesterday}.txt"):
                    file_path = os.path.join(AUDIT_DIR, file)
                    zipf.write(file_path, arcname=file)
                    os.remove(file_path)

        self.stdout.write(self.style.SUCCESS(f"Archived logs for {yesterday}"))
