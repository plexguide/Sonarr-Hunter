#!/usr/bin/env python3
"""
Keys manager for Huntarr
Handles secure storage and retrieval of API keys and URLs
"""

import os
import json
import hashlib
import base64
import pathlib
import logging
from typing import Dict, Any, Optional, Tuple

# Create a simple logger
logging.basicConfig(level=logging.INFO)
keys_logger = logging.getLogger("keys_manager")

# Keys directory setup
KEYS_DIR = pathlib.Path("/config/apps")
KEYS_DIR.mkdir(parents=True, exist_ok=True)

KEYS_FILE = KEYS_DIR / "keys.json"

# Create an initial empty keys file if it doesn't exist
if not KEYS_FILE.exists():
    with open(KEYS_FILE, 'w') as f:
        json.dump({}, f)

def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage"""
    # Use SHA-256 with a salt from the key itself
    salt = api_key[:8] if len(api_key) >= 8 else api_key
    hash_input = (api_key + salt).encode('utf-8')
    return base64.b64encode(hashlib.sha256(hash_input).digest()).decode('utf-8')

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
        # Load existing keys file
        with open(KEYS_FILE, 'r') as f:
            keys_data = json.load(f)
        
        # Check if we're changing anything
        if app_type in keys_data:
            if keys_data[app_type].get('api_url') == api_url and keys_data[app_type].get('api_key') == api_key:
                # No changes, nothing to do
                return True
        
        # Create a new entry or update existing one
        hashed_key = hash_api_key(api_key) if api_key else ""
        
        keys_data[app_type] = {
            'api_url': api_url,
            'api_key': api_key,
            'api_key_hash': hashed_key  # Store hashed version for verification later
        }
        
        # Save the file
        with open(KEYS_FILE, 'w') as f:
            json.dump(keys_data, f, indent=2)
        
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
        # Load keys file
        with open(KEYS_FILE, 'r') as f:
            keys_data = json.load(f)
        
        # Get keys for the app
        if app_type in keys_data:
            return keys_data[app_type].get('api_url', ''), keys_data[app_type].get('api_key', '')
        
        return '', ''
    except Exception as e:
        keys_logger.error(f"Error getting API keys: {e}")
        return '', ''

def verify_api_key(app_type: str, api_key: str) -> bool:
    """
    Verify if an API key matches the stored hash.
    
    Args:
        app_type: The type of app (sonarr, radarr, etc.)
        api_key: The API key to verify
    
    Returns:
        bool: True if the API key is correct
    """
    try:
        # Load keys file
        with open(KEYS_FILE, 'r') as f:
            keys_data = json.load(f)
        
        # Check if app type exists and has a key
        if app_type not in keys_data or not keys_data[app_type].get('api_key_hash'):
            return False
        
        # Get the stored hash
        stored_hash = keys_data[app_type].get('api_key_hash')
        
        # Hash the provided key
        hashed_key = hash_api_key(api_key)
        
        # Compare hashes
        return stored_hash == hashed_key
    except Exception as e:
        keys_logger.error(f"Error verifying API key: {e}")
        return False

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
        # Load keys file
        with open(KEYS_FILE, 'r') as f:
            keys_data = json.load(f)
        
        # Check each app
        for app in result.keys():
            if app in keys_data and keys_data[app].get('api_url') and keys_data[app].get('api_key'):
                result[app] = True
        
        return result
    except Exception as e:
        keys_logger.error(f"Error listing configured apps: {e}")
        return result