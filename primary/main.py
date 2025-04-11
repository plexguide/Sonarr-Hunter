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
from primary.utils.logger import logger
from primary.config import HUNT_MODE, SLEEP_DURATION, MINIMUM_DOWNLOAD_QUEUE_SIZE, APP_TYPE, log_configuration, refresh_settings
from primary.state import check_state_reset, calculate_reset_time
from primary.api import get_download_queue_size

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

def get_ip_address():
    """Get the host's IP address from API_URL for display"""
    try:
        from urllib.parse import urlparse
        from primary.config import API_URL
        
        # Extract the hostname/IP from the API_URL
        parsed_url = urlparse(API_URL)
        hostname = parsed_url.netloc
        
        # Remove port if present
        if ':' in hostname:
            hostname = hostname.split(':')[0]
            
        return hostname
    except Exception as e:
        # Fallback to the current method if there's an issue
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            return ip
        except:
            return "YOUR_SERVER_IP"

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
    
    # Log welcome message
    logger.info(f"=== Huntarr [{APP_TYPE.title()} Edition] Starting ===")
    
    # Log web UI information (always enabled)
    server_ip = get_ip_address()
    logger.info(f"Web interface available at http://{server_ip}:9705")
    
    logger.info("GitHub: https://github.com/plexguide/huntarr")
    
    while True:
        # Set restart_cycle flag to False at the beginning of each cycle
        restart_cycle = False
        
        # Always force reload all modules at the start of each cycle
        force_reload_all_modules()
        
        # Check if state files need to be reset
        check_state_reset()
        
        logger.info(f"=== Starting Huntarr cycle ===")
        
        # Check API connectivity before proceeding
        from primary.api import check_connection
        api_connected = False
        
        while not api_connected and not restart_cycle:
            api_connected = check_connection()
            if not api_connected:
                logger.error(f"Cannot connect to {APP_TYPE.title()}. Please check your API URL and API key.")
                logger.info(f"Will retry in 10 seconds...")
                
                # Sleep for 10 seconds before retrying
                for _ in range(10):
                    time.sleep(1)
                    if restart_cycle:
                        break
                        
                # If settings were changed and restart was triggered, break out
                if restart_cycle:
                    logger.warning("⚠️ Restarting cycle due to settings change... ⚠️")
                    continue
        
        # Skip processing if we still can't connect after retries
        if not api_connected:
            logger.error("Connection failed, skipping this cycle.")
            time.sleep(10)
            continue
        
        # Track if any processing was done in this cycle
        processing_done = False

        # Check if we should ignore the download queue size or if we are below the minimum queue size
        download_queue_size = get_download_queue_size()
        if MINIMUM_DOWNLOAD_QUEUE_SIZE < 0 or (MINIMUM_DOWNLOAD_QUEUE_SIZE >= 0 and download_queue_size <= MINIMUM_DOWNLOAD_QUEUE_SIZE):
            # Process items based on APP_TYPE and HUNT_MODE
            if restart_cycle:
                logger.warning("⚠️ Restarting cycle due to settings change... ⚠️")
                continue
                
            if APP_TYPE == "sonarr":
                # Get updated settings to ensure we're using the current values
                from primary.config import HUNT_MISSING_SHOWS, HUNT_UPGRADE_EPISODES
                
                # First process missing shows if configured
                if HUNT_MISSING_SHOWS > 0:
                    logger.info(f"Configured to look for {HUNT_MISSING_SHOWS} missing shows")
                    from primary.missing import process_missing_episodes
                    if process_missing_episodes():
                        processing_done = True
                    else:
                        logger.info("No missing episodes processed - check if you have any missing episodes in Sonarr")
                    
                    # Check if restart signal received
                    if restart_cycle:
                        logger.warning("⚠️ Restarting cycle due to settings change... ⚠️")
                        continue
                else:
                    logger.info("Missing shows search disabled (HUNT_MISSING_SHOWS=0)")
                        
                # Then process quality upgrades if configured
                if HUNT_UPGRADE_EPISODES > 0:
                    logger.info(f"Configured to look for {HUNT_UPGRADE_EPISODES} quality upgrades")
                    from primary.upgrade import process_cutoff_upgrades
                    if process_cutoff_upgrades():
                        processing_done = True
                    else:
                        logger.info("No quality upgrades processed - check if you have any cutoff unmet episodes in Sonarr")
                    
                    # Check if restart signal received
                    if restart_cycle:
                        logger.warning("⚠️ Restarting cycle due to settings change... ⚠️")
                        continue
                else:
                    logger.info("Quality upgrades search disabled (HUNT_UPGRADE_EPISODES=0)")
            
            elif APP_TYPE == "radarr":
                # TODO: Implement Radarr processing
                logger.info("Radarr processing not yet implemented")
                time.sleep(5)  # Short sleep to avoid log spam
                
            elif APP_TYPE == "lidarr":
                # TODO: Implement Lidarr processing
                logger.info("Lidarr processing not yet implemented")
                time.sleep(5)  # Short sleep to avoid log spam
                
            elif APP_TYPE == "readarr":
                # TODO: Implement Readarr processing
                logger.info("Readarr processing not yet implemented")
                time.sleep(5)  # Short sleep to avoid log spam

        else:
            logger.info(f"Download queue size ({download_queue_size}) is above the minimum threshold ({MINIMUM_DOWNLOAD_QUEUE_SIZE}). Skipped processing.")

        # Calculate time until the next reset
        calculate_reset_time()
        
        # Refresh settings before sleep to get the latest sleep_duration
        refresh_settings()
        # Import it directly from the settings manager to ensure latest value
        from primary.config import SLEEP_DURATION as CURRENT_SLEEP_DURATION
        
        # Sleep at the end of the cycle only
        logger.info(f"Cycle complete. Sleeping {CURRENT_SLEEP_DURATION}s before next cycle...")
        
        # Log web UI information
        server_ip = get_ip_address()
        logger.info(f"Web interface available at http://{server_ip}:9705")
        
        # Sleep with progress updates for the web interface
        sleep_start = time.time()
        sleep_end = sleep_start + CURRENT_SLEEP_DURATION
        
        while time.time() < sleep_end and not restart_cycle:
            # Sleep in smaller chunks for more responsive shutdown and restart
            time.sleep(min(1, sleep_end - time.time()))
            
            # Every minute, log the remaining sleep time for web interface visibility
            if int((time.time() - sleep_start) % 60) == 0 and time.time() < sleep_end - 10:
                remaining = int(sleep_end - time.time())
                logger.debug(f"Sleeping... {remaining}s remaining until next cycle")
            
            # Check if restart signal received
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