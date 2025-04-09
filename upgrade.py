#!/usr/bin/env python3
"""
Quality Upgrade Processing
Handles searching for episodes that need quality upgrades in Sonarr
"""

import random
import time
import datetime
from utils.logger import logger
from config import (
    HUNT_UPGRADE_EPISODES, 
    MONITORED_ONLY, 
    RANDOM_SELECTION,
    RANDOM_UPGRADES,
    SKIP_FUTURE_EPISODES,
    SKIP_SERIES_REFRESH
)
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

    # Get current date for future episode filtering
    current_date = datetime.datetime.now().date()

    # Use the specific RANDOM_UPGRADES setting
    # (no longer dependent on the master RANDOM_SELECTION setting)
    should_use_random = RANDOM_UPGRADES
    
    if should_use_random:
        logger.info("Using random selection for quality upgrades (RANDOM_UPGRADES=true)")
    else:
        logger.info("Using sequential selection for quality upgrades (RANDOM_UPGRADES=false)")
        page = 1

    while True:
        if episodes_processed >= HUNT_UPGRADE_EPISODES:
            logger.info(f"Reached HUNT_UPGRADE_EPISODES={HUNT_UPGRADE_EPISODES} for this cycle.")
            break

        # If random selection is enabled, pick a random page each iteration
        if should_use_random and total_pages > 1:
            page = random.randint(1, total_pages)
        # If sequential and we've reached the end, we're done
        elif not should_use_random and page > total_pages:
            break

        logger.info(f"Retrieving cutoff-unmet episodes (page={page} of {total_pages})...")
        cutoff_data = get_cutoff_unmet(page)
        if not cutoff_data or "records" not in cutoff_data:
            logger.error(f"ERROR: Unable to retrieve cutoff–unmet data from Sonarr on page {page}.")
            
            # In sequential mode, try the next page
            if not should_use_random:
                page += 1
                continue
            else:
                break

        episodes = cutoff_data["records"]
        total_eps = len(episodes)
        logger.info(f"Found {total_eps} episodes on page {page} that need quality upgrades.")

        # Randomize or sequential indices within the page
        indices = list(range(total_eps))
        if should_use_random:
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

            # Skip future episodes if SKIP_FUTURE_EPISODES is enabled
            if SKIP_FUTURE_EPISODES:
                air_date_str = ep_obj.get("airDateUtc")
                if air_date_str:
                    try:
                        # Parse the UTC date string
                        air_date = datetime.datetime.fromisoformat(air_date_str.replace('Z', '+00:00')).date()
                        if air_date > current_date:
                            logger.info(f"Skipping future episode '{series_title}' - S{season_num}E{ep_num} - '{ep_title}' (airs on {air_date})")
                            continue
                    except (ValueError, TypeError):
                        # If date parsing fails, proceed with the episode
                        pass

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

            # Refresh the series only if SKIP_SERIES_REFRESH is not enabled
            if not SKIP_SERIES_REFRESH:
                logger.info(" - Refreshing series information...")
                refresh_res = refresh_series(series_id)
                if not refresh_res:
                    logger.warning("WARNING: Refresh command failed. Skipping this episode.")
                    continue
                logger.info(f"Refresh command completed successfully.")
            else:
                logger.info(" - Skipping series refresh (SKIP_SERIES_REFRESH=true)")

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

        # Move to the next page if using sequential mode
        if not should_use_random:
            page += 1
        # In random mode, we just handle one random page this iteration,
        # then check if we've processed enough episodes or continue to another random page
    
    logger.info(f"Completed processing {episodes_processed} upgrade episodes for this cycle.")
    truncate_processed_list(PROCESSED_UPGRADE_FILE)
    
    return processing_done