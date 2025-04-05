from pathlib import Path
from .logger import logger
from typing import List


def truncate_processed_list(file_path: Path, max_lines: int = 500) -> None:
    """Truncate the processed list to prevent unbounded growth."""
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()

        if len(lines) > 10000:
            logger.info(f"Processed list is large ({len(lines)} lines). Truncating to last {max_lines} entries.")
            with open(file_path, 'w') as file:
                file.writelines(lines[-max_lines:])
    except Exception as e:
        logger.error(f"Error truncating {file_path}: {e}")


def load_processed_ids(file_path: Path) -> List[int]:
    """Load processed show/episode IDs from a file."""
    try:
        with open(file_path, 'r') as f:
            return [int(line.strip()) for line in f if line.strip().isdigit()]
    except Exception as e:
        logger.error(f"Error reading processed IDs from {file_path}: {e}")
        return []


def save_processed_id(file_path: Path, obj_id: int) -> None:
    """Save a processed show/episode ID to a file."""
    try:
        with open(file_path, 'a') as f:
            f.write(f"{obj_id}\n")
    except Exception as e:
        logger.error(f"Error writing to {file_path}: {e}")
