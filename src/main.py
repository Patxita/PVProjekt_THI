"""Application entry point: the PV data collection loop.

Wires the pipeline together — data source -> cleaner -> storage — and runs it
forever, fetching a reading every ``INTERVAL_S`` seconds and persisting it to
SQLite. While the real PV API is unavailable, :class:`MockPVSource` is used;
swapping in :class:`ApiClient` is a one-line change because both implement
:class:`PVDataSource`.
"""

import logging
import time
from pathlib import Path

from src.backend.data_cleaner import DataCleaner
from src.backend.data_storage import SQLiteStorage
from src.backend.mock_source import MockPVSource

INTERVAL_S = 5
DB_PATH = "data/pv.db"

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the collection loop until interrupted.

    Fetches a reading every ``INTERVAL_S`` seconds, cleans it, and stores it
    in the SQLite database at ``DB_PATH``. Transient per-reading errors are
    logged and skipped so the loop keeps running.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    source = MockPVSource()  # swap for ApiClient() once the API is available
    cleaner = DataCleaner()
    store = SQLiteStorage(DB_PATH)
    logger.info("Collector started; writing readings to %s", DB_PATH)

    try:
        while True:
            try:
                reading = source.fetch()
                cleaned = cleaner.clean(reading)
                if cleaned is not None:
                    store.insert(cleaned)
                else:
                    logger.warning("Reading rejected by cleaner; skipped")
            except Exception:
                logger.exception("Failed to collect a reading; continuing")
            time.sleep(INTERVAL_S)
    except KeyboardInterrupt:
        logger.info("Collector stopped by user")
    finally:
        store.close()


if __name__ == "__main__":
    main()