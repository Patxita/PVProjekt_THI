"""Mock PV data source for use while the real PV API is unavailable.

Generates synthetic :class:`PVReading` values that follow a realistic
clear-day solar curve: zero generation at night, a smooth ramp after
sunrise, a midday peak, and a symmetric fall-off toward sunset, with small
random noise applied. Implements the :class:`PVDataSource` interface so it
is interchangeable with the real API client.
"""

import math
import random
from datetime import datetime, timezone

from src.backend.models import PVReading


class MockPVSource:
    """Produces synthetic PV readings following a daily solar curve.

    Attributes:
        peak_power_w (float): Panel output at solar noon on a clear day, in W.
        base_load_w (float): Building's average baseline consumption, in W.
        sunrise_hour (float): Hour of day (0-24) when generation begins.
        sunset_hour (float): Hour of day (0-24) when generation ends.
        noise (float): Fractional random noise per value (0.05 = +/-5 %).
    """

    def __init__(
        self,
        peak_power_w: float = 30000.0,
        base_load_w: float = 5000.0,
        sunrise_hour: float = 6.0,
        sunset_hour: float = 20.0,
        noise: float = 0.05,
    ) -> None:
        """Initialise the mock source with curve and load parameters.

        Args:
            peak_power_w: Clear-sky panel output at solar noon, in W.
            base_load_w: Average building consumption, in W.
            sunrise_hour: Hour (0-24) at which generation starts.
            sunset_hour: Hour (0-24) at which generation stops.
            noise: Fractional noise applied to each value, e.g. 0.05.
        """
        self.peak_power_w = peak_power_w
        self.base_load_w = base_load_w
        self.sunrise_hour = sunrise_hour
        self.sunset_hour = sunset_hour
        self.noise = noise

    def _solar_factor(self, when: datetime) -> float:
        """Return the fraction of peak output expected at a given time.

        Uses a raised-cosine that is 0 at sunrise and sunset and 1.0 at the
        midpoint between them; outside daylight hours it returns 0.

        Args:
            when: Timestamp to evaluate (its time-of-day is what matters).

        Returns:
            float: Output fraction in the closed interval [0.0, 1.0].
        """
        hour = when.hour + when.minute / 60 + when.second / 3600
        if hour <= self.sunrise_hour or hour >= self.sunset_hour:
            return 0.0
        midpoint = (self.sunrise_hour + self.sunset_hour) / 2
        half_width = (self.sunset_hour - self.sunrise_hour) / 2
        return max(0.0, math.cos((hour - midpoint) / half_width * (math.pi / 2)))

    def _jitter(self) -> float:
        """Return a random multiplier around 1.0 for adding noise.

        Returns:
            float: A factor in the range [1 - noise, 1 + noise].
        """
        return 1.0 + random.uniform(-self.noise, self.noise)

    def fetch(self) -> PVReading:
        """Generate one synthetic reading for the current moment.

        Generation follows the solar curve; consumption varies around the
        baseline load; grid import covers whatever the panels cannot.

        Returns:
            PVReading: A fresh reading with all power values in W.
        """
        now = datetime.now(timezone.utc)
        pv_power = self.peak_power_w * self._solar_factor(now) * self._jitter()
        consumption_power = self.base_load_w * self._jitter()
        grid_power = consumption_power - pv_power
        return PVReading(
            timestamp=now,
            pv_power=round(pv_power, 1),
            consumption_power=round(consumption_power, 1),
            grid_power=round(grid_power, 1),
        )
