import os
import datetime
import logging
from django.conf import settings

# Configure a dedicated logger for employee audits
employee_audit_logger = logging.getLogger('employee_audit')
employee_audit_logger.setLevel(logging.INFO) # Set to INFO, DEBUG, etc. as needed
employee_audit_logger.propagate = False # Prevent messages from going to default Django loggers

def get_employee_audit_filepath(employee_email):
    """
    Generates the path for an employee's daily audit log file.
    Logs will be stored in a subfolder like: audit_logs/john.doe_at_example_dot_com_YYYY-MM-DD_audit.log
    """
    # Define where audit logs should be stored. Reads from settings or defaults to 'audit_logs' in BASE_DIR.
    audit_log_dir = getattr(settings, 'AUDIT_LOG_DIR', os.path.join(settings.BASE_DIR, 'audit_logs'))
    os.makedirs(audit_log_dir, exist_ok=True) # Ensure this directory exists

    today_str = datetime.date.today().strftime('%Y-%m-%d')
    # Sanitize email for filename (replace characters that might cause issues in file names)
    safe_email = employee_email.replace('@', '_at_').replace('.', '_dot_')
    filename = f"{safe_email}_{today_str}_audit.log"
    return os.path.join(audit_log_dir, filename)

def log_employee_action(employee_email, action_description):
    """
    Logs an action to a specific employee's daily audit log file.
    This function dynamically attaches and detaches a file handler to ensure
    each log entry goes to the correct, employee-specific file.
    """
    if not employee_email:
        # Handle cases where employee_email might be empty or None
        logging.error("log_employee_action called with empty employee_email.")
        return

    log_filepath = get_employee_audit_filepath(employee_email)

    # Remove existing handlers from this logger to ensure only the new one is active
    for handler in list(employee_audit_logger.handlers):
        employee_audit_logger.removeHandler(handler)

    # Create a file handler for the specific employee's log file
    file_handler = logging.FileHandler(log_filepath, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    file_handler.setFormatter(formatter)
    employee_audit_logger.addHandler(file_handler)

    # Log the action
    employee_audit_logger.info(action_description)

    # Remove the handler after logging to prevent it from accumulating or
    # writing subsequent logs to the wrong file if email changes
    employee_audit_logger.removeHandler(file_handler)
    file_handler.close() # Ensure the file handle is released