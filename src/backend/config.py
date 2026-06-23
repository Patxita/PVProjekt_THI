"""Application configuration loaded from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(__file__).resolve().parents[2] / '.env'
load_dotenv()

API_URL = os.getenv("PV_API_URL")
API_KEY = os.getenv("PV_API_KEY")

if not API_URL:
    raise ValueError("PV_API_URL not configured")

if not API_KEY:
    raise ValueError("PV_API_KEY not configured")

