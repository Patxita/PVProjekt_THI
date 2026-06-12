"""Unit tests for :class:`MetricsCalculator`."""

from datetime import datetime, timezone

import pytest

from src.backend.metrics import MetricsCalculator
from src.backend.models import PVReading


def make_reading(pv: float, consumption: float, grid_import: float = 0.0) -> PVReading:
    """Build a PVReading with a fixed timestamp for tests.

    Args:
        pv: PV generation power in W.
        consumption: Consumption power in W.
        grid_import: Grid import power in W.

    Returns:
        PVReading: A reading carrying the given power values.
    """
    return PVReading(
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        pv_power=pv,
        consumption_power=consumption,
        grid_import_power=grid_import,
    )


class TestMetricsCalculator:
    """Tests for the derived-KPI calculations."""

    def test_self_consumption_limited_by_load(self) -> None:
        """When PV exceeds the load, self-consumption equals the load."""
        assert MetricsCalculator().self_consumption_w(make_reading(3000, 1000)) == 1000

    def test_self_consumption_limited_by_pv(self) -> None:
        """When the load exceeds PV, self-consumption equals PV output."""
        assert MetricsCalculator().self_consumption_w(make_reading(800, 2000)) == 800

    def test_grid_export_when_surplus(self) -> None:
        """Surplus PV beyond the load is exported."""
        assert MetricsCalculator().grid_export_w(make_reading(3000, 1000)) == 2000

    def test_grid_export_zero_without_surplus(self) -> None:
        """No export when the load exceeds PV output."""
        assert MetricsCalculator().grid_export_w(make_reading(500, 1000)) == 0.0

    def test_autarky_full_coverage(self) -> None:
        """Autarky is 1.0 when PV fully covers the load."""
        assert MetricsCalculator().autarky_ratio(make_reading(3000, 1000)) == 1.0

    def test_autarky_partial_coverage(self) -> None:
        """Autarky equals the covered fraction when PV is below the load."""
        assert MetricsCalculator().autarky_ratio(make_reading(500, 1000)) == 0.5

    def test_autarky_zero_consumption(self) -> None:
        """Autarky is 1.0 when there is no consumption to cover."""
        assert MetricsCalculator().autarky_ratio(make_reading(500, 0)) == 1.0

    def test_energy_increment_conversion(self) -> None:
        """3600 W sustained for 1 s equals exactly 1 Wh."""
        assert MetricsCalculator().energy_increment_wh(3600, 1) == pytest.approx(1.0)
