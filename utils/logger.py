#!/usr/bin/env python3
"""
Logging configuration for Huntarr-Sonarr
"""

import logging
import sys
import os
import pathlib
from config import DEBUG_MODE

# Create log directory
LOG_DIR = pathlib.Path("/tmp/huntarr-logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "huntarr.log"

def setup_logger():
    """Configure and return the application logger"""
    logger = logging.getLogger("huntarr-sonarr")
    
    # Set the log level based on DEBUG_MODE
    logger.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)
    
    # Create file handler for the web interface
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)
    
    # Set format
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# Create the logger instance
logger = setup_logger()

def debug_log(message: str, data: object = None) -> None:
    """Log debug messages with optional data."""
    if DEBUG_MODE:
        logger.debug(f"{message}")
        if data is not None:
            try:
                import json
                as_json = json.dumps(data)
                if len(as_json) > 500:
                    as_json = as_json[:500] + "..."
                logger.debug(as_json)
            except:
                data_str = str(data)
                if len(data_str) > 500:
                    data_str = data_str[:500] + "..."
                logger.debug(data_str)