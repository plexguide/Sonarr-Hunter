#!/usr/bin/env python3
"""
Settings manager for Huntarr
Handles loading, saving, and providing settings from a JSON file
Supports default configurations for different Arr applications
"""

import os
import json
import pathlib
import logging
from typing import Dict, Any, Optional
from primary import keys_manager

# Create a simple logger for settings_manager
logging.basicConfig(level=logging.INFO)
settings_logger = logging.getLogger("settings_manager")

# Settings directory setup
SETTINGS_DIR = pathlib.Path("/config/settings")
SETTINGS_DIR.mkdir(parents=True, exist_ok=True)

SETTINGS_FILE = SETTINGS_DIR / "huntarr.json"

# Default settings
DEFAULT_SETTINGS = {
    "ui": {
        "dark_mode": True
    },
    "app_type": "sonarr",  # Default app type
    "huntarr": {
        # These will be loaded from default_configs.json based on app_type
    },
    "advanced": {
        # These will be loaded from default_configs.json based on app_type
    }
}

# Load default configurations from file
def load_default_configs():
    """Load default configurations for all supported apps"""
    try:
        default_configs_path = pathlib.Path("/app/default_configs.json")
        if default_configs_path.exists():
            with open(default_configs_path, 'r') as f:
                return json.load(f)
        else:
            settings_logger.warning(f"Default configs file not found at {default_configs_path}")
            return {}
    except Exception as e:
        settings_logger.error(f"Error loading default configs: {e}")
        return {}

# Initialize default configs
DEFAULT_CONFIGS = load_default_configs()

def get_app_defaults(app_type):
    """Get default settings for a specific app type"""
    if app_type in DEFAULT_CONFIGS:
        return DEFAULT_CONFIGS[app_type]
    else:
        settings_logger.warning(f"No default config found for app_type: {app_type}, falling back to sonarr")
        return DEFAULT_CONFIGS.get("sonarr", {})

def get_env_settings():
    """Get settings from environment variables"""
    env_settings = {
        "app_type": os.environ.get("APP_TYPE", "sonarr").lower()
    }
    
    # Optional environment variables
    if "API_TIMEOUT" in os.environ:
        try:
            env_settings["api_timeout"] = int(os.environ.get("API_TIMEOUT"))
        except ValueError:
            pass
            
    if "MONITORED_ONLY" in os.environ:
        env_settings["monitored_only"] = os.environ.get("MONITORED_ONLY", "true").lower() == "true"
        
    # All other environment variables that might override defaults
    for key, value in os.environ.items():
        if key.startswith(("HUNT_", "SLEEP_", "STATE_", "SKIP_", "RANDOM_", "COMMAND_", "MINIMUM_", "DEBUG_")):
            # Convert to lowercase with underscores
            settings_key = key.lower()
            
            # Try to convert to appropriate type
            if value.lower() in ("true", "false"):
                env_settings[settings_key] = value.lower() == "true"
            else:
                try:
                    env_settings[settings_key] = int(value)
                except ValueError:
                    env_settings[settings_key] = value
    
    return env_settings

def load_settings() -> Dict[str, Any]:
    """
    Load settings with the following priority:
    1. User-defined settings in the settings file
    2. Environment variables
    3. Default settings for the selected app_type
    """
    try:
        # Start with default settings structure
        settings = dict(DEFAULT_SETTINGS)
        
        # Get environment variables
        env_settings = get_env_settings()
        
        # If we have an app_type, update the settings
        app_type = env_settings.get("app_type", "sonarr")
        settings["app_type"] = app_type
        
        # Get default settings for this app type
        app_defaults = get_app_defaults(app_type)
        
        # Categorize settings
        huntarr_settings = {}
        advanced_settings = {}
        
        # Distribute app defaults into categories
        for key, value in app_defaults.items():
            # Simple categorization based on key name
            if key in ("api_timeout", "debug_mode", "command_wait_delay", 
                      "command_wait_attempts", "minimum_download_queue_size",
                      "random_missing", "random_upgrades"):
                advanced_settings[key] = value
            else:
                huntarr_settings[key] = value
        
        # Apply defaults to settings
        settings["huntarr"].update(huntarr_settings)
        settings["advanced"].update(advanced_settings)
        
        # Apply environment settings, keeping track of whether they're huntarr or advanced
        for key, value in env_settings.items():
            if key in ("app_type"):
                settings[key] = value
            elif key in ("api_timeout", "debug_mode", "command_wait_delay", 
                        "command_wait_attempts", "minimum_download_queue_size",
                        "random_missing", "random_upgrades"):
                settings["advanced"][key] = value
            else:
                settings["huntarr"][key] = value
        
        # Finally, load user settings from file (highest priority)
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, 'r') as f:
                user_settings = json.load(f)
                # Deep merge user settings
                _deep_update(settings, user_settings)
                settings_logger.info("Settings loaded from configuration file")
        else:
            settings_logger.info("No settings file found, creating with default values")
            save_settings(settings)
        
        return settings
    except Exception as e:
        settings_logger.error(f"Error loading settings: {e}")
        settings_logger.info("Using default settings due to error")
        return DEFAULT_SETTINGS

def _deep_update(d, u):
    """Recursively update a dictionary without overwriting entire nested dicts"""
    for k, v in u.items():
        if isinstance(v, dict) and k in d and isinstance(d[k], dict):
            _deep_update(d[k], v)
        else:
            d[k] = v

def save_settings(settings: Dict[str, Any]) -> bool:
    """Save settings to the settings file."""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
        settings_logger.info("Settings saved successfully")
        return True
    except Exception as e:
        settings_logger.error(f"Error saving settings: {e}")
        return False

def update_setting(category: str, key: str, value: Any) -> bool:
    """Update a specific setting value."""
    try:
        settings = load_settings()
        
        # Ensure category exists
        if category not in settings:
            settings[category] = {}
            
        # Update the value
        settings[category][key] = value
        
        # Save the updated settings
        return save_settings(settings)
    except Exception as e:
        settings_logger.error(f"Error updating setting {category}.{key}: {e}")
        return False

def get_setting(category: str, key: str, default: Any = None) -> Any:
    """Get a specific setting value."""
    try:
        settings = load_settings()
        return settings.get(category, {}).get(key, default)
    except Exception as e:
        settings_logger.error(f"Error getting setting {category}.{key}: {e}")
        return default

def get_all_settings() -> Dict[str, Any]:
    """Get all settings."""
    return load_settings()

def get_app_type() -> str:
    """Get the current app type"""
    settings = load_settings()
    return settings.get("app_type", "sonarr")

def get_api_key() -> str:
    """Get the API key"""
    app_type = get_app_type()
    _, api_key = keys_manager.get_api_keys(app_type)
    return api_key

def get_api_url() -> str:
    """Get the API URL"""
    app_type = get_app_type()
    api_url, _ = keys_manager.get_api_keys(app_type)
    return api_url

# Initialize settings file if it doesn't exist
if not SETTINGS_FILE.exists():
    save_settings(load_settings())