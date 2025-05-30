# newproject/staff/audit_logger.py

import logging
import os
from django.conf import settings
from logging.handlers import RotatingFileHandler
from datetime import datetime

# --- Configuration ---
AUDIT_LOG_DIR = getattr(settings, 'AUDIT_LOG_DIR', os.path.join(settings.BASE_DIR, 'audit_logs'))

# Ensure the audit log directory exists
os.makedirs(AUDIT_LOG_DIR, exist_ok=True)

# --- Logger Cache ---
# To store individual loggers for each user
_audit_loggers = {}

# --- Logging Function ---
def get_user_audit_logger(user_identifier):
    """
    Returns a logger for the given user identifier that logs to a date-specific file.
    Reinitializes the logger if the date has changed to create a new file per day.
    """
    current_date = datetime.now().strftime('%Y-%m-%d')
    logger_key = f"{user_identifier}_{current_date}"

    if logger_key not in _audit_loggers:
        logger_name = f"audit_log_user_{logger_key}"
        user_logger = logging.getLogger(logger_name)
        user_logger.setLevel(logging.INFO)
        user_logger.propagate = False

        log_file_path = os.path.join(AUDIT_LOG_DIR, f"{user_identifier}_{current_date}.txt")

        try:
            handler = RotatingFileHandler(
                log_file_path,
                maxBytes=1 * 1024 * 1024,
                backupCount=5,
                encoding='utf-8'
            )
            formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H.%M.%S')
            handler.setFormatter(formatter)
            user_logger.addHandler(handler)
            print(f"DEBUG: Audit logger initialized for {user_identifier}. Logging to: {log_file_path}")
        except Exception as e:
            print(f"ERROR: Could not set up audit logger handler for {user_identifier}: {e}")
            user_logger.addHandler(logging.StreamHandler())
            user_logger.propagate = True

        _audit_loggers[logger_key] = user_logger

    return _audit_loggers[logger_key]


def log_audit_action(user_identifier, action_description):
    """
    Logs an audit action to the specific audit log file for the given user.
    """
    user_logger = get_user_audit_logger(user_identifier)
    try:
        user_logger.info(f"{action_description}") # User identifier is part of the filename, so not needed in message
        print(f"DEBUG: Attempted to log for '{user_identifier}': '{action_description}'")
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to write audit log entry for {user_identifier} - {action_description}. Error: {e}")