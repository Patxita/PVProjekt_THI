"""Validation and repair of raw PV readings.

The collector emits one :class:`PVReading` roughly every 5 seconds, so
cleaning operates on a single reading at a time (streaming). A reading that
cannot be sensibly repaired is rejected (``clean`` returns ``None``) so that
corrupt or implausible data never reaches the metrics store.
"""

from src.backend.models import PVReading


class DataCleaner:
    """Validates and repairs individual PV readings.

    Attributes:
        max_power_w (float): Upper plausibility bound for any power value, in
            W. Readings above this are treated as sensor errors and rejected.
    """

    def __init__(self, max_power_w: float = 1_000_000.0) -> None:
        """Initialise the cleaner.

        Args:
            max_power_w: Maximum plausible power for any single field, in W.
        """
        self.max_power_w = max_power_w

    def clean(self, reading: PVReading) -> PVReading | None:
        """Validate and repair a single reading.

        Negative power values (physically impossible for these fields) are
        clamped to 0. Readings with missing values or implausibly large
        values are rejected.

        Args:
            reading: The raw reading to clean.

        Returns:
            PVReading | None: A repaired reading, or ``None`` if the reading
            is too corrupt to use.
        """
        if self._has_missing_values(reading) or self._is_implausible(reading):
            return None
        return self._clamp_negatives(reading)

    def _has_missing_values(self, reading: PVReading) -> bool:
        """Check whether any power field is ``None`` or NaN.

        Args:
            reading: The reading to inspect.

        Returns:
            bool: ``True`` if any required value is missing.
        """
        values = (
            reading.pv_power,
            reading.consumption_power,
            reading.grid_power,
        )
        return any(v is None or v != v for v in values)  # v != v is True for NaN

    def _is_implausible(self, reading: PVReading) -> bool:
        """Check whether any power value exceeds the plausibility bound.

        Args:
            reading: The reading to inspect.

        Returns:
            bool: ``True`` if any value is above ``max_power_w``.
        """
        return any(
            v > self.max_power_w
            for v in (
                reading.pv_power,
                reading.consumption_power,
                abs(reading.grid_power),
            )
        )

    def _clamp_negatives(self, reading: PVReading) -> PVReading:
        """Clamp negative pv and consumption to 0; grid_power may stay negative.

        Args:
            reading: The reading to repair.

        Returns:
            PVReading: A new reading with pv_power and consumption_power >= 0.
        """
        return PVReading(
            timestamp=reading.timestamp,
            pv_power=max(0.0, reading.pv_power),
            consumption_power=max(0.0, reading.consumption_power),
            grid_power=reading.grid_power,
        )