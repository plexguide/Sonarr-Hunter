#!/usr/bin/env python3
"""
Web server for Huntarr
Provides a web interface to view logs in real-time, manage settings, and includes authentication
"""

import os
import time
import datetime
import pathlib
import socket
import json
import signal
import sys
import qrcode
import pyotp
import base64
import io
import requests
from flask import Flask, render_template, Response, stream_with_context, request, jsonify, send_from_directory, redirect, session, url_for
import logging
from primary.config import API_URL
from primary import settings_manager
from primary import keys_manager
from primary.utils.logger import setup_logger
from primary.auth import (
    authenticate_request, user_exists, create_user, verify_user, create_session, 
    logout, SESSION_COOKIE_NAME, is_2fa_enabled, generate_2fa_secret, 
    verify_2fa_code, disable_2fa, change_username, change_password
)

# Disable Flask default logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Create Flask app
app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

# Log file location
LOG_FILE = "/tmp/huntarr-logs/huntarr.log"
LOG_DIR = pathlib.Path("/tmp/huntarr-logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Authentication middleware
@app.before_request
def before_request():
    auth_result = authenticate_request()
    if auth_result:
        return auth_result

# Get the PID of the main process
def get_main_process_pid():
    try:
        # Try to find the main.py process
        for proc in os.listdir('/proc'):
            if not proc.isdigit():
                continue
            try:
                with open(f'/proc/{proc}/cmdline', 'r') as f:
                    cmdline = f.read().replace('\0', ' ')
                    if 'python' in cmdline and 'primary/main.py' in cmdline:
                        return int(proc)
            except (IOError, ProcessLookupError):
                continue
        return None
    except:
        return None

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/settings')
def settings_page():
    """Render the settings page"""
    return render_template('index.html')

@app.route('/user')
def user_page():
    """Render the user settings page"""
    return render_template('user.html')

@app.route('/setup', methods=['GET'])
def setup_page():
    """Render the setup page for first-time users"""
    if user_exists():
        return redirect('/')
    # Log the access to setup page
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, 'a') as f:
        f.write(f"{timestamp} - huntarr-web - INFO - Accessed setup page - no user exists yet\n")
    return render_template('setup.html')

@app.route('/reset-password')
def reset_password_page():
    """Render the password reset instructions page"""
    return render_template('reset-password.html')

@app.route('/login', methods=['GET'])
def login_page():
    """Render the login page"""
    if not user_exists():
        return redirect('/setup')
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def api_login_form():
    """Handle form-based login (for 2FA implementation)"""
    username = request.form.get('username')
    password = request.form.get('password')
    otp_code = request.form.get('otp_code')
    
    auth_success, needs_2fa = verify_user(username, password, otp_code)
    
    if auth_success:
        # Create a session for the authenticated user
        session_id = create_session(username)
        session[SESSION_COOKIE_NAME] = session_id
        return redirect('/')
    elif needs_2fa:
        # Show 2FA input form
        return render_template('login.html', username=username, password=password, needs_2fa=True)
    else:
        # Invalid credentials
        return render_template('login.html', error="Invalid username or password")

@app.route('/logout')
def logout_page():
    """Log out and redirect to login page"""
    logout()
    return redirect('/login')

@app.route('/api/setup', methods=['POST'])
def api_setup():
    """Create the initial user"""
    if user_exists():
        return jsonify({"success": False, "message": "User already exists"}), 400
        
    data = request.json
    username = data.get('username')
    password = data.get('password')
    confirm_password = data.get('confirm_password')
    
    if not username or not password:
        return jsonify({"success": False, "message": "Username and password required"}), 400
        
    if password != confirm_password:
        return jsonify({"success": False, "message": "Passwords do not match"}), 400
        
    # Log the creation attempt
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, 'a') as f:
        f.write(f"{timestamp} - huntarr-web - INFO - Attempting to create first user: {username}\n")
    
    if create_user(username, password):
        # Log success
        with open(LOG_FILE, 'a') as f:
            f.write(f"{timestamp} - huntarr-web - INFO - Successfully created first user\n")
        
        # Create a session for the new user
        session_id = create_session(username)
        session[SESSION_COOKIE_NAME] = session_id
        return jsonify({"success": True})
    else:
        # Log failure
        with open(LOG_FILE, 'a') as f:
            f.write(f"{timestamp} - huntarr-web - ERROR - Failed to create user - check permissions\n")
        return jsonify({"success": False, "message": "Failed to create user - check directory permissions"}), 500

@app.route('/api/test-connection', methods=['POST'])
def test_connection():
    """Test connection to an Arr application"""
    data = request.json
    app_type = data.get('app')
    api_url = data.get('api_url')
    api_key = data.get('api_key')
    
    if not app_type:
        return jsonify({"success": False, "message": "Missing app type parameter"}), 400
    
    # If API URL and key aren't provided, get them from storage
    if not api_url or not api_key:
        stored_url, stored_key = keys_manager.get_api_keys(app_type)
        api_url = api_url or stored_url
        api_key = api_key or stored_key
    
    if not api_url or not api_key:
        return jsonify({"success": False, "message": "Missing API URL or API key"}), 400
    
    try:
        # Test connection by making a simple request to the API
        url = f"{api_url}/api/v3/system/status"
        headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Log the successful connection test
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, 'a') as f:
            f.write(f"{timestamp} - huntarr-web - INFO - Connection test successful for {app_type}: {api_url}\n")
        
        return jsonify({"success": True})
    except Exception as e:
        # Log the failed connection test
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, 'a') as f:
            f.write(f"{timestamp} - huntarr-web - ERROR - Connection test failed for {app_type}: {api_url} - {str(e)}\n")
        
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/login', methods=['POST'])
def api_login():
    """Authenticate a user"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    otp_code = data.get('otp_code')
    
    auth_success, needs_2fa = verify_user(username, password, otp_code)
    
    if auth_success:
        # Create a session for the authenticated user
        session_id = create_session(username)
        session[SESSION_COOKIE_NAME] = session_id
        return jsonify({"success": True})
    elif needs_2fa:
        # Need 2FA code
        return jsonify({"success": False, "needs_2fa": True})
    else:
        return jsonify({"success": False, "message": "Invalid credentials"}), 401

@app.route('/api/user/2fa-status')
def api_2fa_status():
    """Check if 2FA is enabled for the current user"""
    return jsonify({"enabled": is_2fa_enabled()})

@app.route('/api/user/generate-2fa')
def api_generate_2fa():
    """Generate a new 2FA secret and QR code"""
    try:
        secret, qr_code_url = generate_2fa_secret()
        return jsonify({
            "success": True,
            "secret": secret,
            "qr_code_url": qr_code_url
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Failed to generate 2FA: {str(e)}"
        }), 500

@app.route('/api/user/verify-2fa', methods=['POST'])
def api_verify_2fa():
    """Verify a 2FA code and enable 2FA if valid"""
    data = request.json
    code = data.get('code')
    
    if not code:
        return jsonify({"success": False, "message": "Verification code is required"}), 400
    
    if verify_2fa_code(code):
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "message": "Invalid verification code"}), 400

@app.route('/api/user/disable-2fa', methods=['POST'])
def api_disable_2fa():
    """Disable 2FA for the current user"""
    data = request.json
    password = data.get('password')
    
    if not password:
        return jsonify({"success": False, "message": "Password is required"}), 400
    
    if disable_2fa(password):
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "message": "Invalid password"}), 400

@app.route('/api/user/change-username', methods=['POST'])
def api_change_username():
    """Change the username for the current user"""
    data = request.json
    current_username = data.get('current_username')
    new_username = data.get('new_username')
    password = data.get('password')
    
    if not current_username or not new_username or not password:
        return jsonify({"success": False, "message": "All fields are required"}), 400
    
    if change_username(current_username, new_username, password):
        # Force logout
        logout()
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "message": "Invalid username or password"}), 400

@app.route('/api/user/change-password', methods=['POST'])
def api_change_password():
    """Change the password for the current user"""
    data = request.json
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not current_password or not new_password:
        return jsonify({"success": False, "message": "All fields are required"}), 400
    
    if change_password(current_password, new_password):
        # Force logout
        logout()
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "message": "Invalid current password"}), 400

@app.route('/static/<path:path>')
def send_static(path):
    """Serve static files"""
    return send_from_directory('../static', path)

@app.route('/logs')
def stream_logs():
    """Stream logs to the client"""
    app = request.args.get('app', 'sonarr')  # Default to 'sonarr' if not specified
    
    def generate():
        # First get all existing logs
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r') as f:
                # Read the last 100 lines of the log file
                lines = f.readlines()[-100:]
                for line in lines:
                    # Filter logs by app type
                    if app == 'sonarr' or app in line.lower():
                        yield f"data: {line}\n\n"
        
        # Then stream new logs as they appear
        with open(LOG_FILE, 'r') as f:
            # Move to the end of the file
            f.seek(0, 2)
            while True:
                line = f.readline()
                if line:
                    # Filter logs by app type
                    if app == 'sonarr' or app in line.lower():
                        yield f"data: {line}\n\n"
                else:
                    time.sleep(0.1)

    return Response(stream_with_context(generate()), 
                   mimetype='text/event-stream')

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get all settings"""
    # Get settings from settings_manager
    settings = settings_manager.get_all_settings()
    
    # Add API keys from keys_manager for each app
    apps = ['sonarr', 'radarr', 'lidarr', 'readarr']
    for app in apps:
        api_url, api_key = keys_manager.get_api_keys(app)
        if app == settings.get('app_type', 'sonarr'):
            # For current app, set at root level
            settings['api_url'] = api_url
            settings['api_key'] = api_key
    
    return jsonify(settings)

@app.route('/api/app-settings', methods=['GET'])
def get_app_settings():
    """Get settings for a specific app"""
    app = request.args.get('app')
    if not app:
        return jsonify({"success": False, "message": "App parameter required"}), 400
    
    # Get API keys for the requested app
    api_url, api_key = keys_manager.get_api_keys(app)
    
    return jsonify({
        "success": True,
        "app": app,
        "api_url": api_url,
        "api_key": api_key
    })

@app.route('/api/configured-apps', methods=['GET'])
def get_configured_apps():
    """Get which apps are configured"""
    return jsonify(keys_manager.list_configured_apps())

@app.route('/api/settings', methods=['POST'])
def update_settings():
    """Update settings and restart the main process to apply them immediately"""
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400
        
        # Get current settings to compare
        old_settings = settings_manager.get_all_settings()
        old_huntarr = old_settings.get("huntarr", {})
        old_advanced = old_settings.get("advanced", {})
        old_ui = old_settings.get("ui", {})
        
        # Get current API URL and key
        app_type = data.get('app_type', 'sonarr')
        old_api_url, old_api_key = keys_manager.get_api_keys(app_type)
        
        # Find changes
        huntarr_changes = {}
        advanced_changes = {}
        ui_changes = {}
        api_changes = {}
        
        # Track if any real changes were made
        changes_made = False
        
        # Check API URL and key changes
        new_api_url = data.get('api_url', '')
        new_api_key = data.get('api_key', '')
        
        if old_api_url != new_api_url:
            api_changes['api_url'] = {"old": old_api_url, "new": new_api_url}
            changes_made = True
        
        if old_api_key != new_api_key:
            api_changes['api_key'] = {"old": "****", "new": "****"}  # Don't log actual keys
            changes_made = True
        
        # Save API keys if changed
        if api_changes:
            keys_manager.save_api_keys(app_type, new_api_url, new_api_key)
        
        # Update huntarr settings and track changes
        if "huntarr" in data:
            for key, value in data["huntarr"].items():
                old_value = old_huntarr.get(key)
                if old_value != value:
                    huntarr_changes[key] = {"old": old_value, "new": value}
                    changes_made = True
                settings_manager.update_setting("huntarr", key, value)
        
        # Update UI settings and track changes
        if "ui" in data:
            for key, value in data["ui"].items():
                old_value = old_ui.get(key)
                if old_value != value:
                    ui_changes[key] = {"old": old_value, "new": value}
                    changes_made = True
                settings_manager.update_setting("ui", key, value)
        
        # Update advanced settings and track changes
        if "advanced" in data:
            for key, value in data["advanced"].items():
                old_value = old_advanced.get(key)
                if old_value != value:
                    advanced_changes[key] = {"old": old_value, "new": value}
                    changes_made = True
                settings_manager.update_setting("advanced", key, value)
                
                # Special handling for debug_mode setting
                if key == "debug_mode" and old_value != value:
                    # Reconfigure the logger with new debug mode setting
                    setup_logger(value)
        
        # Log changes if any were made
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if changes_made:
            with open(LOG_FILE, 'a') as f:
                f.write(f"{timestamp} - huntarr-web - INFO - Settings updated by user\n")
                
                # Log API changes
                for key, change in api_changes.items():
                    if key == 'api_key':
                        f.write(f"{timestamp} - huntarr-web - INFO - Changed API key for {app_type}\n")
                    else:
                        f.write(f"{timestamp} - huntarr-web - INFO - Changed {key} for {app_type} from {change['old']} to {change['new']}\n")
                
                # Log huntarr changes
                for key, change in huntarr_changes.items():
                    f.write(f"{timestamp} - huntarr-web - INFO - Changed {key} from {change['old']} to {change['new']}\n")
                
                # Log advanced changes
                for key, change in advanced_changes.items():
                    f.write(f"{timestamp} - huntarr-web - INFO - Changed advanced.{key} from {change['old']} to {change['new']}\n")
                
                # Log UI changes
                for key, change in ui_changes.items():
                    f.write(f"{timestamp} - huntarr-web - INFO - Changed UI.{key} from {change['old']} to {change['new']}\n")
                
                f.write(f"{timestamp} - huntarr-web - INFO - Settings saved successfully\n")
                f.write(f"{timestamp} - huntarr-web - INFO - Restarting current cycle to apply new settings immediately\n")
            
            # Try to signal the main process to restart the cycle
            main_pid = get_main_process_pid()
            if main_pid:
                try:
                    # Send a SIGUSR1 signal which we'll handle in main.py to restart the cycle
                    os.kill(main_pid, signal.SIGUSR1)
                    return jsonify({"success": True, "message": "Settings saved and cycle restarted", "changes_made": True})
                except:
                    # If signaling fails, just return success for the settings save
                    return jsonify({"success": True, "message": "Settings saved, but cycle not restarted", "changes_made": True})
            else:
                return jsonify({"success": True, "message": "Settings saved, but main process not found", "changes_made": True})
        else:
            # No changes were made
            return jsonify({"success": True, "message": "No changes detected", "changes_made": False})
            
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/settings/reset', methods=['POST'])
def reset_settings():
    """Reset settings to defaults"""
    try:
        # Get current settings to compare
        old_settings = settings_manager.get_all_settings()
        
        # Reset settings
        settings_manager.save_settings(settings_manager.DEFAULT_SETTINGS)
        
        # Log the reset
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, 'a') as f:
            f.write(f"{timestamp} - huntarr-web - INFO - Settings reset to defaults by user\n")
            f.write(f"{timestamp} - huntarr-web - INFO - Restarting current cycle to apply new settings immediately\n")
        
        # Try to signal the main process to restart the cycle
        main_pid = get_main_process_pid()
        if main_pid:
            try:
                # Send a SIGUSR1 signal which we'll handle in main.py to restart the cycle
                os.kill(main_pid, signal.SIGUSR1)
                return jsonify({"success": True, "message": "Settings reset and cycle restarted"})
            except:
                # If signaling fails, just return success for the settings reset
                return jsonify({"success": True, "message": "Settings reset, but cycle not restarted"})
        else:
            return jsonify({"success": True, "message": "Settings reset, but main process not found"})
        
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/settings/theme', methods=['GET'])
def get_theme():
    """Get the current theme setting"""
    dark_mode = settings_manager.get_setting("ui", "dark_mode", True)
    return jsonify({"dark_mode": dark_mode})

@app.route('/api/settings/theme', methods=['POST'])
def update_theme():
    """Update the theme setting"""
    try:
        data = request.json
        old_value = settings_manager.get_setting("ui", "dark_mode", True)
        if "dark_mode" in data and old_value != data["dark_mode"]:
            settings_manager.update_setting("ui", "dark_mode", data["dark_mode"])
            
            # Log the theme change - simplified to remove "from X" text
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(LOG_FILE, 'a') as f:
                new_mode = 'Dark' if data['dark_mode'] else 'Light'
                f.write(f"{timestamp} - huntarr-web - INFO - Changed theme to {new_mode} Mode\n")
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

def get_ip_address():
    """Get the host's IP address from API_URL for display"""
    try:
        from urllib.parse import urlparse
        
        # Extract the hostname/IP from the API_URL
        parsed_url = urlparse(API_URL)
        hostname = parsed_url.netloc
        
        # Remove port if present
        if ':' in hostname:
            hostname = hostname.split(':')[0]
            
        return hostname
    except Exception as e:
        # Fallback to the current method if there's an issue
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            return ip
        except:
            return "localhost"

if __name__ == "__main__":
    # Create a basic log entry at startup
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ip_address = get_ip_address()
    
    with open(LOG_FILE, 'a') as f:
        f.write(f"{timestamp} - huntarr-web - INFO - Web server starting on port 8988\n")
        f.write(f"{timestamp} - huntarr-web - INFO - Web interface available at http://{ip_address}:8988\n")
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=9705, debug=False, threaded=True)