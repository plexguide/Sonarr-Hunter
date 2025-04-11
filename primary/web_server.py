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
import logging
from flask import Flask
from primary.config import API_URL
from primary import settings_manager, keys_manager
from primary.utils.logger import setup_logger
from primary.auth import (
    authenticate_request, user_exists, create_user, verify_user, create_session, 
    logout, SESSION_COOKIE_NAME, is_2fa_enabled, generate_2fa_secret, 
    verify_2fa_code, disable_2fa, change_username, change_password
)
# Import blueprints for apps and common routes
from primary.routes.common import common_bp
from primary.apps.sonarr import sonarr_bp
from primary.apps.radarr import radarr_bp
from primary.apps.lidarr import lidarr_bp
from primary.apps.readarr import readarr_bp

# Disable Flask default logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Create Flask app
app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)

# Log file location
LOG_FILE = "/tmp/huntarr-logs/huntarr.log"
LOG_DIR = pathlib.Path(LOG_FILE).parent
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("huntarr-web")
logging.basicConfig(level=logging.DEBUG)

# Register blueprints
app.register_blueprint(common_bp, url_prefix="/")
app.register_blueprint(sonarr_bp, url_prefix="/sonarr")
app.register_blueprint(radarr_bp, url_prefix="/radarr")
app.register_blueprint(lidarr_bp, url_prefix="/lidarr")
app.register_blueprint(readarr_bp, url_prefix="/readarr")

# Authentication middleware remains here for app-wide protection if needed
@app.before_request
def before_request():
    auth_result = authenticate_request()
    if auth_result:
        return auth_result

def get_main_process_pid():
    try:
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

if __name__ == "__main__":
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    from primary.utils.app_utils import get_ip_address
    ip_address = get_ip_address()
    with open(LOG_FILE, 'a') as f:
        f.write(f"{timestamp} - huntarr-web - INFO - Web server starting on port 9705\n")
        f.write(f"{timestamp} - huntarr-web - INFO - Web interface available at http://{ip_address}:9705\n")
    app.run(host='0.0.0.0', port=9705, debug=False, threaded=True)