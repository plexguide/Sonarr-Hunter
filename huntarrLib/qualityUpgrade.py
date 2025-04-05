from pathlib import Path
import time
import random
from typing import List
from .logger import logger
from .config import settings
import huntarrLib.sonarr_api as sonarr_api


# ---------------------------
# Quality Upgrades Logic
# ---------------------------
def process_cutoff_upgrades() -> None:
    """Process episodes that need quality upgrades (cutoff unmet)."""
    logger.info("=== Checking for Quality Upgrades (Cutoff Unmet) ===")

    total_pages = sonarr_api.get_cutoff_unmet_total_pages()
    if total_pages == 0:
        logger.info("No episodes found that need quality upgrades.")
        return

    logger.info(f"Found {total_pages} total pages of episodes that need quality upgrades.")
    processed_upgrade_ids = sonarr_api.load_processed_ids(settings.PROCESSED_UPGRADE_FILE)
    episodes_processed = 0

    page = 1
    while True:
        if int(settings.MAX_MISSING) > 0 and episodes_processed >= int(settings.MAX_UPGRADES):
            logger.info(f"Reached MAX_UPGRADES={settings['MAX_UPGRADES']} for this cycle.")
            break

        # If random selection, pick a random page each iteration
        if settings['RANDOM_SELECTION'] and total_pages > 1:
            page = random.randint(1, total_pages)

        logger.info(f"Retrieving cutoff-unmet episodes (page={page} of {total_pages})...")
        cutoff_data = sonarr_api.get_cutoff_unmet(page)
        if not cutoff_data or "records" not in cutoff_data:
            logger.error(f"ERROR: Unable to retrieve cutoff–unmet data from Sonarr on page {page}.")
            break

        episodes = cutoff_data["records"]
        total_eps = len(episodes)
        logger.info(f"Found {total_eps} episodes on page {page} that need quality upgrades.")

        # Randomize or sequential indices
        indices = list(range(total_eps))
        if settings.RANDOM_SELECTION:
            random.shuffle(indices)

        for idx in indices:
            if int(settings.MAX_UPGRADES) > 0 and episodes_processed >= int(settings.MAX_UPGRADES):
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
                series_data = sonarr_api.sonarr_request(f"series/{series_id}", method="GET")
                if series_data:
                    series_title = series_data.get("title", "Unknown Series")
                else:
                    series_title = "Unknown Series"

            logger.info(f"Processing upgrade for \"{series_title}\" - S{season_num}E{ep_num} - \"{ep_title}\" (Episode ID: {episode_id})")

            # If MONITORED_ONLY, ensure both series & episode are monitored
            if settings.MONITORED_ONLY:
                ep_monitored = ep_obj.get("monitored", False)
                # Check if series info is already included
                if "series" in ep_obj and isinstance(ep_obj["series"], dict):
                    series_monitored = ep_obj["series"].get("monitored", False)
                else:
                    # retrieve the series
                    series_data = sonarr_api.sonarr_request(f"series/{series_id}", "GET")
                    series_monitored = series_data.get("monitored", False) if series_data else False

                if not ep_monitored or not series_monitored:
                    logger.info("Skipping unmonitored episode or series.")
                    continue

            # Refresh the series
            logger.info(" - Refreshing series information...")
            refresh_res = sonarr_api.refresh_series(series_id)
            if not refresh_res or "id" not in refresh_res:
                logger.warning("WARNING: Refresh command failed. Skipping this episode.")
                time.sleep(10)
                continue

            logger.info(f"Refresh command accepted (ID: {refresh_res['id']}). Waiting 5s...")
            time.sleep(5)

            # Search for the episode (upgrade)
            logger.info(" - Searching for quality upgrade...")
            search_res = sonarr_api.episode_search_episodes([episode_id])
            if search_res and "id" in search_res:
                logger.info(f"Search command accepted (ID: {search_res['id']}).")
                # Mark processed
                sonarr_api.save_processed_id(settings.PROCESSED_UPGRADE_FILE, episode_id)
                episodes_processed += 1
                logger.info(f"Processed {episodes_processed}/{settings.MAX_UPGRADES} upgrade episodes this cycle.")
            else:
                logger.warning(f"WARNING: Search command failed for episode ID {episode_id}.")
                time.sleep(10)

        # Move to the next page if not random
        if not settings['RANDOM_SELECTION']:
            page += 1
            if page > total_pages:
                break
        else:
            # In random mode, we just handle one random page this iteration,
            # then either break or keep looping until we hit MAX_UPGRADES.
            pass

    logger.info(f"Completed processing {episodes_processed} upgrade episodes for this cycle.")
    truncate_processed_list(settings.PROCESSED_UPGRADE_FILE)


def truncate_processed_list(file_path: Path, max_lines: int = 500) -> None:
    """Truncate the processed list to prevent unbounded growth."""
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()

        if len(lines) > 10000:
            logger.info(f"Processed list is large ({len(lines)} lines). Truncating to last {max_lines} entries.")
            with open(file_path, 'w') as file:
                file.writelines(lines[-max_lines:])
    except Exception as e:
        logger.error(f"Error truncating {file_path}: {e}")


def load_processed_ids(file_path: Path) -> List[int]:
    """Load processed show/episode IDs from a file."""
    try:
        with open(file_path, 'r') as f:
            return [int(line.strip()) for line in f if line.strip().isdigit()]
    except Exception as e:
        logger.error(f"Error reading processed IDs from {file_path}: {e}")
        return []


def save_processed_id(file_path: Path, obj_id: int) -> None:
    """Save a processed show/episode ID to a file."""
    try:
        with open(file_path, 'a') as f:
            f.write(f"{obj_id}\n")
    except Exception as e:
        logger.error(f"Error writing to {file_path}: {e}")


def process_missing_episodes() -> None:
    """
    Process shows that have missing episodes, but respect
    unmonitored seasons/episodes. We'll fetch episodes for each show
    and only search for episodes that are BOTH missing and monitored.
    """
    logger.info("=== Checking for Missing Episodes ===")

    shows = sonarr_api.get_series()
    if not shows:
        logger.error("ERROR: Unable to retrieve series data from Sonarr. Retrying in 60s...")
        time.sleep(60)
        return

    # Optionally filter to only monitored shows (if MONITORED_ONLY==true).
    if settings.MONITORED_ONLY:
        logger.info("MONITORED_ONLY=true => only fully monitored shows.")
        shows = [s for s in shows if s.get("monitored") is True]
    else:
        logger.info("MONITORED_ONLY=false => all shows, even if unmonitored.")

    if not shows:
        logger.info("No shows to process.")
        return

    processed_missing_ids = load_processed_ids(settings.PROCESSED_MISSING_FILE)
    shows_processed = 0

    indices = list(range(len(shows)))
    if settings.RANDOM_SELECTION:
        random.shuffle(indices)

    for idx in indices:
        if int(settings.MAX_MISSING) > 0 and shows_processed >= int(settings.MAX_MISSING):
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
        episode_list = sonarr_api.sonarr_request(f"episode?seriesId={series_id}", method="GET")
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
        refresh_res = sonarr_api.refresh_series(series_id)
        if not refresh_res or "id" not in refresh_res:
            logger.warning(f"WARNING: Refresh command failed for {show_title}. Skipping.")
            time.sleep(5)
            continue

        logger.info(f"Refresh command accepted (ID: {refresh_res['id']}). Waiting 5s...")
        time.sleep(5)

        # Search specifically for these missing + monitored episodes
        episode_ids = [ep["id"] for ep in missing_monitored_eps]
        logger.info(f" - Searching for {len(episode_ids)} missing episodes in '{show_title}'...")
        search_res = sonarr_api.episode_search_episodes(episode_ids)
        if search_res and "id" in search_res:
            logger.info(f"Search command accepted (ID: {search_res['id']}).")
        else:
            logger.warning(f"WARNING: EpisodeSearch failed for show '{show_title}' (ID: {series_id}).")

        # Mark as processed
        save_processed_id(settings['PROCESSED_MISSING_FILE'], series_id)
        shows_processed += 1
        logger.info(f"Processed {shows_processed}/{int(settings.MAX_MISSING)} missing shows this cycle.")

    # Truncate processed list if needed
    truncate_processed_list(settings.PROCESSED_MISSING_FILE)
    
