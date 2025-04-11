#!/usr/bin/env python3
"""
Keys manager for Huntarr
Handles storage and retrieval of API keys and URLs from huntarr.json
"""

import os
import json
import pathlib
import logging
from typing import Dict, Any, Optional, Tuple

# Create a simple logger
logging.basicConfig(level=logging.INFO)
keys_logger = logging.getLogger("keys_manager")

# Settings directory - use the same directory as settings_manager
SETTINGS_DIR = pathlib.Path("/config/settings")
SETTINGS_DIR.mkdir(parents=True, exist_ok=True)

SETTINGS_FILE = SETTINGS_DIR / "huntarr.json"

def save_api_keys(app_type: str, api_url: str, api_key: str) -> bool:
    """
    Save API keys and URL for an app.
    
    Args:
        app_type: The type of app (sonarr, radarr, etc.)
        api_url: The API URL for the app
        api_key: The API key
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure settings file exists
        if not SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, 'w') as f:
                json.dump({}, f)
        
        # Load existing settings
        with open(SETTINGS_FILE, 'r') as f:
            settings_data = json.load(f)
        
        # Ensure we have a connections section
        if "connections" not in settings_data:
            settings_data["connections"] = {}
            
        # Create or update connection info for this app
        settings_data["connections"][app_type] = {
            'api_url': api_url,
            'api_key': api_key
        }
        
        # Save the file
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings_data, f, indent=2)
        
        keys_logger.info(f"Saved API keys for {app_type}")
        return True
    except Exception as e:
        keys_logger.error(f"Error saving API keys: {e}")
        return False

def get_api_keys(app_type: str) -> Tuple[str, str]:
    """
    Get API keys and URL for an app.
    
    Args:
        app_type: The type of app (sonarr, radarr, etc.)
    
    Returns:
        Tuple[str, str]: (api_url, api_key)
    """
    try:
        # Check if settings file exists
        if not SETTINGS_FILE.exists():
            keys_logger.warning(f"Settings file not found at {SETTINGS_FILE}")
            return '', ''
            
        # Load settings file
        with open(SETTINGS_FILE, 'r') as f:
            settings_data = json.load(f)
        
        # Get connection info
        connections = settings_data.get("connections", {})
        app_config = connections.get(app_type, {})
        
        api_url = app_config.get('api_url', '')
        api_key = app_config.get('api_key', '')
        
        # Log what we found (without revealing the full API key)
        masked_key = "****" + api_key[-4:] if len(api_key) > 4 else "****" if api_key else ""
        keys_logger.debug(f"Retrieved API info for {app_type}: URL={api_url}, Key={masked_key}")
        
        # Return URL and key
        return api_url, api_key
    except Exception as e:
        keys_logger.error(f"Error getting API keys: {e}")
        return '', ''

def list_configured_apps() -> Dict[str, bool]:
    """
    List all apps and whether they're configured.
    
    Returns:
        Dict[str, bool]: Dictionary of app_type -> is_configured
    """
    result = {
        'sonarr': False,
        'radarr': False,
        'lidarr': False,
        'readarr': False
    }
    
    try:
        # Check if settings file exists
        if not SETTINGS_FILE.exists():
            return result
            
        # Load settings file
        with open(SETTINGS_FILE, 'r') as f:
            settings_data = json.load(f)
        
        # Get connection info
        connections = settings_data.get("connections", {})
        
        # Check each app
        for app in result.keys():
            if app in connections and connections[app].get('api_url') and connections[app].get('api_key'):
                result[app] = True
        
        return result
    except Exception as e:
        keys_logger.error(f"Error listing configured apps: {e}")
        return result