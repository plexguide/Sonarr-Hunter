from flask import Blueprint, request, jsonify
import datetime, os, signal, pathlib, requests
from primary import keys_manager

sonarr_bp = Blueprint('sonarr', __name__)

LOG_FILE = "/tmp/huntarr-logs/huntarr.log"

def get_main_process_pid():
    # ...existing logic...
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

@sonarr_bp.route('/test-connection', methods=['POST'])
def test_connection():
    """Test connection to a Sonarr API instance"""
    data = request.json
    api_url = data.get('api_url')
    api_key = data.get('api_key')
    if not api_url or not api_key:
        return jsonify({"success": False, "message": "Missing API URL or API key"}), 400

    # For Sonarr, always use api/v3
    api_base = "api/v3"
    url = f"{api_url}/{api_base}/system/status"
    headers = {
        "X-Api-Key": api_key,
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        keys_manager.save_api_keys("sonarr", api_url, api_key)
        
        # Removed cycle restart functionality:
        # main_pid = get_main_process_pid()
        # if main_pid:
        #     os.kill(main_pid, signal.SIGUSR1)
        #     timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        #     with open(LOG_FILE, 'a') as f:
        #         f.write(f"{timestamp} - sonarr - INFO - Triggered cycle restart to apply new connection settings\n")
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, 'a') as f:
            f.write(f"{timestamp} - sonarr - INFO - Connection test successful: {api_url}\n")
        return jsonify({"success": True})
    except Exception as e:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, 'a') as f:
            f.write(f"{timestamp} - sonarr - ERROR - Connection test failed: {api_url} - {str(e)}\n")
        return jsonify({"success": False, "message": str(e)}), 500
