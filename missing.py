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
from api import get_series, get_episodes_for_series, refresh_series, episode_search_episodes
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

    shows = get_series()
    if not shows:
        logger.error("ERROR: Unable to retrieve series data from Sonarr.")
        return False

    # Optionally filter to only monitored shows (if MONITORED_ONLY==true)
    if MONITORED_ONLY:
        logger.info("MONITORED_ONLY=true => only fully monitored shows.")
        shows = [s for s in shows if s.get("monitored") is True]
    else:
        logger.info("MONITORED_ONLY=false => all shows, even if unmonitored.")

    if not shows:
        logger.info("No shows to process.")
        return False

    processed_missing_ids = load_processed_ids(PROCESSED_MISSING_FILE)
    shows_processed = 0
    processing_done = False

    indices = list(range(len(shows)))
    if RANDOM_SELECTION:
        random.shuffle(indices)

    for idx in indices:
        if shows_processed >= HUNT_MISSING_SHOWS:
            break

        show = shows[idx]
        series_id = show.get("id")
        if not series_id:
            continue

        # If we already processed this show ID, skip
        if series_id in processed_missing_ids:
            continue

        show_title = show.get("title", "Unknown Show")

        # Fetch the episodes for this show
        episode_list = get_episodes_for_series(series_id)
        if not episode_list:
            logger.warning(f"WARNING: Could not retrieve episodes for series ID={series_id}. Skipping.")
            continue

        # Find all episodes that are monitored and missing a file
        missing_monitored_eps = [
            e for e in episode_list
            if e.get("monitored") is True
            and e.get("hasFile") is False
        ]

        if not missing_monitored_eps:
            # This show has no missing monitored episodes, skip
            logger.info(f"No missing monitored episodes for '{show_title}' — skipping.")
            continue

        logger.info(f"Found {len(missing_monitored_eps)} missing monitored episode(s) for '{show_title}'.")

        # Refresh the series
        logger.info(f" - Refreshing series (ID: {series_id})...")
        refresh_res = refresh_series(series_id)
        if not refresh_res or "id" not in refresh_res:
            logger.warning(f"WARNING: Refresh command failed for {show_title}. Skipping.")
            time.sleep(5)
            continue

        logger.info(f"Refresh command accepted (ID: {refresh_res['id']}). Waiting 5s...")
        time.sleep(5)

        # Search specifically for these missing + monitored episodes
        episode_ids = [ep["id"] for ep in missing_monitored_eps]
        logger.info(f" - Searching for {len(episode_ids)} missing episodes in '{show_title}'...")
        search_res = episode_search_episodes(episode_ids)
        if search_res and "id" in search_res:
            logger.info(f"Search command accepted (ID: {search_res['id']}).")
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