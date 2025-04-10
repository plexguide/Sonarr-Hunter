#!/usr/bin/env python3
"""
Authentication module for Huntarr
Handles user creation, verification, and session management
Including two-factor authentication
"""

import os
import json
import hashlib
import secrets
import time
import pathlib
import base64
import io
import qrcode
import pyotp
from typing import Dict, Any, Optional, Tuple
from flask import request, redirect, url_for, session

# User directory setup
USER_DIR = pathlib.Path("/config/user")
USER_DIR.mkdir(parents=True, exist_ok=True)
USER_FILE = USER_DIR / "credentials.json"

# Session settings
SESSION_EXPIRY = 60 * 60 * 24 * 7  # 1 week in seconds
SESSION_COOKIE_NAME = "huntarr_session"

# Store active sessions
active_sessions = {}

def hash_password(password: str) -> str:
    """Hash a password for storage"""
    # Use SHA-256 with a salt
    salt = secrets.token_hex(16)
    pw_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{pw_hash}"

def verify_password(stored_password: str, provided_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        salt, pw_hash = stored_password.split(':', 1)
        verify_hash = hashlib.sha256((provided_password + salt).encode()).hexdigest()
        return secrets.compare_digest(verify_hash, pw_hash)
    except:
        return False

def hash_username(username: str) -> str:
    """Create a normalized hash of the username"""
    # Convert to lowercase and hash
    return hashlib.sha256(username.lower().encode()).hexdigest()

def user_exists() -> bool:
    """Check if a user has been created"""
    return USER_FILE.exists()

def create_user(username: str, password: str) -> bool:
    """Create a new user"""
    if not username or not password:
        return False
        
    # Hash the username and password
    username_hash = hash_username(username)
    password_hash = hash_password(password)
    
    # Store the credentials
    user_data = {
        "username": username_hash,
        "password": password_hash,
        "created_at": time.time(),
        "2fa_enabled": False,
        "2fa_secret": None
    }
    
    try:
        with open(USER_FILE, 'w') as f:
            json.dump(user_data, f)
        return True
    except Exception as e:
        print(f"Error creating user: {e}")
        return False

def verify_user(username: str, password: str, otp_code: str = None) -> Tuple[bool, bool]:
    """
    Verify user credentials
    
    Returns:
        Tuple[bool, bool]: (auth_success, needs_2fa)
    """
    if not user_exists():
        return False, False
        
    try:
        with open(USER_FILE, 'r') as f:
            user_data = json.load(f)
            
        # Hash the provided username
        username_hash = hash_username(username)
        
        # Compare username and verify password
        if user_data.get("username") == username_hash:
            if verify_password(user_data.get("password", ""), password):
                # Check if 2FA is enabled
                if user_data.get("2fa_enabled", False):
                    # If 2FA code was provided, verify it
                    if otp_code:
                        totp = pyotp.TOTP(user_data.get("2fa_secret"))
                        if totp.verify(otp_code):
                            return True, False
                        else:
                            return False, True
                    else:
                        # No OTP code provided but 2FA is enabled
                        return False, True
                else:
                    # 2FA not enabled, password is correct
                    return True, False
    except Exception as e:
        print(f"Error verifying user: {e}")
    
    return False, False

def create_session(username: str) -> str:
    """Create a new session for an authenticated user"""
    session_id = secrets.token_hex(32)
    username_hash = hash_username(username)
    
    # Store session data
    active_sessions[session_id] = {
        "username": username_hash,
        "created_at": time.time(),
        "expires_at": time.time() + SESSION_EXPIRY
    }
    
    return session_id

def verify_session(session_id: str) -> bool:
    """Verify if a session is valid"""
    if not session_id or session_id not in active_sessions:
        return False
        
    session_data = active_sessions[session_id]
    
    # Check if session has expired
    if session_data.get("expires_at", 0) < time.time():
        # Clean up expired session
        del active_sessions[session_id]
        return False
        
    # Extend session expiry
    active_sessions[session_id]["expires_at"] = time.time() + SESSION_EXPIRY
    return True

def get_username_from_session(session_id: str) -> Optional[str]:
    """Get the username hash from a session"""
    if not session_id or session_id not in active_sessions:
        return None
    
    return active_sessions[session_id].get("username")

def authenticate_request():
    """Flask route decorator to check if user is authenticated"""
    # If no user exists, redirect to setup
    if not user_exists():
        if request.path != "/setup" and not request.path.startswith(("/static/", "/api/setup")):
            return redirect("/setup")
        return None
    
    # Skip authentication for static files and the login page
    if request.path.startswith(("/static/", "/login", "/api/login")) or request.path == "/favicon.ico":
        return None
    
    # Check for valid session
    session_id = session.get(SESSION_COOKIE_NAME)
    if session_id and verify_session(session_id):
        return None
    
    # No valid session, redirect to login
    if request.path != "/login" and not request.path.startswith("/api/"):
        return redirect("/login")
    
    # For API calls, return 401 Unauthorized
    if request.path.startswith("/api/"):
        return {"error": "Unauthorized"}, 401
    
    return None

def logout():
    """Log out the current user by invalidating their session"""
    session_id = session.get(SESSION_COOKIE_NAME)
    if session_id and session_id in active_sessions:
        del active_sessions[session_id]
    
    # Clear the session cookie
    session.pop(SESSION_COOKIE_NAME, None)

def get_user_data() -> Dict:
    """Get the user data from the credentials file"""
    if not user_exists():
        return {}
    
    try:
        with open(USER_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading user data: {e}")
        return {}

def save_user_data(user_data: Dict) -> bool:
    """Save the user data to the credentials file"""
    try:
        with open(USER_FILE, 'w') as f:
            json.dump(user_data, f)
        return True
    except Exception as e:
        print(f"Error saving user data: {e}")
        return False

def is_2fa_enabled() -> bool:
    """Check if 2FA is enabled for the current user"""
    user_data = get_user_data()
    return user_data.get("2fa_enabled", False)

def generate_2fa_secret() -> Tuple[str, str]:
    """
    Generate a new 2FA secret and QR code
    
    Returns:
        Tuple[str, str]: (secret, qr_code_url)
    """
    # Generate a random secret
    secret = pyotp.random_base32()
    
    # Create a TOTP object
    totp = pyotp.TOTP(secret)
    
    # Get the provisioning URI
    uri = totp.provisioning_uri(name="Huntarr", issuer_name="Huntarr")
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64 string
    buffered = io.BytesIO()
    img.save(buffered)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    # Store the secret temporarily
    user_data = get_user_data()
    user_data["temp_2fa_secret"] = secret
    save_user_data(user_data)
    
    return secret, f"data:image/png;base64,{img_str}"

def verify_2fa_code(code: str) -> bool:
    """Verify a 2FA code against the temporary secret"""
    user_data = get_user_data()
    temp_secret = user_data.get("temp_2fa_secret")
    
    if not temp_secret:
        return False
    
    totp = pyotp.TOTP(temp_secret)
    if totp.verify(code):
        # Enable 2FA
        user_data["2fa_enabled"] = True
        user_data["2fa_secret"] = temp_secret
        user_data.pop("temp_2fa_secret", None)
        save_user_data(user_data)
        return True
    
    return False

def disable_2fa(password: str) -> bool:
    """Disable 2FA for the current user"""
    user_data = get_user_data()
    
    # Verify password
    if verify_password(user_data.get("password", ""), password):
        user_data["2fa_enabled"] = False
        user_data["2fa_secret"] = None
        save_user_data(user_data)
        return True
    
    return False

def change_username(current_username: str, new_username: str, password: str) -> bool:
    """Change the username for the current user"""
    user_data = get_user_data()
    
    # Verify current username and password
    current_username_hash = hash_username(current_username)
    if user_data.get("username") != current_username_hash:
        return False
    
    if not verify_password(user_data.get("password", ""), password):
        return False
    
    # Update username
    user_data["username"] = hash_username(new_username)
    return save_user_data(user_data)

def change_password(current_password: str, new_password: str) -> bool:
    """Change the password for the current user"""
    user_data = get_user_data()
    
    # Verify current password
    if not verify_password(user_data.get("password", ""), current_password):
        return False
    
    # Update password
    user_data["password"] = hash_password(new_password)
    return save_user_data(user_data)