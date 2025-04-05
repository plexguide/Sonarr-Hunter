#!/usr/bin/env python3
"""
Huntarr [Sonarr Edition] - Python Version
Automatically search for missing episodes (per-episode) and quality upgrades in Sonarr,
while respecting unmonitored seasons/episodes.
"""
import time
from huntarrLib.logger import logger
from huntarrLib.config import settings
import huntarrLib.qualityUpgrade as qualityUpgrade


def check_state_reset() -> None:
    """Check if state files need to be reset based on their age."""
    if int(settings.STATE_RESET_INTERVAL_HOURS) <= 0:
        logger.info("State reset is disabled. Processed items will be remembered indefinitely.")
        return

    now = time.time()

    missing_age = now - settings.PROCESSED_MISSING_FILE.stat().st_mtime
    upgrade_age = now - settings.PROCESSED_UPGRADE_FILE.stat().st_mtime

    reset_interval_seconds = int(settings.STATE_RESET_INTERVAL_HOURS) * 3600

    if missing_age >= reset_interval_seconds or upgrade_age >= reset_interval_seconds:
        logger.info(f"Resetting processed state files (older than {settings.STATE_RESET_INTERVAL_HOURS} hours).")
        settings.PROCESSED_MISSING_FILE.write_text("")
        settings.PROCESSED_UPGRADE_FILE.write_text("")


# ---------------------------
# Main Loop
# ---------------------------
def calculate_reset_time() -> None:
    """Calculate and display time until the next state reset."""
    if int(settings.STATE_RESET_INTERVAL_HOURS) <= 0:
        logger.info("State reset is disabled. Processed items will be remembered indefinitely.")
        return

    current_time = time.time()
    missing_age = current_time - settings.PROCESSED_MISSING_FILE.stat().st_mtime
    upgrade_age = current_time - settings.PROCESSED_UPGRADE_FILE.stat().st_mtime

    reset_interval_seconds = int(settings.STATE_RESET_INTERVAL_HOURS) * 3600
    missing_remaining = reset_interval_seconds - missing_age
    upgrade_remaining = reset_interval_seconds - upgrade_age

    remaining_seconds = min(missing_remaining, upgrade_remaining)
    remaining_minutes = int(remaining_seconds / 60)

    logger.info(f"State reset will occur in approximately {remaining_minutes} minutes.")


def main_loop() -> None:
    """Main processing loop."""
    while True:
        # Check if state files need to be reset
        check_state_reset()

        # Process shows/episodes based on SEARCH_TYPE
        if settings.SEARCH_TYPE == "missing":
            qualityUpgrade.process_missing_episodes()
        elif settings.SEARCH_TYPE == "upgrade":
            qualityUpgrade.process_cutoff_upgrades()
        elif settings.SEARCH_TYPE == "both":
            qualityUpgrade.process_missing_episodes()
            qualityUpgrade.process_cutoff_upgrades()
        else:
            logger.error(f"Unknown SEARCH_TYPE={settings.SEARCH_TYPE}. Use 'missing','upgrade','both'.")

        # Calculate time until the next reset
        calculate_reset_time()

        logger.info(f"Cycle complete. Waiting {settings.SLEEP_DURATION} seconds before next cycle...")
        logger.info("⭐ Enjoy the Tool? Donate @ https://donate.plex.one towards my Daughter's 501 College Fund!")
        time.sleep(settings.SLEEP_DURATION)


if __name__ == "__main__":
    logger.info("=== Huntarr [Sonarr Edition] Starting ===")
    logger.info(f"API URL: {settings.API_URL}")
    logger.debug(f"API KEY: {settings.API_KEY}")
    logger.info(f"Configuration: MAX_MISSING={settings.MAX_MISSING}, MAX_UPGRADES={settings.MAX_UPGRADES}, SLEEP_DURATION={settings.SLEEP_DURATION}s")
    logger.info(f"Configuration: MONITORED_ONLY={settings.MONITORED_ONLY}, RANDOM_SELECTION={settings.RANDOM_SELECTION}, SEARCH_TYPE={settings.SEARCH_TYPE}")

    try:
        main_loop()
    except KeyboardInterrupt:
        logger.info("Huntarr stopped by user.")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise
