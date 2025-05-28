import os
import sys

# Add your project root to the Python path if it's not already there.
# This ensures Python can find your 'management' folder and the script within it.
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set the Django settings module environment variable
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newproject.settings')

# Import and run your daily_audit_cleanup script
try:
    # Django's setup() must be called *after* settings are configured,
    # but *before* you import Django components that rely on them (like your command)
    from django import setup
    setup() # Initialize Django apps

    from management.commands import daily_audit_cleanup
    daily_audit_cleanup.Command().handle()
except Exception as e:
    # Basic error logging if direct execution fails
    print(f"Error running daily_audit_cleanup: {e}", file=sys.stderr)
    sys.exit(1) # Exit with an error code

import os
import sys

# Add your project root to the Python path. This is crucial for finding 'newproject.settings'.
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set the Django settings module environment variable
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newproject.settings')

try:
    # Initialize Django apps. This must be called AFTER settings are configured.
    from django import setup
    setup()

    # Import and run your daily_audit_cleanup command
    # This import path 'management.commands.daily_audit_cleanup' works because
    # the project_root is now in sys.path, making 'management' a top-level package.
    from management.commands import daily_audit_cleanup
    daily_audit_cleanup.Command().handle()

except Exception as e:
    print(f"Error running daily_audit_cleanup: {e}", file=sys.stderr)
    sys.exit(1) # Exit with an error code