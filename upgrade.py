#!/usr/bin/env python3
"""
Quality Upgrade Processing
Handles searching for episodes that need quality upgrades in Sonarr
"""

import random
import time
from utils.logger import logger
from config import HUNT_UPGRADE_EPISODES, MONITORED_ONLY, RANDOM_SELECTION
from api import get_cutoff_unmet, get_cutoff_unmet_total_pages, refresh_series, episode_search_episodes, sonarr_request
from state import load_processed_ids, save_processed_id, truncate_processed_list, PROCESSED_UPGRADE_FILE

def process_cutoff_upgrades() -> bool:
    """
    Process episodes that need quality upgrades (cutoff unmet).
    
    Returns:
        True if any processing was done, False otherwise
    """
    logger.info("=== Checking for Quality Upgrades (Cutoff Unmet) ===")

    # Skip if HUNT_UPGRADE_EPISODES is set to 0
    if HUNT_UPGRADE_EPISODES <= 0:
        logger.info("HUNT_UPGRADE_EPISODES is set to 0, skipping quality upgrades")
        return False

    total_pages = get_cutoff_unmet_total_pages()
    if total_pages == 0:
        logger.info("No episodes found that need quality upgrades.")
        return False

    logger.info(f"Found {total_pages} total pages of episodes that need quality upgrades.")
    processed_upgrade_ids = load_processed_ids(PROCESSED_UPGRADE_FILE)
    episodes_processed = 0
    processing_done = False

    page = 1
    while True:
        if episodes_processed >= HUNT_UPGRADE_EPISODES:
            logger.info(f"Reached HUNT_UPGRADE_EPISODES={HUNT_UPGRADE_EPISODES} for this cycle.")
            break

        # If random selection, pick a random page each iteration
        if RANDOM_SELECTION and total_pages > 1:
            page = random.randint(1, total_pages)

        logger.info(f"Retrieving cutoff-unmet episodes (page={page} of {total_pages})...")
        cutoff_data = get_cutoff_unmet(page)
        if not cutoff_data or "records" not in cutoff_data:
            logger.error(f"ERROR: Unable to retrieve cutoff–unmet data from Sonarr on page {page}.")
            break

        episodes = cutoff_data["records"]
        total_eps = len(episodes)
        logger.info(f"Found {total_eps} episodes on page {page} that need quality upgrades.")

        # Randomize or sequential indices
        indices = list(range(total_eps))
        if RANDOM_SELECTION:
            random.shuffle(indices)

        for idx in indices:
            if episodes_processed >= HUNT_UPGRADE_EPISODES:
                break

            ep_obj = episodes[idx]
            episode_id = ep_obj.get("id")
            if not episode_id or episode_id in processed_upgrade_ids:
                continue

            series_id = ep_obj.get("seriesId")
            season_num = ep_obj.get("seasonNumber")
            ep_num = ep_obj.get("episodeNumber")
            ep_title = ep_obj.get("title", "Unknown Episode Title")

            series_title = ep_obj.get("seriesTitle", None)
            if not series_title:
                # fallback: request the series
                series_data = sonarr_request(f"series/{series_id}", method="GET")
                if series_data:
                    series_title = series_data.get("title", "Unknown Series")
                else:
                    series_title = "Unknown Series"

            logger.info(f"Processing upgrade for \"{series_title}\" - S{season_num}E{ep_num} - \"{ep_title}\" (Episode ID: {episode_id})")

            # If MONITORED_ONLY, ensure both series & episode are monitored
            if MONITORED_ONLY:
                ep_monitored = ep_obj.get("monitored", False)
                # Check if series info is already included
                if "series" in ep_obj and isinstance(ep_obj["series"], dict):
                    series_monitored = ep_obj["series"].get("monitored", False)
                else:
                    # retrieve the series
                    series_data = sonarr_request(f"series/{series_id}", "GET")
                    series_monitored = series_data.get("monitored", False) if series_data else False

                if not ep_monitored or not series_monitored:
                    logger.info("Skipping unmonitored episode or series.")
                    continue

            # Refresh the series
            logger.info(" - Refreshing series information...")
            refresh_res = refresh_series(series_id)
            if not refresh_res:
                logger.warning("WARNING: Refresh command failed. Skipping this episode.")
                continue
            
            logger.info(f"Refresh command completed successfully.")

            # Search for the episode (upgrade)
            logger.info(" - Searching for quality upgrade...")
            search_res = episode_search_episodes([episode_id])
            if search_res:
                logger.info(f"Search command completed successfully.")
                # Mark processed
                save_processed_id(PROCESSED_UPGRADE_FILE, episode_id)
                episodes_processed += 1
                processing_done = True
                logger.info(f"Processed {episodes_processed}/{HUNT_UPGRADE_EPISODES} upgrade episodes this cycle.")
            else:
                logger.warning(f"WARNING: Search command failed for episode ID {episode_id}.")
                continue

        # Move to the next page if not random
        if not RANDOM_SELECTION:
            page += 1
            if page > total_pages:
                break
        else:
            # In random mode, we just handle one random page this iteration,
            # then either break or keep looping until we hit HUNT_UPGRADE_EPISODES.
            pass

    logger.info(f"Completed processing {episodes_processed} upgrade episodes for this cycle.")
    truncate_processed_list(PROCESSED_UPGRADE_FILE)
    
    return processing_done