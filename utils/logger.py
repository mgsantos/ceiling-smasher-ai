import logging
import os
import sys
from datetime import datetime

# Create logs directory if it doesn't exist
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, f"app_{datetime.now().strftime('%Y-%m-%d')}.log")

class CustomFormatter(logging.Formatter):
    """
    Custom formatter to match the requested format:
    [INFO/ERROR/WARN] dd-mm-yyyy hh:mm <LOG DATA>
    """
    def format(self, record):
        # Format timestamp: dd-mm-yyyy hh:mm
        timestamp = datetime.fromtimestamp(record.created).strftime('%d-%m-%Y %H:%M')
        
        # Format level
        level = record.levelname
        if level == "WARNING":
            level = "WARN"
            
        # Format message
        msg = record.getMessage()
        
        return f"[{level}] {timestamp} {msg}"

def setup_logger(name="finance_agent", level=logging.INFO):
    """
    Sets up the logger with file and console handlers.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid adding duplicate handlers if setup needed multiple times
    if logger.hasHandlers():
        return logger

    # File Handler
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setFormatter(CustomFormatter())
    logger.addHandler(file_handler)

    # Console Handler (Optional: Keep stdout clean or mirror logs? 
    # User asked for logs folder, but we still need terminal output for the UI stream)
    # We will keep using 'print' or 'rich' for UI/Terminal visible output, 
    # and use this logger primarily for persistence and debugging details.
    # However, to capture everything, we can add a console handler too.
    # But usually 'rich' handles stdout. Let's stick to File Logging for this system 
    # to avoid double-printing in the UI stream which captures stdout.
    
    return logger

# Singleton logger instance
logger = setup_logger()
