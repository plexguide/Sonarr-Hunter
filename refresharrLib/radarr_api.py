from typing import Dict, Optional, List, Union
from .config import settings
from .logger import logger
import requests
import time
import random
from .utils import (
    load_processed_ids, save_processed_id, truncate_processed_list
)
# ---------------------------
# Radarr API Functions
# ---------------------------


def radarr_request(
        endpoint: str, method: str = "GET", data: Dict = None
        ) -> Optional[Union[Dict, List]]:
    """
    Make a request to the Radarr API (v3).
    `endpoint` should be something like 'series',
    'command', 'wanted/cutoff', etc.
    """
    url = f"{settings.RADARR_API_URL}/api/v3/{endpoint}"
    headers = {
        "X-Api-Key": settings.RADARR_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(
                url, headers=headers, json=data, timeout=30)
        else:
            logger.error(f"Unsupported HTTP method: {method}")
            return None

        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"API request error: {e}")
        return None


def get_movies() -> List[Dict]:
    """Get all movies from Radarr (full list)"""
    result = radarr_request("movie")
    if result:
        logger.debug(
            "Raw movies API response sample:",
            result[:2] if len(result) > 2 else result)
    return result or []


def get_cutoff_unmet() -> List[Dict]:
    """
    Directly query Radarr for only those movies
    where the quality cutoff is not met.
    This is the most reliable way for big libraries.
    Optionally filter by monitored.
    """
    query = "movie?qualityCutoffNotMet=true"
    if settings.MONITORED_ONLY:
        # Append &monitored=true to the querystring
        query += "&monitored=true"

    # Perform the request
    result = radarr_request(query, method="GET")
    return result or []


def refresh_movie(movie_id: int) -> Optional[Dict]:
    data = {
        "name": "RefreshMovie",
        "movieIds": [movie_id]
    }
    return radarr_request("command", method="POST", data=data)


def movie_search(movie_id: int) -> Optional[Dict]:
    """Search for a movie by ID"""
    data = {
        "name": "MoviesSearch",
        "movieIds": [movie_id]
    }
    return radarr_request("command", method="POST", data=data)


def rescan_movie(movie_id: int) -> Optional[Dict]:
    """Rescan movie files"""
    data = {
        "name": "RescanMovie",
        "movieIds": [movie_id]
    }
    return radarr_request("command", method="POST", data=data)


def process_missing_movies() -> None:
    """Process missing movies from the library"""
    logger.info("=== Checking for Missing Movies ===")

    movies = get_movies()
    if not movies:
        logger.error(
            "ERROR: Unable to retrieve movie data from Radarr. "
            "Retrying in 60s...")
        time.sleep(60)
        return

    if settings.MONITORED_ONLY:
        logger.info(
            "MONITORED_ONLY=true => only monitored movies without files.")
        missing_movies = [
            m for m in movies if m.get('monitored') and not m.get('hasFile')
            ]
    else:
        logger.info("MONITORED_ONLY=false => all movies without files.")
        missing_movies = [m for m in movies if not m.get('hasFile')]

    if not missing_movies:
        logger.info("No missing movies found.")
        return

    logger.info(f"Found {len(missing_movies)} movie(s) with missing files.")
    processed_missing_ids = load_processed_ids(settings.PROCESSED_MISSING_FILE)
    movies_processed = 0

    indices = list(range(len(missing_movies)))
    if settings.RANDOM_SELECTION:
        random.shuffle(indices)

    for i in indices:
        if (int(settings.MAX_MISSING) > 0 and
                movies_processed >= int(settings.MAX_MISSING)):
            break

        movie = missing_movies[i]
        movie_id = movie.get('id')
        if not movie_id or movie_id in processed_missing_ids:
            continue

        title = movie.get('title', 'Unknown Title')
        year = movie.get('year', 'Unknown Year')

        logger.info("Processing missing movie "
                    f"\"{title} ({year})\" (ID: {movie_id}).")

        # Refresh
        logger.info(" - Refreshing movie...")
        refresh_res = refresh_movie(movie_id)
        if not refresh_res or 'id' not in refresh_res:
            logger.warning(
                f"WARNING: Refresh command failed for {title}. Skipping.")
            time.sleep(10)
            continue

        logger.info(
            f"Refresh command accepted (ID: {refresh_res.get('id')}). "
            "Waiting 5s...")
        time.sleep(5)

        # Search
        logger.info(f" - Searching for \"{title}\"...")
        search_res = movie_search(movie_id)
        if search_res and 'id' in search_res:
            logger.info("Search command accepted "
                        f"(ID: {search_res.get('id')}).")
        else:
            logger.warning("WARNING: Movie search failed.")

        # Rescan
        logger.info(" - Rescanning movie folder...")
        rescan_res = rescan_movie(movie_id)
        if rescan_res and 'id' in rescan_res:
            logger.info("Rescan command accepted "
                        f"(ID: {rescan_res.get('id')}).")
        else:
            logger.warning("WARNING: Rescan command not available or failed.")

        # Mark processed
        save_processed_id(settings.PROCESSED_MISSING_FILE, movie_id)
        movies_processed += 1
        logger.info(
            f"Processed {movies_processed}/{settings.MAX_MISSING} "
            "missing movies this cycle.")

    # Truncate processed list if needed
        if (settings.SEARCH_TYPE == "both"):
            truncate_processed_list(settings.PROCESSED_UPGRADE_FILE, 250)
        else:
            truncate_processed_list(settings.PROCESSED_UPGRADE_FILE)


def process_cutoff_upgrades() -> None:
    """Process movies that need quality upgrades."""
    logger.info("=== Checking for Quality Upgrades (Cutoff Unmet) ===")

    # Instead of retrieving the full movie list and filtering,
    # directly query the subset of movies that do not meet cutoff:
    upgrade_movies = get_cutoff_unmet()

    if not upgrade_movies:
        logger.info("No movies found that need quality upgrades.")
        return

    logger.info(
        f"Found {len(upgrade_movies)} movies that need quality upgrades.")
    processed_upgrade_ids = load_processed_ids(settings.PROCESSED_UPGRADE_FILE)
    movies_processed = 0

    indices = list(range(len(upgrade_movies)))
    if settings.RANDOM_SELECTION:
        random.shuffle(indices)

    for i in indices:
        if (int(settings.MAX_UPGRADES) > 0 and
                movies_processed >= int(settings.MAX_UPGRADES)):
            break

        movie = upgrade_movies[i]
        movie_id = movie.get('id')
        if not movie_id or movie_id in processed_upgrade_ids:
            continue

        title = movie.get('title', 'Unknown Title')
        year = movie.get('year', 'Unknown Year')
        logger.info(
            "Processing quality upgrade for "
            f"\"{title} ({year})\" (ID: {movie_id})")

        # Refresh
        logger.info(" - Refreshing movie information...")
        refresh_res = refresh_movie(movie_id)
        if not refresh_res or 'id' not in refresh_res:
            logger.warning(
                "WARNING: Refresh command failed. Skipping this movie.")
            time.sleep(10)
            continue

        logger.info(
            f"Refresh command accepted (ID: {refresh_res.get('id')}). "
            "Waiting 5s...")
        time.sleep(5)

        # Search
        logger.info(" - Searching for quality upgrade...")
        search_res = movie_search(movie_id)
        if search_res and 'id' in search_res:
            logger.info(
                f"Search command accepted (ID: {search_res.get('id')}).")

            # Rescan
            logger.info(" - Rescanning movie folder...")
            rescan_res = rescan_movie(movie_id)
            if rescan_res and 'id' in rescan_res:
                logger.info(
                    f"Rescan command accepted (ID: {rescan_res.get('id')}).")
            else:
                logger.warning(
                    "WARNING: Rescan command not available or failed.")

            # Mark processed
            save_processed_id(settings.PROCESSED_UPGRADE_FILE, movie_id)
            movies_processed += 1
            logger.info(
                f"Processed {movies_processed}/{settings.MAX_UPGRADES} "
                "upgrade movies this cycle.")
        else:
            logger.warning("WARNING: Search command failed for movie ID "
                           f"{movie_id}.")
            time.sleep(10)

    logger.info(f"Completed processing {movies_processed} "
                "upgrade movies for this cycle.")
    if (settings.SEARCH_TYPE == "both"):
        truncate_processed_list(settings.PROCESSED_UPGRADE_FILE, 250)
    else:
        truncate_processed_list(settings.PROCESSED_UPGRADE_FILE)
