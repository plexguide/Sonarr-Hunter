from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_logger():
    from .logger import logger
    return logger


class Settings(BaseSettings):
    API_KEY: str = "your-api-key"
    API_URL: str = "your-ip-address:7878"
    MAX_MISSING: str = "1"
    MAX_UPGRADES: str = "5"
    SLEEP_DURATION: str = "900"
    STATE_RESET_INTERVAL_HOURS: str = "168"
    RANDOM_SELECTION: bool = True
    MONITORED_ONLY: bool = True
    SEARCH_TYPE: str = "both"
    DEBUG_MODE: bool = False
    PROCESSED_UPGRADE_FILE: Path = Path("/app/data/processed_missing_ids.txt")
    PROCESSED_MISSING_FILE: Path = Path("/app/data/processed_upgrade_ids.txt")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True)


def get_settings() -> Settings:

    logger = get_logger()
    logger.debug('Getting settings from .env')


settings = Settings()
