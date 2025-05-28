import os
import datetime
import zipfile
from django.conf import settings
from django.core.management.base import BaseCommand
import logging  # Import logging module for internal messages

# Configure a logger for the cleanup script itself
cleanup_logger = logging.getLogger('audit_cleanup_script')
cleanup_logger.setLevel(logging.INFO)  # Log level for the script's own messages


# You might want to add a file handler to this logger to log cleanup script's activity
# For simplicity, we'll use stdout/stderr for now as in BaseCommand

class Command(BaseCommand):
    help = 'Archives all individual daily audit logs for the previous day into a single ZIP file and deletes original files.'

    def handle(self, *args, **kwargs):
        # Define directories for logs and archives. Reads from settings or uses defaults.
        # Ensure these are configured in your Django settings.py if you want custom paths.
        audit_log_dir = getattr(settings, 'AUDIT_LOG_DIR', os.path.join(settings.BASE_DIR, 'audit_logs'))
        audit_archive_dir = getattr(settings, 'AUDIT_ARCHIVE_DIR', os.path.join(settings.BASE_DIR, 'audit_archives'))

        os.makedirs(audit_archive_dir, exist_ok=True)  # Ensure archive directory exists

        if not os.path.exists(audit_log_dir):
            self.stdout.write(
                self.style.WARNING(f"Audit log directory not found: '{audit_log_dir}'. Nothing to archive."))
            return

        # Calculate yesterday's date (since the script runs at 00:00:00 for the previous day)
        archive_date = datetime.date.today() - datetime.timedelta(days=1)
        archive_date_str = archive_date.strftime('%Y-%m-%d')

        # Name the ZIP file for the previous day's audits
        archive_filename = f"daily_employee_audits_{archive_date_str}.zip"
        archive_filepath = os.path.join(audit_archive_dir, archive_filename)

        log_files_to_archive = []
        # Iterate through files in the audit log directory
        for filename in os.listdir(audit_log_dir):
            # Check if the file matches the naming convention for the previous day
            # (e.g., any_email_YYYY-MM-DD_audit.log)
            if filename.endswith(f"_{archive_date_str}_audit.log"):
                log_files_to_archive.append(os.path.join(audit_log_dir, filename))

        if not log_files_to_archive:
            self.stdout.write(self.style.WARNING(
                f"No individual employee audit log files found for {archive_date_str} to archive."))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting daily employee audit log archiving for {archive_date_str} at {datetime.datetime.now()}"))

        try:
            # Create the ZIP archive
            with zipfile.ZipFile(archive_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in log_files_to_archive:
                    # Add file to ZIP, using just its filename (arcname)
                    zipf.write(file_path, arcname=os.path.basename(file_path))
                    self.stdout.write(self.style.SUCCESS(f"Added '{os.path.basename(file_path)}' to archive."))

            self.stdout.write(self.style.SUCCESS(f"Successfully created archive: {archive_filepath}"))

            # Delete original log files after successful zipping
            deleted_files_count = 0
            for file_path in log_files_to_archive:
                try:
                    os.remove(file_path)  # <<< THIS LINE DELETES THE FILE!
                    self.stdout.write(self.style.SUCCESS(f"Deleted original log file: {os.path.basename(file_path)}"))
                    deleted_files_count += 1
                except Exception as e:
                    self.stderr.write(
                        self.style.ERROR(f"Failed to delete original file '{os.path.basename(file_path)}': {e}"))

            self.stdout.write(self.style.SUCCESS(
                f"Finished daily employee audit log archiving. Archived {len(log_files_to_archive)} files, deleted {deleted_files_count} original files."))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"CRITICAL ERROR: Failed to create audit log archive: {e}"))
            self.stderr.write(self.style.ERROR("Original log files were NOT deleted due to archiving failure."))

# ... (rest of your daily_audit_cleanup.py code is above this)

# --- THIS BLOCK ALLOWS THE SCRIPT TO BE RUN DIRECTLY ---
if __name__ == '__main__':
    import os
    import sys

    # Calculate the path to your project's root directory.
    # This navigates up from 'commands' to 'management' then to 'newproject'.
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Add the project root to Python's system path.
    # This tells Python where to find your 'newproject' package.
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from django.conf import settings
    from django import setup

    # Set the Django settings module environment variable.
    # 'newproject.settings' assumes your main project folder is named 'newproject'.
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newproject.settings')

    # Initialize Django apps and settings.
    try:
        setup()
    except Exception as e:
        print(f"Error during Django setup: {e}", file=sys.stderr)
        sys.exit(1) # Exit with an error code if setup fails

    # Run the command.
    try:
        Command().handle()
    except Exception as e:
        print(f"Error running the audit cleanup command: {e}", file=sys.stderr)
        sys.exit(1) # Exit with an error code if command fails