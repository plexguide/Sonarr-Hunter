#!/usr/bin/env python3
"""
Logging configuration for Huntarr
"""

import logging
import sys
import os
import pathlib

# Create log directory
LOG_DIR = pathlib.Path("/tmp/huntarr-logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "huntarr.log"

# Global logger instance
logger = None

def setup_logger(debug_mode=None):
    """Configure and return the application logger
    
    Args:
        debug_mode (bool, optional): Override the DEBUG_MODE from config. Defaults to None.
    
    Returns:
        logging.Logger: The configured logger
    """
    global logger
    
    # Get DEBUG_MODE from config, but only if we haven't been given a value
    # Use a safe approach to avoid circular imports
    use_debug_mode = False
    if debug_mode is None:
        try:
            # Try to get DEBUG_MODE from config, but don't fail if it's not available
            from primary.config import DEBUG_MODE as CONFIG_DEBUG_MODE
            use_debug_mode = CONFIG_DEBUG_MODE
        except (ImportError, AttributeError):
            # Default to False if there's any issue
            pass
    else:
        use_debug_mode = debug_mode
    
    if logger is None:
        # First-time setup
        logger = logging.getLogger("huntarr")
    else:
        # Reset handlers to avoid duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
    
    # Set the log level based on use_debug_mode
    logger.setLevel(logging.DEBUG if use_debug_mode else logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if use_debug_mode else logging.INFO)
    
    # Create file handler for the web interface
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.DEBUG if use_debug_mode else logging.INFO)
    
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
    
    if use_debug_mode:
        logger.debug("Debug logging enabled")
    
    return logger

# Create the logger instance on module import
logger = setup_logger()

def debug_log(message: str, data: object = None) -> None:
    """Log debug messages with optional data."""
    if logger.level <= logging.DEBUG:
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