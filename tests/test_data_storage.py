"""Integration tests for :class:`PrometheusExporter`.

These exercise the full record-to-metric path using an isolated registry,
so they do not interfere with the global Prometheus registry.
"""

from datetime import datetime, timezone

import pytest
from prometheus_client import CollectorRegistry

from src.backend.data_storage import PrometheusExporter
from src.backend.models import PVReading


def make_reading(pv: float, consumption: float, grid_import: float) -> PVReading:
    """Build a PVReading with a fixed timestamp for tests."""
    return PVReading(
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        pv_power=pv,
        consumption_power=consumption,
        grid_import_power=grid_import,
    )


class TestPrometheusExporter:
    """Tests that readings are reflected correctly in the metrics."""

    def test_gauges_reflect_reading(self) -> None:
        """Recording a reading sets the instantaneous gauges."""
        registry = CollectorRegistry()
        exporter = PrometheusExporter(registry=registry)
        exporter.record(make_reading(3000, 1000, 0), interval_s=5)
        assert registry.get_sample_value("pv_power_watts") == 3000
        assert registry.get_sample_value("consumption_power_watts") == 1000
        assert registry.get_sample_value("autarky_ratio") == 1.0

    def test_energy_counter_accumulates(self) -> None:
        """Recording twice accumulates the cumulative energy counter."""
        registry = CollectorRegistry()
        exporter = PrometheusExporter(registry=registry)
        # 3600 W for 1 s = 1 Wh per call -> two calls = 2 Wh.
        exporter.record(make_reading(3600, 0, 0), interval_s=1)
        exporter.record(make_reading(3600, 0, 0), interval_s=1)
        assert registry.get_sample_value("pv_energy_wh_total") == pytest.approx(2.0)

    def test_grid_export_gauge_reflects_surplus(self) -> None:
        """Surplus PV beyond the load is recorded as grid export."""
        registry = CollectorRegistry()
        exporter = PrometheusExporter(registry=registry)
        exporter.record(make_reading(5000, 1000, 0), interval_s=5)
        assert registry.get_sample_value("grid_export_power_watts") == 4000
