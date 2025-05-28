import logging
import os
from django.conf import settings

def get_user_logger(user_id):
    logger_name = f"user_{user_id}"
    log_dir = os.path.join(settings.BASE_DIR, 'logs', 'users')
    os.makedirs(log_dir, exist_ok=True)

    log_file_path = os.path.join(log_dir, f"employee_{user_id}.log")

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.FileHandler(log_file_path, encoding='utf-8')
        formatter = logging.Formatter(
            '{asctime} | Action: {action} | Details: {details}',
            style='{'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False

    return logger