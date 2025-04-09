#!/usr/bin/env python3
"""
Huntarr [Sonarr Edition] - Python Version
Main entry point for the application
"""

import time
import sys
import os
import socket
import signal
import importlib
from utils.logger import logger
from config import HUNT_MODE, SLEEP_DURATION, MINIMUM_DOWNLOAD_QUEUE_SIZE, ENABLE_WEB_UI, log_configuration, refresh_settings
from missing import process_missing_episodes
from state import check_state_reset, calculate_reset_time
from api import get_download_queue_size

# Flag to indicate if cycle should restart
restart_cycle = False

def signal_handler(signum, frame):
    """Handle signals from the web UI for cycle restart"""
    global restart_cycle
    if signum == signal.SIGUSR1:
        logger.info("Received restart signal from web UI. Immediately aborting current operations...")
        restart_cycle = True

# Register signal handler for SIGUSR1
signal.signal(signal.SIGUSR1, signal_handler)

def get_ip_address():
    """Get the host's IP address from API_URL for display"""
    try:
        from urllib.parse import urlparse
        from config import API_URL
        
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
        # Force reload the config module
        import config
        importlib.reload(config)
        
        # Reload any modules that might cache config values
        import missing
        importlib.reload(missing)
        
        import upgrade
        importlib.reload(upgrade)
        
        # Call the refresh function to ensure settings are updated
        config.refresh_settings()
        
        # Log the reloaded settings for verification
        logger.info("Settings reloaded from JSON file after restart signal")
        config.log_configuration(logger)
        
        return True
    except Exception as e:
        logger.error(f"Error reloading modules: {e}")
        return False

def main_loop() -> None:
    """Main processing loop for Huntarr-Sonarr"""
    global restart_cycle
    
    # Log welcome message for web interface
    logger.info("=== Huntarr [Sonarr Edition] Starting ===")
    
    # Log web UI information if enabled
    if ENABLE_WEB_UI:
        server_ip = get_ip_address()
        logger.info(f"Web interface available at http://{server_ip}:8988")
    
    logger.info("GitHub: https://github.com/plexguide/huntarr-sonarr")
    
    while True:
        # Set restart_cycle flag to False at the beginning of each cycle
        restart_cycle = False
        
        # Always force reload all modules at the start of each cycle
        force_reload_all_modules()
        
        # Import after reload to ensure we get fresh values
        from config import HUNT_MODE, HUNT_MISSING_SHOWS, HUNT_UPGRADE_EPISODES
        from upgrade import process_cutoff_upgrades
        
        # Check if state files need to be reset
        check_state_reset()
        
        logger.info(f"=== Starting Huntarr-Sonarr cycle ===")
        
        # Track if any processing was done in this cycle
        processing_done = False

        # Check if we should ignore the download queue size or if we are below the minimum queue size
        download_queue_size = get_download_queue_size()
        if MINIMUM_DOWNLOAD_QUEUE_SIZE < 0 or (MINIMUM_DOWNLOAD_QUEUE_SIZE >= 0 and download_queue_size <= MINIMUM_DOWNLOAD_QUEUE_SIZE):
        
            # Process shows/episodes based on HUNT_MODE
            if restart_cycle:
                logger.info("Restarting cycle due to settings change...")
                continue
                
            if HUNT_MODE in ["missing", "both"] and HUNT_MISSING_SHOWS > 0:
                if process_missing_episodes():
                    processing_done = True
                
                # Check if restart signal received
                if restart_cycle:
                    logger.info("Restarting cycle due to settings change...")
                    continue
                    
            if HUNT_MODE in ["upgrade", "both"] and HUNT_UPGRADE_EPISODES > 0:
                logger.info(f"Starting upgrade process with HUNT_UPGRADE_EPISODES={HUNT_UPGRADE_EPISODES}")
                
                if process_cutoff_upgrades():
                    processing_done = True
                
                # Check if restart signal received
                if restart_cycle:
                    logger.info("Restarting cycle due to settings change...")
                    continue

        else:
            logger.info(f"Download queue size ({download_queue_size}) is above the minimum threshold ({MINIMUM_DOWNLOAD_QUEUE_SIZE}). Skipped processing.")

        # Calculate time until the next reset
        calculate_reset_time()
        
        # Refresh settings before sleep to get the latest sleep_duration
        refresh_settings()
        # Import it directly from the settings manager to ensure latest value
        from config import SLEEP_DURATION as CURRENT_SLEEP_DURATION
        
        # Sleep at the end of the cycle only
        logger.info(f"Cycle complete. Sleeping {CURRENT_SLEEP_DURATION}s before next cycle...")
        logger.info("⭐ Tool Great? Donate @ https://donate.plex.one for Daughter's College Fund!")
        
        # Log web UI information if enabled
        if ENABLE_WEB_UI:
            server_ip = get_ip_address()
            logger.info(f"Web interface available at http://{server_ip}:8988")
        
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
                logger.info("Sleep interrupted due to settings change. Restarting cycle immediately...")
                break

if __name__ == "__main__":
    # Log configuration settings
    log_configuration(logger)

    try:
        main_loop()
    except KeyboardInterrupt:
        logger.info("Huntarr-Sonarr stopped by user.")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)