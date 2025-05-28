import os
import zipfile
import shutil
from datetime import datetime


def compress_logs():
    # Get current date to generate zip filename
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())  # Start of the week (Monday)
    week_end = week_start + timedelta(days=6)  # End of the week (Sunday)

    # Create the zip filename
    zip_filename = f"logs_{week_start.strftime('%Y-%m-%d')}_to_{week_end.strftime('%Y-%m-%d')}.zip"

    # Compress all user log files
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        log_folder = "logs"
        for root, dirs, files in os.walk(log_folder):
            for file in files:
                if file.endswith(".log"):
                    zipf.write(os.path.join(root, file), file)  # Add the log file to zip

    # Move zip file to a proper directory (Optional)
    shutil.move(zip_filename, "archived_logs")
    print(f"Logs have been compressed to {zip_filename}")


# Run the compression function
if __name__ == "__main__":
    compress_logs()
