#!/usr/bin/env python3
"""
Missing Episode Processing
Handles searching for missing episodes in Sonarr
"""

import random
import time
from typing import List
from utils.logger import logger
from config import HUNT_MISSING_SHOWS, MONITORED_ONLY, RANDOM_SELECTION
from api import (
    get_episodes_for_series, 
    refresh_series, 
    episode_search_episodes, 
    get_series_with_missing_episodes
)
from state import load_processed_ids, save_processed_id, truncate_processed_list, PROCESSED_MISSING_FILE

def process_missing_episodes() -> bool:
    """
    Process shows that have missing episodes, but respect
    unmonitored seasons/episodes. We'll fetch episodes for each show
    and only search for episodes that are BOTH missing and monitored.
    
    Returns:
        True if any processing was done, False otherwise
    """
    logger.info("=== Checking for Missing Episodes ===")

    # Skip if HUNT_MISSING_SHOWS is set to 0
    if HUNT_MISSING_SHOWS <= 0:
        logger.info("HUNT_MISSING_SHOWS is set to 0, skipping missing content")
        return False

    # Get shows that have missing episodes directly - more efficient than checking all shows
    shows_with_missing = get_series_with_missing_episodes()
    if not shows_with_missing:
        logger.info("No shows with missing episodes found.")
        return False
    
    logger.info(f"Found {len(shows_with_missing)} shows with missing episodes.")

    # Optionally filter to only monitored shows (if MONITORED_ONLY==true)
    if MONITORED_ONLY:
        logger.info("MONITORED_ONLY=true => only fully monitored shows.")
        shows_with_missing = [s for s in shows_with_missing if s.get("monitored") is True]
    else:
        logger.info("MONITORED_ONLY=false => all shows, even if unmonitored.")

    if not shows_with_missing:
        logger.info("No monitored shows with missing episodes found.")
        return False

    processed_missing_ids = load_processed_ids(PROCESSED_MISSING_FILE)
    shows_processed = 0
    processing_done = False

    # Optionally randomize show order
    if RANDOM_SELECTION:
        random.shuffle(shows_with_missing)

    for show in shows_with_missing:
        if shows_processed >= HUNT_MISSING_SHOWS:
            break

        series_id = show.get("id")
        if not series_id:
            continue

        # If we already processed this show ID, skip
        if series_id in processed_missing_ids:
            continue

        show_title = show.get("title", "Unknown Show")
        missing_count = show.get("missingEpisodeCount", 0)
        missing_episodes = show.get("missingEpisodes", [])
        
        logger.info(f"Processing '{show_title}' with {missing_count} missing episodes.")

        # Filter missing episodes to find those that are monitored
        monitored_missing_episodes = [
            ep for ep in missing_episodes
            if ep.get("monitored") is True
        ]

        if not monitored_missing_episodes:
            logger.info(f"No missing monitored episodes found for '{show_title}' — skipping.")
            continue

        logger.info(f"Found {len(monitored_missing_episodes)} missing monitored episode(s) for '{show_title}'.")

        # Refresh the series
        logger.info(f" - Refreshing series (ID: {series_id})...")
        refresh_res = refresh_series(series_id)
        if not refresh_res:
            logger.warning(f"WARNING: Refresh command failed for {show_title}. Skipping.")
            continue

        logger.info(f"Refresh command completed successfully.")

        # Search specifically for these missing + monitored episodes
        episode_ids = [ep["id"] for ep in monitored_missing_episodes]
        logger.info(f" - Searching for {len(episode_ids)} missing episodes in '{show_title}'...")
        search_res = episode_search_episodes(episode_ids)
        if search_res:
            logger.info(f"Search command completed successfully.")
            processing_done = True
        else:
            logger.warning(f"WARNING: EpisodeSearch failed for show '{show_title}' (ID: {series_id}).")
            continue

        # Mark as processed
        save_processed_id(PROCESSED_MISSING_FILE, series_id)
        shows_processed += 1
        logger.info(f"Processed {shows_processed}/{HUNT_MISSING_SHOWS} missing shows this cycle.")

    # Truncate processed list if needed
    truncate_processed_list(PROCESSED_MISSING_FILE)
    
    return processing_done