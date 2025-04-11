#!/usr/bin/env python3
"""
Huntarr - Main entry point for the application
Supports multiple Arr applications
"""

import time
import sys
import os
import socket
import signal
import importlib
import logging

# Set up logging first to avoid circular imports
from primary.utils.logger import setup_logger
logger = setup_logger()

# Now import the rest of the modules
from primary.config import HUNT_MODE, SLEEP_DURATION, MINIMUM_DOWNLOAD_QUEUE_SIZE, APP_TYPE, log_configuration, refresh_settings
from primary.state import check_state_reset, calculate_reset_time
from primary.api import get_download_queue_size
from primary.utils.app_utils import get_ip_address  # Use centralized function

# Flag to indicate if cycle should restart
restart_cycle = False

def signal_handler(signum, frame):
    """Handle signals from the web UI for cycle restart"""
    global restart_cycle
    if signum == signal.SIGUSR1:
        logger.warning("⚠️ Received restart signal from web UI. Immediately aborting current operations... ⚠️")
        restart_cycle = True

# Register signal handler for SIGUSR1
signal.signal(signal.SIGUSR1, signal_handler)

# Removed duplicate get_ip_address(); now using get_ip_address() from app_utils

def force_reload_all_modules():
    """Force reload of all relevant modules to ensure fresh settings"""
    try:
        # Force reload the settings_manager first
        from primary import settings_manager
        importlib.reload(settings_manager)
        
        # Then reload config which depends on settings_manager
        from primary import config
        importlib.reload(config)
        
        # Reload app-specific modules
        if APP_TYPE == "sonarr":
            from primary import missing
            importlib.reload(missing)
            
            from primary import upgrade
            importlib.reload(upgrade)
        # TODO: Add other app type module reloading when implemented
        
        # Call the refresh function to ensure settings are updated
        config.refresh_settings()
        
        # Log the reloaded settings for verification
        logger.info("Settings reloaded from huntarr.json file")
        config.log_configuration(logger)
        
        return True
    except Exception as e:
        logger.error(f"Error reloading modules: {e}")
        return False

def main_loop() -> None:
    """Main processing loop for Huntarr"""
    global restart_cycle

    logger.info(f"=== Huntarr [{APP_TYPE.title()} Edition] Starting ===")

    server_ip = get_ip_address()
    logger.info(f"Web interface available at http://{server_ip}:9705")

    while True:
        restart_cycle = False

        # Always reload settings from huntarr.json at the start of each cycle
        refresh_settings()

        check_state_reset()

        logger.info(f"=== Starting Huntarr cycle ===")

        from primary.api import check_connection
        api_connected = False

        connection_attempts = 0
        while not api_connected and not restart_cycle:
            refresh_settings()  # Ensure latest settings are loaded

            api_connected = check_connection()
            if not api_connected:
                logger.error(f"Cannot connect to {APP_TYPE.title()}. Please check your API URL and API key.")
                logger.info(f"Will retry in 10 seconds...")

                for _ in range(10):
                    time.sleep(1)
                    if restart_cycle:
                        break

                connection_attempts += 1

                if restart_cycle:
                    logger.warning("⚠️ Restarting cycle due to settings change... ⚠️")
                    continue

        if not api_connected:
            logger.error("Connection failed, skipping this cycle.")
            time.sleep(10)
            continue

        processing_done = False

        download_queue_size = get_download_queue_size()
        if MINIMUM_DOWNLOAD_QUEUE_SIZE < 0 or (MINIMUM_DOWNLOAD_QUEUE_SIZE >= 0 and download_queue_size <= MINIMUM_DOWNLOAD_QUEUE_SIZE):
            if restart_cycle:
                logger.warning("⚠️ Restarting cycle due to settings change... ⚠️")
                continue

            if APP_TYPE == "sonarr":
                from primary.config import HUNT_MISSING_SHOWS, HUNT_UPGRADE_EPISODES

                if HUNT_MISSING_SHOWS > 0:
                    logger.info(f"Configured to look for {HUNT_MISSING_SHOWS} missing shows")
                    from primary.missing import process_missing_episodes
                    if process_missing_episodes():
                        processing_done = True
                    else:
                        logger.info("No missing episodes processed - check if you have any missing episodes in Sonarr")

                    if restart_cycle:
                        logger.warning("⚠️ Restarting cycle due to settings change... ⚠️")
                        continue
                else:
                    logger.info("Missing shows search disabled (HUNT_MISSING_SHOWS=0)")

                if HUNT_UPGRADE_EPISODES > 0:
                    logger.info(f"Configured to look for {HUNT_UPGRADE_EPISODES} quality upgrades")
                    from primary.upgrade import process_cutoff_upgrades
                    if process_cutoff_upgrades():
                        processing_done = True
                    else:
                        logger.info("No quality upgrades processed - check if you have any cutoff unmet episodes in Sonarr")

                    if restart_cycle:
                        logger.warning("⚠️ Restarting cycle due to settings change... ⚠️")
                        continue
                else:
                    logger.info("Quality upgrades search disabled (HUNT_UPGRADE_EPISODES=0)")

        else:
            logger.info(f"Download queue size ({download_queue_size}) is above the minimum threshold ({MINIMUM_DOWNLOAD_QUEUE_SIZE}). Skipped processing.")

        calculate_reset_time()

        refresh_settings()
        from primary.config import SLEEP_DURATION as CURRENT_SLEEP_DURATION

        logger.info(f"Cycle complete. Sleeping {CURRENT_SLEEP_DURATION}s before next cycle...")

        server_ip = get_ip_address()
        logger.info(f"Web interface available at http://{server_ip}:9705")

        sleep_start = time.time()
        sleep_end = sleep_start + CURRENT_SLEEP_DURATION

        while time.time() < sleep_end and not restart_cycle:
            time.sleep(min(1, sleep_end - time.time()))

            if int((time.time() - sleep_start) % 60) == 0 and time.time() < sleep_end - 10:
                remaining = int(sleep_end - time.time())
                logger.debug(f"Sleeping... {remaining}s remaining until next cycle")

            if restart_cycle:
                logger.warning("⚠️ Sleep interrupted due to settings change. Restarting cycle immediately... ⚠️")
                break

if __name__ == "__main__":
    # Log configuration settings
    log_configuration(logger)

    try:
        main_loop()
    except KeyboardInterrupt:
        logger.info("Huntarr stopped by user.")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)