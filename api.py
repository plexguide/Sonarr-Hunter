#!/usr/bin/env python3
"""
Sonarr API Helper Functions
Handles all communication with the Sonarr API
"""

import requests
from typing import List, Dict, Any, Optional, Union
from utils.logger import logger, debug_log
from config import API_KEY, API_URL

# Create a session for reuse
session = requests.Session()

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
            response = session.get(url, headers=headers, timeout=30)
        elif method.upper() == "POST":
            response = session.post(url, headers=headers, json=data, timeout=30)
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

def get_episodes_for_series(series_id: int) -> Optional[List[Dict]]:
    """Get all episodes for a specific series"""
    return sonarr_request(f"episode?seriesId={series_id}", method="GET")

def get_missing_episodes(pageSize: int = 1000) -> Optional[Dict]:
    """
    GET /api/v3/wanted/missing?pageSize=<pageSize>&includeSeriesInformation=true
    Returns JSON with a "records" array of missing episodes and "totalRecords".
    """
    endpoint = f"wanted/missing?pageSize={pageSize}&includeSeriesInformation=true"
    return sonarr_request(endpoint, method="GET")

def get_series_with_missing_episodes() -> List[Dict]:
    """
    Fetch all shows that have missing episodes using the wanted/missing endpoint.
    Returns a list of series objects with an additional 'missingEpisodes' field 
    containing the list of missing episodes for that series.
    """
    missing_data = get_missing_episodes()
    if not missing_data or "records" not in missing_data:
        return []
    
    # Group missing episodes by series ID
    series_with_missing = {}
    for episode in missing_data.get("records", []):
        series_id = episode.get("seriesId")
        series_title = None
        
        # Try to get series info from the episode record
        if "series" in episode and isinstance(episode["series"], dict):
            series_info = episode["series"]
            series_title = series_info.get("title")
        
        if series_id not in series_with_missing:
            # Initialize the series entry if it doesn't exist
            if series_title:
                # We have the series info from the episode
                series_with_missing[series_id] = {
                    "id": series_id,
                    "title": series_title,
                    "monitored": series_info.get("monitored", False),
                    "missingEpisodes": [episode]
                }
            else:
                # We need to fetch the series info
                series_info = sonarr_request(f"series/{series_id}", method="GET")
                if series_info:
                    series_with_missing[series_id] = {
                        "id": series_id,
                        "title": series_info.get("title", "Unknown Show"),
                        "monitored": series_info.get("monitored", False),
                        "missingEpisodes": [episode]
                    }
        else:
            # Add the episode to the existing series entry
            series_with_missing[series_id]["missingEpisodes"].append(episode)
    
    # Convert to list and add count for convenience
    result = []
    for series_id, series_data in series_with_missing.items():
        series_data["missingEpisodeCount"] = len(series_data["missingEpisodes"])
        result.append(series_data)
    
    return result