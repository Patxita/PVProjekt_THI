"""Unit tests for :class:`DataCleaner`."""

from datetime import datetime, timezone

from src.backend.data_cleaner import DataCleaner
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
        grid_power=grid_import,
    )


class TestDataCleaner:
    """Tests for single-reading validation and repair."""

    def test_valid_reading_passes_unchanged(self) -> None:
        """A plausible reading is returned identical."""
        reading = make_reading(3000, 1000, 0)
        assert DataCleaner().clean(reading) == reading

    def test_negative_values_clamped_to_zero(self) -> None:
        """Negative pv and consumption are clamped to 0; grid_power may be negative."""
        cleaned = DataCleaner().clean(make_reading(-50, -10, -5))
        assert cleaned.pv_power == 0.0
        assert cleaned.consumption_power == 0.0
        assert cleaned.grid_power == -5  # grid_power can be negative (feed-in)

    def test_implausible_value_rejected(self) -> None:
        """A value above max_power_w causes rejection (returns None)."""
        cleaner = DataCleaner(max_power_w=100_000)
        assert cleaner.clean(make_reading(999_999_999, 1000)) is None

    def test_nan_value_rejected(self) -> None:
        """A NaN value causes rejection (returns None)."""
        assert DataCleaner().clean(make_reading(float("nan"), 1000)) is None
