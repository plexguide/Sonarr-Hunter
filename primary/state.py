#!/usr/bin/env python3
"""
State management for Huntarr
Handles tracking which items have been processed
"""

import os
import time
import pathlib
from typing import List
from primary.utils.logger import logger
from primary.config import STATE_RESET_INTERVAL_HOURS, APP_TYPE

# State directory setup
STATE_DIR = pathlib.Path("/config/stateful")
STATE_DIR.mkdir(parents=True, exist_ok=True)

# Create app-specific state file paths
if APP_TYPE == "sonarr":
    PROCESSED_MISSING_FILE = STATE_DIR / "processed_missing_sonarr.txt"
    PROCESSED_UPGRADE_FILE = STATE_DIR / "processed_upgrade_sonarr.txt"
elif APP_TYPE == "radarr":
    PROCESSED_MISSING_FILE = STATE_DIR / "processed_missing_radarr.txt"
    PROCESSED_UPGRADE_FILE = STATE_DIR / "processed_upgrade_radarr.txt"
elif APP_TYPE == "lidarr":
    PROCESSED_MISSING_FILE = STATE_DIR / "processed_missing_lidarr.txt"
    PROCESSED_UPGRADE_FILE = STATE_DIR / "processed_upgrade_lidarr.txt"
elif APP_TYPE == "readarr":
    PROCESSED_MISSING_FILE = STATE_DIR / "processed_missing_readarr.txt"
    PROCESSED_UPGRADE_FILE = STATE_DIR / "processed_upgrade_readarr.txt"
else:
    # Default fallback to sonarr
    PROCESSED_MISSING_FILE = STATE_DIR / "processed_missing_sonarr.txt"
    PROCESSED_UPGRADE_FILE = STATE_DIR / "processed_upgrade_sonarr.txt"

# Create files if they don't exist
PROCESSED_MISSING_FILE.touch(exist_ok=True)
PROCESSED_UPGRADE_FILE.touch(exist_ok=True)

def load_processed_ids(file_path: pathlib.Path) -> List[int]:
    """Load processed item IDs from a file."""
    try:
        with open(file_path, 'r') as f:
            return [int(line.strip()) for line in f if line.strip().isdigit()]
    except Exception as e:
        logger.error(f"Error reading processed IDs from {file_path}: {e}")
        return []

def save_processed_id(file_path: pathlib.Path, obj_id: int) -> None:
    """Save a processed item ID to a file."""
    try:
        with open(file_path, 'a') as f:
            f.write(f"{obj_id}\n")
    except Exception as e:
        logger.error(f"Error writing to {file_path}: {e}")

def truncate_processed_list(file_path: pathlib.Path, max_lines: int = 500) -> None:
    """Truncate the processed list to prevent unbounded growth."""
    try:
        # Only check if file is somewhat large
        if file_path.stat().st_size > 10000:
            lines = file_path.read_text().splitlines()
            if len(lines) > max_lines:
                logger.info(f"Processed list is large. Truncating to last {max_lines} entries.")
                with open(file_path, 'w') as f:
                    f.write('\n'.join(lines[-max_lines:]) + '\n')
    except Exception as e:
        logger.error(f"Error truncating {file_path}: {e}")

def check_state_reset() -> None:
    """Check if state files need to be reset based on their age."""
    if STATE_RESET_INTERVAL_HOURS <= 0:
        logger.info("State reset is disabled. Processed items will be remembered indefinitely.")
        return
    
    missing_age = time.time() - PROCESSED_MISSING_FILE.stat().st_mtime
    upgrade_age = time.time() - PROCESSED_UPGRADE_FILE.stat().st_mtime
    reset_interval_seconds = STATE_RESET_INTERVAL_HOURS * 3600
    
    if missing_age >= reset_interval_seconds or upgrade_age >= reset_interval_seconds:
        logger.info(f"Resetting processed state files (older than {STATE_RESET_INTERVAL_HOURS} hours).")
        PROCESSED_MISSING_FILE.write_text("")
        PROCESSED_UPGRADE_FILE.write_text("")

def calculate_reset_time() -> None:
    """Calculate and display time until the next state reset."""
    if STATE_RESET_INTERVAL_HOURS <= 0:
        logger.info("State reset is disabled. Processed items will be remembered indefinitely.")
        return
    
    current_time = time.time()
    missing_age = current_time - PROCESSED_MISSING_FILE.stat().st_mtime
    upgrade_age = current_time - PROCESSED_UPGRADE_FILE.stat().st_mtime
    
    reset_interval_seconds = STATE_RESET_INTERVAL_HOURS * 3600
    missing_remaining = reset_interval_seconds - missing_age
    upgrade_remaining = reset_interval_seconds - upgrade_age
    
    remaining_seconds = min(missing_remaining, upgrade_remaining)
    remaining_minutes = int(remaining_seconds / 60)
    
    logger.info(f"State reset will occur in approximately {remaining_minutes} minutes.")