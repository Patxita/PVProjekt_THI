"""Application entry point: the PV data collection loop.

Wires the pipeline together — data source → cleaner → storage — and runs it
forever, fetching one reading every ``INTERVAL_S`` seconds and persisting it
to the SQLite database.

Data source selection
---------------------
The collector uses :class:`~src.backend.client.ApiClient` when the
``PV_API_URL`` environment variable is set, and falls back to
:class:`~src.backend.mock_source.MockPVSource` otherwise. This allows
local development and CI to run without network access to the university
server.

Usage
-----
Run from the project root::

    python -m src.main

The database file is created automatically at ``data/pv.db`` if it does not
already exist.
"""

import logging
import os
import time
from pathlib import Path

from src.backend.client import ApiClient
from src.backend.data_cleaner import DataCleaner
from src.backend.data_storage import SQLiteStorage
from src.backend.mock_source import MockPVSource

INTERVAL_S: int = 5
"""Seconds between consecutive readings."""

DB_PATH: str = "data/pv.db"
"""Path to the SQLite database file (relative to the project root)."""

logger = logging.getLogger(__name__)


def _build_source():
    """Select and return the appropriate data source.

    Returns :class:`ApiClient` when ``PV_API_URL`` is set in the environment,
    and :class:`MockPVSource` as a fallback for local/offline use.

    Returns:
        ApiClient | MockPVSource: The configured data source.
    """
    if os.environ.get("PV_API_URL"):
        logger.info("PV_API_URL found — using live ApiClient")
        return ApiClient()
    logger.warning("PV_API_URL not set — using MockPVSource (no live data)")
    return MockPVSource()


def main() -> None:
    """Run the collection loop until interrupted.

    Fetches a reading every :data:`INTERVAL_S` seconds, cleans it, and stores
    it in the SQLite database at :data:`DB_PATH`. Transient per-reading errors
    are logged and skipped so the loop keeps running.

    Raises:
        KeyboardInterrupt: Gracefully caught; the loop exits cleanly.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    source = _build_source()
    cleaner = DataCleaner()
    store = SQLiteStorage(DB_PATH)
    logger.info("Collector started — writing readings to %s", DB_PATH)

    try:
        while True:
            try:
                reading = source.fetch()
                cleaned = cleaner.clean(reading)
                if cleaned is not None:
                    store.insert(cleaned)
                    logger.info("Stored reading: %s", cleaned)  # antes tenia .debug
                else:
                    logger.warning("Reading rejected by cleaner; skipped")
            except Exception:
                logger.exception("Failed to collect a reading; continuing")
            time.sleep(INTERVAL_S)
    except KeyboardInterrupt:
        logger.info("Collector stopped by user")
    finally:
        store.close()
        logger.info("Database connection closed")


if __name__ == "__main__":
    main()
