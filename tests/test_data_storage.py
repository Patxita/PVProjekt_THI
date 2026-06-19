"""Unit tests for :class:`SQLiteStorage`.

Each test runs against a fresh database file created in a pytest-managed
temporary directory, so tests are isolated and leave nothing behind.
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.backend.data_storage import SQLiteStorage
from src.backend.models import PVReading

BASE_TIME = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def make_reading(
    pv: float,
    consumption: float,
    grid_import: float = 0.0,
    timestamp: datetime = BASE_TIME,
) -> PVReading:
    """Build a PVReading for tests.

    Args:
        pv: PV generation power in W.
        consumption: Consumption power in W.
        grid_import: Grid import power in W.
        timestamp: Moment of the reading; defaults to ``BASE_TIME``.

    Returns:
        PVReading: A reading carrying the given values.
    """
    return PVReading(
        timestamp=timestamp,
        pv_power=pv,
        consumption_power=consumption,
        grid_import_power=grid_import,
    )


@pytest.fixture
def store(tmp_path) -> SQLiteStorage:
    """Provide a SQLiteStorage backed by a fresh temporary database file.

    Args:
        tmp_path: Pytest fixture giving a unique temporary directory.

    Returns:
        SQLiteStorage: An empty store ready for use.
    """
    storage = SQLiteStorage(str(tmp_path / "test.db"))
    yield storage
    storage.close()


class TestSQLiteStorage:
    """Tests for the SQLite-backed reading store."""

    def test_latest_on_empty_store_returns_none(self, store) -> None:
        """A store with no rows yet returns None from latest()."""
        assert store.latest() is None

    def test_insert_then_latest_returns_reading(self, store) -> None:
        """After inserting one reading, latest() returns an equal reading."""
        reading = make_reading(1200, 800, 0)
        store.insert(reading)
        assert store.latest() == reading

    def test_roundtrip_preserves_all_fields(self, store) -> None:
        """Values survive a write/read cycle unchanged (incl. timestamp)."""
        reading = make_reading(3333.5, 1111.25, 50.75)
        store.insert(reading)
        result = store.latest()
        assert result.timestamp == reading.timestamp
        assert result.pv_power == reading.pv_power
        assert result.consumption_power == reading.consumption_power
        assert result.grid_import_power == reading.grid_import_power

    def test_latest_returns_most_recent(self, store) -> None:
        """latest() returns the newest reading, not the most recently inserted."""
        older = make_reading(100, 100, timestamp=BASE_TIME)
        newer = make_reading(200, 200, timestamp=BASE_TIME + timedelta(minutes=5))
        # Insert out of chronological order on purpose.
        store.insert(newer)
        store.insert(older)
        assert store.latest() == newer

    def test_query_range_returns_matching_oldest_first(self, store) -> None:
        """query_range returns readings in the window, ordered oldest first."""
        r0 = make_reading(1, 1, timestamp=BASE_TIME)
        r1 = make_reading(2, 2, timestamp=BASE_TIME + timedelta(minutes=5))
        r2 = make_reading(3, 3, timestamp=BASE_TIME + timedelta(minutes=10))
        for reading in (r2, r0, r1):  # insert unordered
            store.insert(reading)

        result = store.query_range(BASE_TIME, BASE_TIME + timedelta(minutes=15))
        assert result == [r0, r1, r2]

    def test_query_range_is_half_open(self, store) -> None:
        """The lower bound is inclusive and the upper bound is exclusive."""
        start = make_reading(1, 1, timestamp=BASE_TIME)
        end = make_reading(2, 2, timestamp=BASE_TIME + timedelta(minutes=10))
        store.insert(start)
        store.insert(end)

        # Window [BASE_TIME, BASE_TIME+10min): includes start, excludes end.
        result = store.query_range(BASE_TIME, BASE_TIME + timedelta(minutes=10))
        assert result == [start]

    def test_query_range_no_matches_returns_empty(self, store) -> None:
        """A window with no readings returns an empty list."""
        store.insert(make_reading(1, 1, timestamp=BASE_TIME))
        result = store.query_range(
            BASE_TIME + timedelta(hours=1), BASE_TIME + timedelta(hours=2)
        )
        assert result == []

    def test_data_persists_across_connections(self, tmp_path) -> None:
        """Committed rows are readable from a new store on the same file."""
        db_path = str(tmp_path / "persist.db")
        first = SQLiteStorage(db_path)
        first.insert(make_reading(500, 400, 0))
        first.close()

        second = SQLiteStorage(db_path)
        assert second.latest() == make_reading(500, 400, 0)
        second.close()