import logging


def get_settings():
    from .config import settings
    return settings


settings = get_settings()
log_path = '/app/log/app.log'

# Setup logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG_MODE else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("huntarr-sonarr")
