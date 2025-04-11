import socket
from urllib.parse import urlparse
from primary.config import API_URL

def get_ip_address():
    try:
        parsed_url = urlparse(API_URL)
        hostname = parsed_url.netloc
        if ':' in hostname:
            hostname = hostname.split(':')[0]
        return hostname
    except Exception:
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            return ip
        except:
            return "localhost"

def write_log(log_file, message):
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, 'a') as f:
        f.write(f"{timestamp} - {message}\n")
