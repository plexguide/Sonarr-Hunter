#!/usr/bin/env python3
"""
Huntarr [Sonarr Edition] - Python Version
Automatically search for missing episodes and quality upgrades in Sonarr
"""

import os
import time
import json
import random
import logging
import requests
import pathlib
from typing import List, Dict, Any, Optional, Union

# ---------------------------
# Main Configuration Variables
# ---------------------------

API_KEY = os.environ.get("API_KEY", "your-api-key")
API_URL = os.environ.get("API_URL", "http://your-sonarr-address:8989")

# Maximum number of missing shows to process per cycle
try:
    MAX_MISSING = int(os.environ.get("MAX_MISSING", "1"))
except ValueError:
    MAX_MISSING = 1
    print(f"Warning: Invalid MAX_MISSING value, using default: {MAX_MISSING}")

# Maximum number of upgrade episodes to process per cycle
try:
    MAX_UPGRADES = int(os.environ.get("MAX_UPGRADES", "5"))
except ValueError:
    MAX_UPGRADES = 5
    print(f"Warning: Invalid MAX_UPGRADES value, using default: {MAX_UPGRADES}")

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

# ---------------------------
# Miscellaneous Configuration
# ---------------------------

# If True, pick items randomly, if False go in order
RANDOM_SELECTION = os.environ.get("RANDOM_SELECTION", "true").lower() == "true"

# If MONITORED_ONLY is "true", only process missing or upgrade episodes from monitored shows
MONITORED_ONLY = os.environ.get("MONITORED_ONLY", "true").lower() == "true"

# SEARCH_TYPE controls what we search for:
# - "missing" => Only find shows with missing episodes
# - "upgrade" => Only find episodes that don't meet quality cutoff
# - "both"    => Do missing episodes first, then upgrade episodes
SEARCH_TYPE = os.environ.get("SEARCH_TYPE", "both")

# Enable debug mode to see API responses
DEBUG_MODE = os.environ.get("DEBUG_MODE", "false").lower() == "true"

# Setup logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("huntarr-sonarr")

# ---------------------------
# State Tracking Setup
# ---------------------------
STATE_DIR = pathlib.Path("/tmp/huntarr-state")
STATE_DIR.mkdir(parents=True, exist_ok=True)

PROCESSED_MISSING_FILE = STATE_DIR / "processed_missing_ids.txt"
PROCESSED_UPGRADE_FILE = STATE_DIR / "processed_upgrade_ids.txt"

# Create files if they don't exist
PROCESSED_MISSING_FILE.touch(exist_ok=True)
PROCESSED_UPGRADE_FILE.touch(exist_ok=True)

# ---------------------------
# Helper Functions
# ---------------------------
def debug_log(message: str, data: Any = None) -> None:
    """Log debug messages with optional data"""
    if DEBUG_MODE:
        logger.debug(f"{message}")
        if data is not None:
            try:
                as_json = json.dumps(data)
                if len(as_json) > 500:
                    as_json = as_json[:500] + "..."
                logger.debug(as_json)
            except:
                data_str = str(data)
                if len(data_str) > 500:
                    data_str = data_str[:500] + "..."
                logger.debug(data_str)

def load_processed_ids(file_path: pathlib.Path) -> List[int]:
    """Load processed show/episode IDs from a file"""
    try:
        with open(file_path, 'r') as f:
            return [int(line.strip()) for line in f if line.strip().isdigit()]
    except Exception as e:
        logger.error(f"Error reading processed IDs from {file_path}: {e}")
        return []

def save_processed_id(file_path: pathlib.Path, obj_id: int) -> None:
    """Save a processed show/episode ID to a file"""
    try:
        with open(file_path, 'a') as f:
            f.write(f"{obj_id}\n")
    except Exception as e:
        logger.error(f"Error writing to {file_path}: {e}")

def truncate_processed_list(file_path: pathlib.Path, max_lines: int = 500) -> None:
    """Truncate the processed list to prevent unbounded growth"""
    try:
        if file_path.stat().st_size > 10000:  # only check if file is somewhat large
            lines = file_path.read_text().splitlines()
            if len(lines) > max_lines:
                logger.info(f"Processed list is large. Truncating to last {max_lines} entries.")
                with open(file_path, 'w') as f:
                    f.write('\n'.join(lines[-max_lines:]) + '\n')
    except Exception as e:
        logger.error(f"Error truncating {file_path}: {e}")

def check_state_reset() -> None:
    """Check if state files need to be reset based on their age"""
    if STATE_RESET_INTERVAL_HOURS <= 0:
        logger.info("State reset is disabled. Processed items will be remembered indefinitely.")
        return
    
    missing_age = time.time() - PROCESSED_MISSING_FILE.stat().st_mtime
    upgrade_age = time.time() - PROCESSED_UPGRADE_FILE.stat().st_mtime
    reset_interval_seconds = STATE_RESET_INTERVAL_HOURS * 3600
    
    if missing_age >= reset_interval_seconds or upgrade_age >= reset_interval_seconds:
        logger.info(f"Resetting processed state files (older than {STATE_RESET_INTERVAL_HOURS} hours).")
        PROCESSED_MISSING_FILE.write_text("")
        PROCESSED_UPGRADE_FILE.write_text("")

# ---------------------------
# Sonarr API Functions
# ---------------------------
def sonarr_request(endpoint: str, method: str = "GET", data: Dict = None) -> Optional[Union[Dict, List]]:
    """
    Make a request to the Sonarr API (v3).
    `endpoint` should be something like 'series', 'command', 'wanted/cutoff', etc.
    """
    url = f"{API_URL}/api/v3/{endpoint}"
    headers = {
        "X-Api-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=30)
        else:
            logger.error(f"Unsupported HTTP method: {method}")
            return None
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"API request error: {e}")
        return None

def get_series() -> List[Dict]:
    """Get all series from Sonarr."""
    series_list = sonarr_request("series")
    if series_list:
        debug_log("Raw series API response sample:", series_list[:2] if len(series_list) > 2 else series_list)
    return series_list or []

def refresh_series(series_id: int) -> Optional[Dict]:
    """
    POST /api/v3/command
    {
      "name": "RefreshSeries",
      "seriesId": <series_id>
    }
    """
    data = {
        "name": "RefreshSeries",
        "seriesId": series_id
    }
    return sonarr_request("command", method="POST", data=data)

def missing_episode_search(series_id: int) -> Optional[Dict]:
    """
    POST /api/v3/command
    {
      "name": "MissingEpisodeSearch",
      "seriesId": <series_id>
    }
    """
    data = {
        "name": "MissingEpisodeSearch",
        "seriesId": series_id
    }
    return sonarr_request("command", method="POST", data=data)

def episode_search_series(series_id: int) -> Optional[Dict]:
    """
    Fallback search:
    POST /api/v3/command
    {
      "name": "EpisodeSearch",
      "seriesId": <series_id>
    }
    """
    data = {
        "name": "EpisodeSearch",
        "seriesId": series_id
    }
    return sonarr_request("command", method="POST", data=data)

def episode_search_episodes(episode_ids: List[int]) -> Optional[Dict]:
    """
    POST /api/v3/command
    {
      "name": "EpisodeSearch",
      "episodeIds": [...]
    }
    """
    data = {
        "name": "EpisodeSearch",
        "episodeIds": episode_ids
    }
    return sonarr_request("command", method="POST", data=data)

def get_cutoff_unmet(page: int = 1) -> Optional[Dict]:
    """
    GET /api/v3/wanted/cutoff?sortKey=airDateUtc&sortDirection=descending&includeSeriesInformation=true
        &page=<page>&pageSize=200
    Returns JSON with a "records" array and "totalRecords".
    """
    endpoint = (
        "wanted/cutoff?"
        "sortKey=airDateUtc&sortDirection=descending&includeSeriesInformation=true"
        f"&page={page}&pageSize=200"
    )
    return sonarr_request(endpoint, method="GET")

def get_cutoff_unmet_total_pages() -> int:
    """
    To find total pages, call the endpoint with page=1&pageSize=1, read totalRecords,
    then compute how many pages if each pageSize=200.
    """
    response = sonarr_request("wanted/cutoff?page=1&pageSize=1")
    if not response or "totalRecords" not in response:
        return 0
    
    total_records = response.get("totalRecords", 0)
    if not isinstance(total_records, int) or total_records < 1:
        return 0
    
    # Each page has up to 200 episodes
    total_pages = (total_records + 200 - 1) // 200
    return max(total_pages, 1)

# ---------------------------
# Missing Episodes Logic
# ---------------------------
def process_missing_episodes() -> None:
    """Process shows that have missing episodes."""
    logger.info("=== Checking for Missing Episodes ===")
    
    shows = get_series()
    if not shows:
        logger.error("ERROR: Unable to retrieve series data from Sonarr. Retrying in 60s...")
        time.sleep(60)
        return
    
    if MONITORED_ONLY:
        logger.info("MONITORED_ONLY=true => only monitored shows with missing episodes.")
        missing_shows = [
            s for s in shows
            if s.get("monitored") 
            and "statistics" in s 
            and s["statistics"].get("episodeCount", 0) > s["statistics"].get("episodeFileCount", 0)
        ]
    else:
        logger.info("MONITORED_ONLY=false => all shows with missing episodes.")
        missing_shows = [
            s for s in shows
            if "statistics" in s
            and s["statistics"].get("episodeCount", 0) > s["statistics"].get("episodeFileCount", 0)
        ]
    
    if not missing_shows:
        logger.info("No shows with missing episodes found.")
        return
    
    logger.info(f"Found {len(missing_shows)} show(s) with missing episodes.")
    processed_missing_ids = load_processed_ids(PROCESSED_MISSING_FILE)
    shows_processed = 0
    
    indices = list(range(len(missing_shows)))
    if RANDOM_SELECTION:
        random.shuffle(indices)
    
    for idx in indices:
        if MAX_MISSING > 0 and shows_processed >= MAX_MISSING:
            break
        
        show = missing_shows[idx]
        show_id = show.get("id")
        if not show_id or show_id in processed_missing_ids:
            continue
        
        show_title = show.get("title", "Unknown Title")
        ep_count = show.get("statistics", {}).get("episodeCount", 0)
        ep_file_count = show.get("statistics", {}).get("episodeFileCount", 0)
        missing = ep_count - ep_file_count
        
        logger.info(f"Processing missing episodes for \"{show_title}\" ({missing} missing).")
        
        logger.info(f" - Refreshing series (ID: {show_id})...")
        refresh_res = refresh_series(show_id)
        if not refresh_res or "id" not in refresh_res:
            logger.warning(f"WARNING: Refresh command failed for {show_title}. Skipping.")
            time.sleep(10)
            continue
        
        logger.info(f"Refresh command accepted (ID: {refresh_res['id']}). Waiting 5s...")
        time.sleep(5)
        
        logger.info(f" - MissingEpisodeSearch for \"{show_title}\"...")
        search_res = missing_episode_search(show_id)
        if search_res and "id" in search_res:
            logger.info(f"Search command accepted (ID: {search_res['id']}).")
        else:
            logger.warning("WARNING: MissingEpisodeSearch failed. Attempting fallback EpisodeSearch...")
            fallback_res = episode_search_series(show_id)
            if fallback_res and "id" in fallback_res:
                logger.info(f"Fallback EpisodeSearch accepted (ID: {fallback_res['id']}).")
        
        # Mark as processed
        save_processed_id(PROCESSED_MISSING_FILE, show_id)
        shows_processed += 1
        logger.info(f"Processed {shows_processed}/{MAX_MISSING} missing shows this cycle.")
    
    # Truncate processed list if needed
    truncate_processed_list(PROCESSED_MISSING_FILE)

# ---------------------------
# Quality Upgrades Logic
# ---------------------------
def process_cutoff_upgrades() -> None:
    """Process episodes that need quality upgrades."""
    logger.info("=== Checking for Quality Upgrades (Cutoff Unmet) ===")
    
    total_pages = get_cutoff_unmet_total_pages()
    if total_pages == 0:
        logger.info("No episodes found that need quality upgrades.")
        return
    
    logger.info(f"Found {total_pages} total pages of episodes that need quality upgrades.")
    processed_upgrade_ids = load_processed_ids(PROCESSED_UPGRADE_FILE)
    episodes_processed = 0
    
    # We'll loop until we've processed MAX_UPGRADES or run out of pages
    page = 1
    while True:
        if MAX_UPGRADES > 0 and episodes_processed >= MAX_UPGRADES:
            logger.info(f"Reached MAX_UPGRADES={MAX_UPGRADES} for this cycle.")
            break
        
        # If random selection, pick a random page each time
        if RANDOM_SELECTION and total_pages > 1:
            page = random.randint(1, total_pages)
        
        logger.info(f"Retrieving cutoff-unmet episodes (page={page} of {total_pages})...")
        cutoff_data = get_cutoff_unmet(page)
        if not cutoff_data or "records" not in cutoff_data:
            logger.error(f"ERROR: Unable to retrieve cutoff–unmet data from Sonarr on page {page}. Retrying next cycle.")
            break
        
        episodes = cutoff_data["records"]
        total_eps = len(episodes)
        logger.info(f"Found {total_eps} episodes on page {page} that need quality upgrades.")
        
        # Randomize or sequential
        indices = list(range(total_eps))
        if RANDOM_SELECTION:
            random.shuffle(indices)
        
        for idx in indices:
            if MAX_UPGRADES > 0 and episodes_processed >= MAX_UPGRADES:
                break
            
            ep_obj = episodes[idx]
            episode_id = ep_obj.get("id")
            if not episode_id or episode_id in processed_upgrade_ids:
                continue
            
            series_id = ep_obj.get("seriesId")
            season_num = ep_obj.get("seasonNumber")
            ep_num = ep_obj.get("episodeNumber")
            ep_title = ep_obj.get("title", "Unknown Episode Title")
            
            # If we already have 'seriesTitle' in response, use it
            series_title = ep_obj.get("seriesTitle", None)
            if not series_title:
                # fallback: request the series
                series_data = sonarr_request(f"series/{series_id}", method="GET")
                series_title = series_data.get("title") if series_data else "Unknown Series"
            
            logger.info(f"Processing upgrade for \"{series_title}\" - S{season_num}E{ep_num} - \"{ep_title}\" (Episode ID: {episode_id})")
            
            # If MONITORED_ONLY, ensure both series & episode are monitored
            if MONITORED_ONLY:
                ep_monitored = ep_obj.get("monitored", False)
                # The API sometimes includes series info; if not, fetch it
                if "series" in ep_obj and isinstance(ep_obj["series"], dict):
                    series_monitored = ep_obj["series"].get("monitored", False)
                else:
                    series_data = sonarr_request(f"series/{series_id}", "GET")
                    series_monitored = series_data.get("monitored", False) if series_data else False
                
                if not ep_monitored or not series_monitored:
                    logger.info("Skipping unmonitored episode or series.")
                    continue
            
            # Refresh the series
            logger.info(" - Refreshing series information...")
            refresh_res = refresh_series(series_id)
            if not refresh_res or "id" not in refresh_res:
                logger.warning("WARNING: Refresh command failed. Skipping this episode.")
                time.sleep(10)
                continue
            
            logger.info(f"Refresh command accepted (ID: {refresh_res['id']}). Waiting 5s...")
            time.sleep(5)
            
            # Search for the episode (upgrade)
            logger.info(" - Searching for quality upgrade...")
            search_res = episode_search_episodes([episode_id])
            if search_res and "id" in search_res:
                logger.info(f"Search command accepted (ID: {search_res['id']}).")
                # Mark processed
                save_processed_id(PROCESSED_UPGRADE_FILE, episode_id)
                episodes_processed += 1
                logger.info(f"Processed {episodes_processed}/{MAX_UPGRADES} upgrade episodes this cycle.")
            else:
                logger.warning(f"WARNING: Search command failed for episode ID {episode_id}.")
                time.sleep(10)
        
        # Move to the next page if not random
        if not RANDOM_SELECTION:
            page += 1
            if page > total_pages:
                break
        else:
            # In random mode, we just do one random page at a time, then break
            # or repeat until we reach the MAX_UPGRADES.
            pass
    
    logger.info(f"Completed processing {episodes_processed} upgrade episodes for this cycle.")
    truncate_processed_list(PROCESSED_UPGRADE_FILE)

# ---------------------------
# Main Loop
# ---------------------------
def calculate_reset_time() -> None:
    """Calculate and display time until the next state reset."""
    if STATE_RESET_INTERVAL_HOURS <= 0:
        logger.info("State reset is disabled. Processed items will be remembered indefinitely.")
        return
    
    current_time = time.time()
    missing_age = current_time - PROCESSED_MISSING_FILE.stat().st_mtime
    upgrade_age = current_time - PROCESSED_UPGRADE_FILE.stat().st_mtime
    
    reset_interval_seconds = STATE_RESET_INTERVAL_HOURS * 3600
    missing_remaining = reset_interval_seconds - missing_age
    upgrade_remaining = reset_interval_seconds - upgrade_age
    
    remaining_seconds = min(missing_remaining, upgrade_remaining)
    remaining_minutes = int(remaining_seconds / 60)
    
    logger.info(f"State reset will occur in approximately {remaining_minutes} minutes.")

def main_loop() -> None:
    """Main processing loop"""
    while True:
        # Reset old state files if needed
        check_state_reset()
        
        # Process based on SEARCH_TYPE
        if SEARCH_TYPE == "missing":
            process_missing_episodes()
        elif SEARCH_TYPE == "upgrade":
            process_cutoff_upgrades()
        elif SEARCH_TYPE == "both":
            process_missing_episodes()
            process_cutoff_upgrades()
        else:
            logger.error(f"Unknown SEARCH_TYPE={SEARCH_TYPE}. Use 'missing','upgrade','both'.")
        
        # Calculate minutes remaining until state reset
        calculate_reset_time()
        
        logger.info(f"Cycle complete. Waiting {SLEEP_DURATION} seconds before next cycle...")
        logger.info("⭐ Enjoy the Tool? Donate @ https://donate.plex.one towards my Daughter's 501 College Fund!")
        time.sleep(SLEEP_DURATION)

if __name__ == "__main__":
    logger.info("=== Huntarr [Sonarr Edition] Starting ===")
    logger.info(f"API URL: {API_URL}")
    debug_log(f"API KEY: {API_KEY}")
    logger.info(f"Configuration: MAX_MISSING={MAX_MISSING}, MAX_UPGRADES={MAX_UPGRADES}, SLEEP_DURATION={SLEEP_DURATION}s")
    logger.info(f"Configuration: MONITORED_ONLY={MONITORED_ONLY}, RANDOM_SELECTION={RANDOM_SELECTION}, SEARCH_TYPE={SEARCH_TYPE}")
    
    try:
        main_loop()
    except KeyboardInterrupt:
        logger.info("Huntarr stopped by user.")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise
