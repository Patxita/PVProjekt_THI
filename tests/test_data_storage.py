"""Unit tests for the SQLite storage module.

Tests cover schema creation, single-row insert, range queries, the
``latest`` helper, and an empty-database edge case. All tests use an
in-memory SQLite database so no files are created on disk.
"""

import pytest
from datetime import datetime, timezone, timedelta

from src.backend.data_storage import SQLiteStorage
from src.backend.models import PVReading


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def store():
    """Open an in-memory SQLiteStorage and close it after the test.

    Yields:
        SQLiteStorage: A fresh, empty storage backed by ``:memory:``.
    """
    s = SQLiteStorage(":memory:")
    yield s
    s.close()


def _reading(offset_s: int = 0) -> PVReading:
    """Create a test :class:`PVReading` at a fixed time plus an offset.

    Args:
        offset_s: Seconds to add to the base timestamp.

    Returns:
        PVReading: A deterministic reading for use in tests.
    """
    base = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
    return PVReading(
        timestamp=base + timedelta(seconds=offset_s),
        pv_power=1000.0 + offset_s,
        consumption_power=800.0,
        grid_import_power=0.0,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestInsertAndLatest:
    """Tests for single-row persistence and the ``latest`` query."""

    def test_latest_empty_db_returns_none(self, store: SQLiteStorage) -> None:
        """``latest`` on an empty database must return ``None``."""
        assert store.latest() is None

    def test_insert_one_row_and_retrieve_via_latest(self, store: SQLiteStorage) -> None:
        """Inserting one reading should make it retrievable via ``latest``."""
        r = _reading()
        store.insert(r)
        got = store.latest()
        assert got is not None
        assert got.pv_power == pytest.approx(r.pv_power)
        assert got.consumption_power == pytest.approx(r.consumption_power)
        assert got.grid_import_power == pytest.approx(r.grid_import_power)

    def test_latest_returns_most_recent(self, store: SQLiteStorage) -> None:
        """``latest`` must return the row with the highest timestamp."""
        for offset in [0, 5, 10]:
            store.insert(_reading(offset))
        latest = store.latest()
        assert latest.pv_power == pytest.approx(1010.0)  # offset=10

    def test_timestamp_roundtrip(self, store: SQLiteStorage) -> None:
        """The timestamp stored in ISO format must survive a roundtrip."""
        r = _reading()
        store.insert(r)
        got = store.latest()
        assert got.timestamp == r.timestamp


class TestQueryRange:
    """Tests for the time-range query helper."""

    def test_query_range_returns_matching_rows(self, store: SQLiteStorage) -> None:
        """``query_range`` must return only readings within the window."""
        for offset in [0, 5, 10, 15, 20]:
            store.insert(_reading(offset))

        start = datetime(2024, 6, 15, 10, 0, 5, tzinfo=timezone.utc)
        end = datetime(2024, 6, 15, 10, 0, 15, tzinfo=timezone.utc)
        rows = store.query_range(start, end)

        # offset=5 and offset=10 fall in [start, end); offset=15 is excluded
        assert len(rows) == 2
        assert rows[0].pv_power == pytest.approx(1005.0)
        assert rows[1].pv_power == pytest.approx(1010.0)

    def test_query_range_empty_result(self, store: SQLiteStorage) -> None:
        """``query_range`` on a window with no data must return an empty list."""
        store.insert(_reading(0))
        far_future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        far_future_end = datetime(2099, 1, 2, tzinfo=timezone.utc)
        assert store.query_range(far_future, far_future_end) == []

    def test_query_range_ordered_oldest_first(self, store: SQLiteStorage) -> None:
        """Rows returned by ``query_range`` must be in ascending timestamp order."""
        for offset in [20, 0, 10, 5, 15]:
            store.insert(_reading(offset))

        start = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 6, 15, 10, 1, 0, tzinfo=timezone.utc)
        rows = store.query_range(start, end)

        timestamps = [r.timestamp for r in rows]
        assert timestamps == sorted(timestamps)

    def test_query_range_start_is_inclusive(self, store: SQLiteStorage) -> None:
        """The start boundary must be inclusive."""
        r = _reading(0)
        store.insert(r)
        end = r.timestamp + timedelta(seconds=1)
        rows = store.query_range(r.timestamp, end)
        assert len(rows) == 1

    def test_query_range_end_is_exclusive(self, store: SQLiteStorage) -> None:
        """The end boundary must be exclusive."""
        r = _reading(0)
        store.insert(r)
        rows = store.query_range(r.timestamp, r.timestamp)

        assert rows == []