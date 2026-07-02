"""Integration test: full pipeline fetch -> clean -> store -> aggregate.

Verifies that all four backend modules work correctly together as a chain.
Uses a synthetic payload (no real API needed) to simulate what ApiClient
would return from the THI endpoint.
"""

import pytest
from datetime import datetime, timezone

from src.backend.client import ApiClient
from src.backend.data_cleaner import DataCleaner
from src.backend.data_storage import SQLiteStorage
from src.backend.metrics import MetricsCalculator


FAKE_PAYLOAD = {
    "collected_at": "2026-06-30T08:00:00.000000+00:00",
    "age_seconds": 3.5,
    "data": [
        {"type": "generation", "value": 20000.0},
        {"type": "generation", "value": 5000.0},
        {"type": "consumption", "value": 18000.0},
    ],
}


class TestPipelineIntegration:
    """End-to-end test: parse -> clean -> store -> query -> aggregate."""

    @pytest.fixture()
    def store(self):
        """In-memory SQLiteStorage, closed after each test.

        Yields:
            SQLiteStorage: A fresh, empty in-memory storage instance.
        """
        s = SQLiteStorage(":memory:")
        yield s
        s.close()

    def test_full_pipeline(self, store: SQLiteStorage) -> None:
        """A parsed reading survives the full pipeline with correct values.

        Parses a synthetic API payload, cleans it, stores it, queries
        it back, and verifies that MetricsCalculator produces the expected
        KPIs from the stored data.

        Args:
            store: In-memory SQLiteStorage fixture.
        """
        # Step 1: parse (what ApiClient._parse() does)
        client = ApiClient(url="http://dummy")
        reading = client._parse(FAKE_PAYLOAD)

        assert reading.pv_power == pytest.approx(25000.0)
        assert reading.consumption_power == pytest.approx(18000.0)
        assert reading.grid_power == pytest.approx(-7000.0)  # net export
        assert reading.age_seconds == pytest.approx(3.5)

        # Step 2: clean
        cleaner = DataCleaner()
        cleaned = cleaner.clean(reading)

        assert cleaned is not None
        assert cleaned.pv_power == pytest.approx(25000.0)
        assert cleaned.age_seconds == pytest.approx(3.5)  # must survive cleaner

        # Step 3: store
        store.insert(cleaned)

        # Step 4: query back
        start = datetime(2026, 6, 30, 7, 59, 0, tzinfo=timezone.utc)
        end = datetime(2026, 6, 30, 9, 0, 0, tzinfo=timezone.utc)
        rows = store.query_range(start, end)

        assert len(rows) == 1
        assert rows[0].pv_power == pytest.approx(25000.0)
        assert rows[0].grid_power == pytest.approx(-7000.0)
        assert rows[0].age_seconds == pytest.approx(3.5)

        # Step 5: aggregate with MetricsCalculator
        calc = MetricsCalculator()
        summary = calc.period_summary(rows, interval_s=5.0)

        assert summary["generation_wh"] == pytest.approx(25000.0 * 5 / 3600)
        assert summary["consumption_wh"] == pytest.approx(18000.0 * 5 / 3600)
        assert summary["autarky"] == pytest.approx(1.0)  # PV fully covers consumption

    def test_pipeline_rejects_implausible_reading(self, store: SQLiteStorage) -> None:
        """A reading with an implausible value is rejected by the cleaner
        and never reaches the database.

        Args:
            store: In-memory SQLiteStorage fixture.
        """
        bad_payload = {
            "collected_at": "2026-06-30T08:00:05.000000+00:00",
            "age_seconds": 0.0,
            "data": [
                {"type": "generation", "value": 999_999_999.0},  # sensor error
                {"type": "consumption", "value": 5000.0},
            ],
        }
        client = ApiClient(url="http://dummy")
        reading = client._parse(bad_payload)

        cleaner = DataCleaner()
        cleaned = cleaner.clean(reading)

        assert cleaned is None  # rejected by cleaner

        start = datetime(2026, 6, 30, 7, 59, 0, tzinfo=timezone.utc)
        end = datetime(2026, 6, 30, 9, 0, 0, tzinfo=timezone.utc)
        assert store.query_range(start, end) == []  # nothing stored