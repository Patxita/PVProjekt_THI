"""Unit tests for :class:`ApiClient`."""

from datetime import datetime

from src.backend.client import ApiClient


class TestApiClient:
    """Tests for parsing API payloads into PVReading objects."""

    def test_parse_payload_sums_generation_sources(self) -> None:
        """Multiple generation sources are summed into one pv_power value."""
        payload = {
            "collected_at": "2026-06-20T18:05:42.939039+02:00",
            "data": [
                {
                    "type": "consumption",
                    "value": 268484.25,
                },
                {
                    "type": "generation",
                    "value": 139447.546875,
                },
                {
                    "type": "generation",
                    "value": 2732.294921875,
                },
                {
                    "type": "generation",
                    "value": 30276.15625,
                },
            ],
            "age_seconds": 0.264598,
        }

        client = ApiClient(url="http://dummy")

        reading = client._parse(payload)

        expected_generation = (
            139447.546875
            + 2732.294921875
            + 30276.15625
        )

        assert reading.pv_power == expected_generation
        assert reading.consumption_power == 268484.25

    def test_parse_derives_grid_import(self) -> None:
        """Grid import is derived from consumption minus PV generation."""
        payload = {
            "collected_at": "2026-06-20T18:05:42.939039+02:00",
            "data": [
                {
                    "type": "consumption",
                    "value": 1000,
                },
                {
                    "type": "generation",
                    "value": 400,
                },
            ],
            "age_seconds": 0,
        }

        client = ApiClient(url="http://dummy")

        reading = client._parse(payload)

        assert reading.grid_import_power == 600

    def test_parse_converts_timestamp(self) -> None:
        """The API timestamp is converted into a datetime object."""
        payload = {
            "collected_at": "2026-06-20T18:05:42.939039+02:00",
            "data": [],
            "age_seconds": 0,
        }

        client = ApiClient(url="http://dummy")

        reading = client._parse(payload)

        assert reading.timestamp == datetime.fromisoformat(
            "2026-06-20T18:05:42.939039+02:00"
        )