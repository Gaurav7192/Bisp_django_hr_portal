# staff/utils/audit.py
import logging
from datetime import datetime
import os


# Setting up the logging configuration
def get_logger(user):
    log_filename = f"{user.username}_log.log"
    log_path = os.path.join("logs", log_filename)

    if not os.path.exists("logs"):
        os.makedirs("logs")

    # Create a logger
    logger = logging.getLogger(user.username)
    handler = logging.FileHandler(log_path)
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger


# Log user action function
def log_user_action(user, action):
    logger = get_logger(user)  # Get user-specific logger
    logger.info(f"{action}")
