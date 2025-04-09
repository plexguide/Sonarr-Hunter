#!/usr/bin/env python3
"""
Configuration module for Huntarr-Sonarr
Handles all environment variables and configuration settings
"""

import os
import logging
import settings_manager

# Web UI Configuration
ENABLE_WEB_UI = os.environ.get("ENABLE_WEB_UI", "true").lower() == "true"

# API Configuration
API_KEY = os.environ.get("API_KEY", "your-api-key")
API_URL = os.environ.get("API_URL", "http://your-sonarr-address:8989")

# API timeout in seconds - load from environment first, will be overridden by settings if they exist
try:
    API_TIMEOUT = int(os.environ.get("API_TIMEOUT", "60"))
except ValueError:
    API_TIMEOUT = 60
    print(f"Warning: Invalid API_TIMEOUT value, using default: {API_TIMEOUT}")

# Settings that can be overridden by the settings manager
# Load from environment first, will be overridden by settings if they exist

# Missing Content Settings
try:
    HUNT_MISSING_SHOWS = int(os.environ.get("HUNT_MISSING_SHOWS", "1"))
except ValueError:
    HUNT_MISSING_SHOWS = 1
    print(f"Warning: Invalid HUNT_MISSING_SHOWS value, using default: {HUNT_MISSING_SHOWS}")

# Upgrade Settings
try:
    HUNT_UPGRADE_EPISODES = int(os.environ.get("HUNT_UPGRADE_EPISODES", "5"))
except ValueError:
    HUNT_UPGRADE_EPISODES = 5
    print(f"Warning: Invalid HUNT_UPGRADE_EPISODES value, using default: {HUNT_UPGRADE_EPISODES}")

# Sleep duration in seconds after completing one full cycle (default 15 minutes)
try:
    SLEEP_DURATION = int(os.environ.get("SLEEP_DURATION", "900"))
except ValueError:
    SLEEP_DURATION = 900
    print(f"Warning: Invalid SLEEP_DURATION value, using default: {SLEEP_DURATION}")

# Reset processed state file after this many hours (default 168 hours = 1 week)
try:
    STATE_RESET_INTERVAL_HOURS = int(os.environ.get("STATE_RESET_INTERVAL_HOURS", "168"))
except ValueError:
    STATE_RESET_INTERVAL_HOURS = 168
    print(f"Warning: Invalid STATE_RESET_INTERVAL_HOURS value, using default: {STATE_RESET_INTERVAL_HOURS}")

# Selection Settings
RANDOM_SELECTION = os.environ.get("RANDOM_SELECTION", "true").lower() == "true"
MONITORED_ONLY = os.environ.get("MONITORED_ONLY", "true").lower() == "true"

# New Options
SKIP_FUTURE_EPISODES = os.environ.get("SKIP_FUTURE_EPISODES", "true").lower() == "true"
SKIP_SERIES_REFRESH = os.environ.get("SKIP_SERIES_REFRESH", "false").lower() == "true"

# Advanced settings - load from environment first, will be overridden by settings if they exist
try:
    COMMAND_WAIT_DELAY = int(os.environ.get("COMMAND_WAIT_DELAY", "1"))
except ValueError:
    COMMAND_WAIT_DELAY = 1
    print(f"Warning: Invalid COMMAND_WAIT_DELAY value, using default: {COMMAND_WAIT_DELAY}")

# Number of attempts to wait for a command to complete before giving up (default 600 attempts)
try:
    COMMAND_WAIT_ATTEMPTS = int(os.environ.get("COMMAND_WAIT_ATTEMPTS", "600"))
except ValueError:
    COMMAND_WAIT_ATTEMPTS = 600
    print(f"Warning: Invalid COMMAND_WAIT_ATTEMPTS value, using default: {COMMAND_WAIT_ATTEMPTS}")

# Minimum size of the download queue before starting a hunt (default -1)
try:
    MINIMUM_DOWNLOAD_QUEUE_SIZE = int(os.environ.get("MINIMUM_DOWNLOAD_QUEUE_SIZE", "-1"))
except ValueError:
    MINIMUM_DOWNLOAD_QUEUE_SIZE = -1
    print(f"Warning: Invalid MINIMUM_DOWNLOAD_QUEUE_SIZE value, using default: {MINIMUM_DOWNLOAD_QUEUE_SIZE}")

# Debug Settings
DEBUG_MODE = os.environ.get("DEBUG_MODE", "false").lower() == "true"

# Random selection for missing and upgrades
RANDOM_MISSING = True  # Will be overridden by settings
RANDOM_UPGRADES = True  # Will be overridden by settings

# Hunt mode: "missing", "upgrade", or "both"
HUNT_MODE = os.environ.get("HUNT_MODE", "both")

def refresh_settings():
    """Refresh configuration settings from the settings manager."""
    global HUNT_MISSING_SHOWS, HUNT_UPGRADE_EPISODES, SLEEP_DURATION
    global STATE_RESET_INTERVAL_HOURS, MONITORED_ONLY, RANDOM_SELECTION
    global SKIP_FUTURE_EPISODES, SKIP_SERIES_REFRESH
    global API_TIMEOUT, DEBUG_MODE, COMMAND_WAIT_DELAY, COMMAND_WAIT_ATTEMPTS
    global MINIMUM_DOWNLOAD_QUEUE_SIZE, RANDOM_MISSING, RANDOM_UPGRADES
    
    # Load settings directly from settings manager
    settings = settings_manager.get_all_settings()
    huntarr_settings = settings.get("huntarr", {})
    advanced_settings = settings.get("advanced", {})
    
    # Update global variables with fresh values
    HUNT_MISSING_SHOWS = huntarr_settings.get("hunt_missing_shows", HUNT_MISSING_SHOWS)
    HUNT_UPGRADE_EPISODES = huntarr_settings.get("hunt_upgrade_episodes", HUNT_UPGRADE_EPISODES)
    SLEEP_DURATION = huntarr_settings.get("sleep_duration", SLEEP_DURATION)
    STATE_RESET_INTERVAL_HOURS = huntarr_settings.get("state_reset_interval_hours", STATE_RESET_INTERVAL_HOURS)
    MONITORED_ONLY = huntarr_settings.get("monitored_only", MONITORED_ONLY)
    RANDOM_SELECTION = huntarr_settings.get("random_selection", RANDOM_SELECTION)
    SKIP_FUTURE_EPISODES = huntarr_settings.get("skip_future_episodes", SKIP_FUTURE_EPISODES)
    SKIP_SERIES_REFRESH = huntarr_settings.get("skip_series_refresh", SKIP_SERIES_REFRESH)
    
    # Advanced settings
    API_TIMEOUT = advanced_settings.get("api_timeout", API_TIMEOUT)
    DEBUG_MODE = advanced_settings.get("debug_mode", DEBUG_MODE)
    COMMAND_WAIT_DELAY = advanced_settings.get("command_wait_delay", COMMAND_WAIT_DELAY)
    COMMAND_WAIT_ATTEMPTS = advanced_settings.get("command_wait_attempts", COMMAND_WAIT_ATTEMPTS)
    MINIMUM_DOWNLOAD_QUEUE_SIZE = advanced_settings.get("minimum_download_queue_size", MINIMUM_DOWNLOAD_QUEUE_SIZE)
    RANDOM_MISSING = advanced_settings.get("random_missing", RANDOM_MISSING)
    RANDOM_UPGRADES = advanced_settings.get("random_upgrades", RANDOM_UPGRADES)
    
    # Log the refresh for debugging
    import logging
    logger = logging.getLogger("huntarr-sonarr")
    logger.debug(f"Settings refreshed: SLEEP_DURATION={SLEEP_DURATION}, HUNT_MISSING_SHOWS={HUNT_MISSING_SHOWS}")
    logger.debug(f"Advanced settings refreshed: API_TIMEOUT={API_TIMEOUT}, DEBUG_MODE={DEBUG_MODE}")

def log_configuration(logger):
    """Log the current configuration settings"""
    # Refresh settings from the settings manager
    refresh_settings()
    
    logger.info("=== Huntarr [Sonarr Edition] Starting ===")
    logger.info(f"API URL: {API_URL}")
    logger.info(f"API Timeout: {API_TIMEOUT}s")
    logger.info(f"Missing Content Configuration: HUNT_MISSING_SHOWS={HUNT_MISSING_SHOWS}")
    logger.info(f"Upgrade Configuration: HUNT_UPGRADE_EPISODES={HUNT_UPGRADE_EPISODES}")
    logger.info(f"State Reset Interval: {STATE_RESET_INTERVAL_HOURS} hours")
    logger.info(f"Minimum Download Queue Size: {MINIMUM_DOWNLOAD_QUEUE_SIZE}")
    logger.info(f"MONITORED_ONLY={MONITORED_ONLY}, RANDOM_SELECTION={RANDOM_SELECTION}")
    logger.info(f"RANDOM_MISSING={RANDOM_MISSING}, RANDOM_UPGRADES={RANDOM_UPGRADES}")
    logger.info(f"HUNT_MODE={HUNT_MODE}, SLEEP_DURATION={SLEEP_DURATION}s")
    logger.info(f"COMMAND_WAIT_DELAY={COMMAND_WAIT_DELAY}, COMMAND_WAIT_ATTEMPTS={COMMAND_WAIT_ATTEMPTS}")
    logger.info(f"SKIP_FUTURE_EPISODES={SKIP_FUTURE_EPISODES}, SKIP_SERIES_REFRESH={SKIP_SERIES_REFRESH}")
    logger.info(f"ENABLE_WEB_UI={ENABLE_WEB_UI}, DEBUG_MODE={DEBUG_MODE}")
    logger.debug(f"API_KEY={API_KEY}")

# Initial refresh of settings
refresh_settings()