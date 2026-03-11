"""File operations tool — sandboxed read/write to outputs directory.

All operations are constrained to `settings.outputs_dir` and log through the
shared app logger so that any failures show up consistently.
"""
import os
import time

from ...config import settings
from ...logger import get_logger

logger = get_logger(__name__)


async def read_file(filepath: str) -> tuple[str, int]:
    """
    Read a file from the outputs directory.
    Returns (content, duration_ms).
    """
    start = time.time()
    try:
        safe_path = _sanitize_path(filepath)
        if not os.path.exists(safe_path):
            logger.warning("Attempted to read missing file: %s", safe_path)
            return f"File not found: {filepath}", 0

        with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        if len(content) > 10000:
            content = content[:10000] + "\n\n[... file truncated ...]"

        duration_ms = int((time.time() - start) * 1000)
        return content, duration_ms
    except Exception as e:
        logger.error("File read failed for %s: %s", filepath, str(e))
        return f"File read failed: {str(e)}", 0


async def write_file(filepath: str, content: str) -> tuple[str, int]:
    """
    Write content to a file in the outputs directory.
    Returns (status_message, duration_ms).
    """
    start = time.time()
    try:
        safe_path = _sanitize_path(filepath)
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)

        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(content)

        duration_ms = int((time.time() - start) * 1000)
        return f"Successfully wrote {len(content)} chars to {filepath}", duration_ms
    except Exception as e:
        logger.error("File write failed for %s: %s", filepath, str(e))
        return f"File write failed: {str(e)}", 0


def _sanitize_path(filepath: str) -> str:
    """Ensure path stays within outputs directory — prevent path traversal."""
    outputs_dir = os.path.abspath(settings.outputs_dir)
    os.makedirs(outputs_dir, exist_ok=True)

    # Strip leading slashes and ../ sequences
    clean = filepath.lstrip("/\\")
    clean = clean.replace("..", "")

    full_path = os.path.abspath(os.path.join(outputs_dir, clean))

    # Verify it's still under outputs_dir
    if not full_path.startswith(outputs_dir):
        raise ValueError(f"Path escape attempt blocked: {filepath}")

    return full_path
