"""Interfaces (structural types) shared across the backend.

Defines the :class:`PVDataSource` protocol that both the mock generator and
the real API client implement, so the collection loop depends on this
abstraction rather than on any concrete data source.
"""

from typing import Protocol

from src.backend.models import PVReading


class PVDataSource(Protocol):
    """Interface for any source that can supply PV readings.

    Both the mock generator and the real API client implement this, so the
    collection loop in ``main.py`` depends only on this abstraction and not
    on a concrete data source (dependency inversion).
    """

    def fetch(self) -> PVReading:
        """Fetch the most recent PV reading.

        Returns:
            PVReading: The latest measurement, with all power values in W.

        Raises:
            ConnectionError: If the underlying source is unreachable.
        """
        ...
