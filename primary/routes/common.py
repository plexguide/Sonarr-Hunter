from flask import Blueprint, render_template, request, redirect, session, jsonify, send_from_directory, Response, stream_with_context
import datetime, os
from primary.auth import (
    authenticate_request, user_exists, create_user, verify_user, create_session, logout, 
    SESSION_COOKIE_NAME, is_2fa_enabled, generate_2fa_secret, verify_2fa_code, disable_2fa, 
    change_username, change_password
)
from primary import settings_manager

common_bp = Blueprint('common', __name__)
LOG_FILE = "/tmp/huntarr-logs/huntarr.log"

@common_bp.before_request
def before_common():
    auth_result = authenticate_request()
    if auth_result:
        return auth_result

@common_bp.route('/')
def index():
    return render_template('index.html')

@common_bp.route('/settings')
def settings_page():
    return render_template('index.html')

@common_bp.route('/user')
def user_page():
    return render_template('user.html')

@common_bp.route('/setup', methods=['GET'])
def setup_page():
    if user_exists():
        return redirect('/')
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, 'a') as f:
        f.write(f"{timestamp} - huntarr-web - INFO - Accessed setup page - no user exists yet\n")
    return render_template('setup.html')

@common_bp.route('/login', methods=['GET'])
def login_page():
    if not user_exists():
        return redirect('/setup')
    return render_template('login.html')

@common_bp.route('/login', methods=['POST'])
def api_login_form():
    username = request.form.get('username')
    password = request.form.get('password')
    otp_code = request.form.get('otp_code')
    auth_success, needs_2fa = verify_user(username, password, otp_code)
    if auth_success:
        session_id = create_session(username)
        session[SESSION_COOKIE_NAME] = session_id
        return redirect('/')
    elif needs_2fa:
        return render_template('login.html', username=username, password=password, needs_2fa=True)
    else:
        return render_template('login.html', error="Invalid username or password")

@common_bp.route('/logout')
def logout_page():
    logout()
    return redirect('/login')

@common_bp.route('/api/setup', methods=['POST'])
def api_setup():
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
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, 'a') as f:
        f.write(f"{timestamp} - huntarr-web - INFO - Attempting to create first user: {username}\n")
    if create_user(username, password):
        with open(LOG_FILE, 'a') as f:
            f.write(f"{timestamp} - huntarr-web - INFO - Successfully created first user\n")
        session_id = create_session(username)
        session[SESSION_COOKIE_NAME] = session_id
        return jsonify({"success": True})
    else:
        with open(LOG_FILE, 'a') as f:
            f.write(f"{timestamp} - huntarr-web - ERROR - Failed to create user - check permissions\n")
        return jsonify({"success": False, "message": "Failed to create user - check directory permissions"}), 500

@common_bp.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    otp_code = data.get('otp_code')
    auth_success, needs_2fa = verify_user(username, password, otp_code)
    if auth_success:
        session_id = create_session(username)
        session[SESSION_COOKIE_NAME] = session_id
        return jsonify({"success": True})
    elif needs_2fa:
        return jsonify({"success": False, "needs_2fa": True})
    else:
        return jsonify({"success": False, "message": "Invalid credentials"}), 401

@common_bp.route('/api/user/2fa-status')
def api_2fa_status():
    return jsonify({"enabled": is_2fa_enabled()})

@common_bp.route('/api/user/generate-2fa')
def api_generate_2fa():
    try:
        secret, qr_code_url = generate_2fa_secret()
        return jsonify({"success": True, "secret": secret, "qr_code_url": qr_code_url})
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to generate 2FA: {str(e)}"}), 500

@common_bp.route('/api/user/verify-2fa', methods=['POST'])
def api_verify_2fa():
    data = request.json
    code = data.get('code')
    if not code:
        return jsonify({"success": False, "message": "Verification code is required"}), 400
    if verify_2fa_code(code):
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "message": "Invalid verification code"}), 400

@common_bp.route('/api/user/disable-2fa', methods=['POST'])
def api_disable_2fa():
    data = request.json
    password = data.get('password')
    if not password:
        return jsonify({"success": False, "message": "Password is required"}), 400
    if disable_2fa(password):
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "message": "Invalid password"}), 400

@common_bp.route('/api/user/change-username', methods=['POST'])
def api_change_username():
    data = request.json
    current_username = data.get('current_username')
    new_username = data.get('new_username')
    password = data.get('password')
    if not current_username or not new_username or not password:
        return jsonify({"success": False, "message": "All fields are required"}), 400
    if change_username(current_username, new_username, password):
        logout()
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "message": "Invalid username or password"}), 400

@common_bp.route('/api/user/change-password', methods=['POST'])
def api_change_password():
    data = request.json
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    if not current_password or not new_password:
        return jsonify({"success": False, "message": "All fields are required"}), 400
    if change_password(current_password, new_password):
        logout()
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "message": "Invalid current password"}), 400

@common_bp.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('../static', path)

@common_bp.route('/logs')
def stream_logs():
    app_type = request.args.get('app', 'sonarr')
    def generate():
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r') as f:
                lines = f.readlines()[-100:]
                for line in lines:
                    if app_type == 'sonarr' or app_type in line.lower():
                        yield f"data: {line}\n\n"
        with open(LOG_FILE, 'r') as f:
            f.seek(0, 2)
            while True:
                line = f.readline()
                if line:
                    if app_type == 'sonarr' or app_type in line.lower():
                        yield f"data: {line}\n\n"
                else:
                    import time
                    time.sleep(0.1)
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@common_bp.route('/api/settings', methods=['GET'])
def get_settings():
    settings = settings_manager.get_all_settings()
    apps = ['sonarr', 'radarr', 'lidarr', 'readarr']
    for app_name in apps:
        api_url, api_key = __import__("primary.keys_manager", fromlist=[""]).get_api_keys(app_name)
        if app_name == settings.get('app_type', 'sonarr'):
            settings['api_url'] = api_url
            settings['api_key'] = api_key
    return jsonify(settings)

@common_bp.route('/api/app-settings', methods=['GET'])
def get_app_settings():
    app_name = request.args.get('app')
    if not app_name:
        return jsonify({"success": False, "message": "App parameter required"}), 400
    api_url, api_key = __import__("primary.keys_manager", fromlist=[""]).get_api_keys(app_name)
    return jsonify({"success": True, "app": app_name, "api_url": api_url, "api_key": api_key})

@common_bp.route('/api/configured-apps', methods=['GET'])
def get_configured_apps():
    return jsonify(__import__("primary.keys_manager", fromlist=[""]).list_configured_apps())

@common_bp.route('/api/settings', methods=['POST'])
def update_settings():
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "message": "No data provided"}), 400
        old_settings = settings_manager.get_all_settings()
        old_huntarr = old_settings.get("huntarr", {})
        old_advanced = old_settings.get("advanced", {})
        old_ui = old_settings.get("ui", {})
        huntarr_changes = {}
        advanced_changes = {}
        ui_changes = {}
        changes_made = False
        if "huntarr" in data:
            for key, value in data["huntarr"].items():
                old_value = old_huntarr.get(key)
                if old_value != value:
                    huntarr_changes[key] = {"old": old_value, "new": value}
                    changes_made = True
                settings_manager.update_setting("huntarr", key, value)
        if "ui" in data:
            for key, value in data["ui"].items():
                old_value = old_ui.get(key)
                if old_value != value:
                    ui_changes[key] = {"old": old_value, "new": value}
                    changes_made = True
                settings_manager.update_setting("ui", key, value)
        if "advanced" in data:
            for key, value in data["advanced"].items():
                old_value = old_advanced.get(key)
                if old_value != value:
                    advanced_changes[key] = {"old": old_value, "new": value}
                    changes_made = True
                settings_manager.update_setting("advanced", key, value)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if changes_made:
            with open(LOG_FILE, 'a') as f:
                f.write(f"{timestamp} - huntarr-web - INFO - Settings updated by user\n")
                for key, change in huntarr_changes.items():
                    f.write(f"{timestamp} - huntarr-web - INFO - Changed {key} from {change['old']} to {change['new']}\n")
                for key, change in advanced_changes.items():
                    f.write(f"{timestamp} - huntarr-web - INFO - Changed advanced.{key} from {change['old']} to {change['new']}\n")
                for key, change in ui_changes.items():
                    f.write(f"{timestamp} - huntarr-web - INFO - Changed UI.{key} from {change['old']} to {change['new']}\n")
            return jsonify({"success": True, "message": "Settings saved successfully", "changes_made": True})
        else:
            return jsonify({"success": True, "message": "No changes detected", "changes_made": False})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@common_bp.route('/api/settings/reset', methods=['POST'])
def reset_settings():
    try:
        settings_manager.save_settings(settings_manager.DEFAULT_SETTINGS)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, 'a') as f:
            f.write(f"{timestamp} - huntarr-web - INFO - Settings reset to defaults by user\n")
        return jsonify({"success": True, "message": "Settings reset to defaults successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@common_bp.route('/api/settings/theme', methods=['GET'])
def get_theme():
    dark_mode = settings_manager.get_setting("ui", "dark_mode", True)
    return jsonify({"dark_mode": dark_mode})

@common_bp.route('/api/settings/theme', methods=['POST'])
def update_theme():
    try:
        data = request.json
        old_value = settings_manager.get_setting("ui", "dark_mode", True)
        if "dark_mode" in data and old_value != data["dark_mode"]:
            settings_manager.update_setting("ui", "dark_mode", data["dark_mode"])
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_mode = 'Dark' if data['dark_mode'] else 'Light'
            with open(LOG_FILE, 'a') as f:
                f.write(f"{timestamp} - huntarr-web - INFO - Changed theme to {new_mode} Mode\n")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
