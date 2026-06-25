"""Application configuration loaded from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)

API_URL: str | None = os.getenv("PV_API_URL")
API_KEY: str | None = os.getenv("PV_API_KEY")


def require_config() -> tuple[str, str]:
    """Return (API_URL, API_KEY) or raise ValueError if either is missing.

    Call this inside ApiClient.fetch(), not at import time, so that
    tests can import the module without a .env file being present.

    Returns:
        tuple[str, str]: The configured API URL and API key.

    Raises:
        ValueError: If PV_API_URL or PV_API_KEY is not set.
    """
    if not API_URL:
        raise ValueError("PV_API_URL not configured")
    if not API_KEY:
        raise ValueError("PV_API_KEY not configured")
    return API_URL, API_KEY
