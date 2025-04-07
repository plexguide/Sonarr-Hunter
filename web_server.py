#!/usr/bin/env python3
"""
Web server for Huntarr-Sonarr
Provides a web interface to view logs in real-time
"""

import os
import time
import datetime
import pathlib
import socket
from flask import Flask, render_template, Response, stream_with_context
import logging
from config import ENABLE_WEB_UI

# Check if web UI is enabled
if not ENABLE_WEB_UI:
    print("Web UI is disabled. Exiting web server.")
    exit(0)

# Disable Flask default logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Create Flask app
app = Flask(__name__)

# Log file location
LOG_FILE = "/tmp/huntarr-logs/huntarr.log"
LOG_DIR = pathlib.Path("/tmp/huntarr-logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/logs')
def stream_logs():
    """Stream logs to the client"""
    def generate():
        # First get all existing logs
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r') as f:
                # Read the last 100 lines of the log file
                lines = f.readlines()[-100:]
                for line in lines:
                    yield f"data: {line}\n\n"
        
        # Then stream new logs as they appear
        with open(LOG_FILE, 'r') as f:
            # Move to the end of the file
            f.seek(0, 2)
            while True:
                line = f.readline()
                if line:
                    yield f"data: {line}\n\n"
                else:
                    time.sleep(0.1)

    return Response(stream_with_context(generate()), 
                   mimetype='text/event-stream')

def get_ip_address():
    """Get the host's IP address or hostname for display"""
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
    app.run(host='0.0.0.0', port=8988, debug=False, threaded=True)