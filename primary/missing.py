#!/usr/bin/env python3
"""
Missing Episode Processing
Handles searching for missing episodes in Sonarr
"""

import random
import time
import datetime
from typing import List, Callable
from primary.utils.logger import logger, debug_log
from primary.config import (
    HUNT_MISSING_SHOWS, 
    MONITORED_ONLY, 
    RANDOM_MISSING,
    SKIP_FUTURE_EPISODES,
    SKIP_SERIES_REFRESH
)
from primary import settings_manager
from primary.api import (
    get_episodes_for_series, 
    refresh_series, 
    episode_search_episodes, 
    get_series_with_missing_episodes
)
from primary.state import load_processed_ids, save_processed_id, truncate_processed_list, PROCESSED_MISSING_FILE

# Ensure RANDOM_MISSING is dynamically reloaded at the start of each cycle
# Updated logic to reload settings before processing missing episodes

def process_missing_episodes(restart_cycle_flag: Callable[[], bool] = lambda: False) -> bool:
    """
    Process episodes that are missing from the library.

    Args:
        restart_cycle_flag: Function that returns whether to restart the cycle

    Returns:
        True if any processing was done, False otherwise
    """
    # Reload settings to ensure the latest values are used
    from primary.config import refresh_settings
    refresh_settings()

    # Get the current value directly at the start of processing
    HUNT_MISSING_SHOWS = settings_manager.get_setting("huntarr", "hunt_missing_shows", 1)
    RANDOM_MISSING = settings_manager.get_setting("advanced", "random_missing", True)

    logger.info("=== Checking for Missing Episodes ===")

    # Skip if HUNT_MISSING_SHOWS is set to 0
    if HUNT_MISSING_SHOWS <= 0:
        logger.info("HUNT_MISSING_SHOWS is set to 0, skipping missing episodes")
        return False

    # Check for restart signal
    if restart_cycle_flag():
        logger.info("🔄 Received restart signal before starting missing episodes. Aborting...")
        return False

    total_pages = get_missing_total_pages()

    # If we got an error (-1) from the API request, return early
    if total_pages < 0:
        logger.error("Failed to get missing data due to API error. Skipping this cycle.")
        return False

    if total_pages == 0:
        logger.info("No missing episodes found.")
        return False

    # Check for restart signal
    if restart_cycle_flag():
        logger.info("🔄 Received restart signal after getting total pages. Aborting...")
        return False

    logger.info(f"Found {total_pages} total pages of missing episodes.")
    processed_missing_ids = load_processed_ids(PROCESSED_MISSING_FILE)
    episodes_processed = 0
    processing_done = False

    # Use RANDOM_MISSING setting
    should_use_random = RANDOM_MISSING

    logger.info(f"Using {'random' if should_use_random else 'sequential'} selection for missing episodes (RANDOM_MISSING={should_use_random})")

    # Initialize page variable for both modes
    page = 1

    while True:
        # Check for restart signal at the beginning of each page processing
        if restart_cycle_flag():
            logger.info("🔄 Received restart signal at start of page loop. Aborting...")
            break

        # Check again to make sure we're using the current limit
        # This ensures if settings changed during processing, we use the new value
        current_limit = settings_manager.get_setting("huntarr", "hunt_missing_shows", 1)

        if episodes_processed >= current_limit:
            logger.info(f"Reached HUNT_MISSING_SHOWS={current_limit} for this cycle.")
            break

        # If random selection is enabled, pick a random page each iteration
        if should_use_random and total_pages > 1:
            page = random.randint(1, total_pages)
        # If sequential and we've reached the end, we're done
        elif not should_use_random and page > total_pages:
            break

        logger.info(f"Retrieving missing episodes (page={page} of {total_pages})...")
        missing_data = get_missing(page)

        # Check for restart signal after retrieving page
        if restart_cycle_flag():
            logger.info(f"🔄 Received restart signal after retrieving page {page}. Aborting...")
            break

        if not missing_data or "records" not in missing_data:
            logger.error(f"ERROR: Unable to retrieve missing data from Sonarr on page {page}.")

            # In sequential mode, try the next page
            if not should_use_random:
                page += 1
                continue
            else:
                break

        episodes = missing_data["records"]
        total_eps = len(episodes)
        logger.info(f"Found {total_eps} episodes on page {page} that are missing.")

        # Randomize or sequential indices within the page
        indices = list(range(total_eps))
        if should_use_random:
            random.shuffle(indices)

        # Check for restart signal before processing episodes
        if restart_cycle_flag():
            logger.info(f"🔄 Received restart signal before processing episodes on page {page}. Aborting...")
            break

        for idx in indices:
            # Check for restart signal before each episode
            if restart_cycle_flag():
                logger.info(f"🔄 Received restart signal during episode processing. Aborting...")
                break

            # Check again for the current limit in case it was changed during processing
            current_limit = settings_manager.get_setting("huntarr", "hunt_missing_shows", 1)

            if episodes_processed >= current_limit:
                break

            ep_obj = episodes[idx]
            episode_id = ep_obj.get("id")
            if not episode_id or episode_id in processed_missing_ids:
                continue

            series_id = ep_obj.get("seriesId")
            season_num = ep_obj.get("seasonNumber")
            ep_num = ep_obj.get("episodeNumber")
            ep_title = ep_obj.get("title", "Unknown Episode Title")

            series_title = ep_obj.get("seriesTitle", None)
            if not series_title:
                # fallback: request the series
                series_data = arr_request(f"series/{series_id}", method="GET")
                if series_data:
                    series_title = series_data.get("title", "Unknown Series")
                else:
                    series_title = "Unknown Series"

            logger.info(f"Processing missing episode for \"{series_title}\" - S{season_num}E{ep_num} - \"{ep_title}\" (Episode ID: {episode_id})")

            # Search for the episode (missing)
            logger.info(" - Searching for missing episode...")
            search_res = episode_search_episodes([episode_id])
            if search_res:
                logger.info(f"Search command completed successfully.")
                # Mark processed
                save_processed_id(PROCESSED_MISSING_FILE, episode_id)
                episodes_processed += 1
                processing_done = True

                # Log with the current limit, not the initial one
                current_limit = settings_manager.get_setting("huntarr", "hunt_missing_shows", 1)
                logger.info(f"Processed {episodes_processed}/{current_limit} missing episodes this cycle.")
            else:
                logger.warning(f"WARNING: Search command failed for episode ID {episode_id}.")
                continue

            # Check for restart signal after processing an episode
            if restart_cycle_flag():
                logger.info(f"🔄 Received restart signal after processing episode {ep_title}. Aborting...")
                break

        # Move to the next page if using sequential mode
        if not should_use_random:
            page += 1
        # In random mode, we just handle one random page this iteration,
        # then check if we've processed enough episodes or continue to another random page

        # Check for restart signal after processing a page
        if restart_cycle_flag():
            logger.info(f"🔄 Received restart signal after processing page {page}. Aborting...")
            break

    # Log with the current limit, not the initial one
    current_limit = settings_manager.get_setting("huntarr", "hunt_missing_shows", 1)
    logger.info(f"Completed processing {episodes_processed} missing episodes for this cycle.")
    truncate_processed_list(PROCESSED_MISSING_FILE)

    return processing_done