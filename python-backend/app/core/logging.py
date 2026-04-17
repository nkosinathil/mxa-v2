"""
Logging Configuration

Sets up structured logging for the application.
"""

import logging
import sys
from pathlib import Path
from pythonjsonlogger import jsonlogger

from app.core.config import settings


def setup_logging():
    """Configure application logging"""
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    
    # Create formatters
    json_formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s'
    )
    
    console_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler (if configured)
    if settings.log_file:
        log_path = Path(settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(settings.log_file)
        file_handler.setFormatter(json_formatter)
        logger.addHandler(file_handler)
    
    return logger


# Initialize logging
logger = setup_logging()
