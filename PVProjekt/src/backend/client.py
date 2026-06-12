"""Client for the THI live PV API.

Fetches readings from the real PV API and adapts them into the project's
:class:`PVReading` contract. Implements the :class:`PVDataSource` interface,
so it is a drop-in replacement for :class:`MockPVSource` once the API is
available.

The endpoint URL and any credentials are read from environment variables and
are never hard-coded, keeping secrets out of version control. The concrete
request/parse logic is left unimplemented until the API specification is
provided by the university.
"""

import os

from src.backend.models import PVReading


class ApiClient:
    """Fetches live PV readings from the university's HTTP API.

    Attributes:
        url (str): Base URL of the PV API endpoint.
        timeout (float): Per-request timeout in seconds.
    """

    def __init__(self, url: str | None = None, timeout: float = 5.0) -> None:
        """Initialise the client.

        Args:
            url: API endpoint. If ``None``, it is read from the
                ``PV_API_URL`` environment variable so the real address
                never appears in source control.
            timeout: Per-request timeout in seconds.

        Raises:
            ValueError: If no URL is given and ``PV_API_URL`` is unset.
        """
        self.url = url or os.environ.get("PV_API_URL")
        if not self.url:
            raise ValueError("No API URL provided and PV_API_URL is unset.")
        self.timeout = timeout

    def fetch(self) -> PVReading:
        """Fetch the most recent reading from the API.

        Returns:
            PVReading: The latest measurement, with all power values in W.

        Raises:
            ConnectionError: If the API cannot be reached.
            NotImplementedError: Always, until the API spec is available.
        """
        raise NotImplementedError("Pending the university's API specification.")

    def _parse(self, payload: dict) -> PVReading:
        """Convert a raw API JSON payload into a :class:`PVReading`.

        Args:
            payload: Decoded JSON object as returned by the API.

        Returns:
            PVReading: The mapped reading, with power values in W.

        Raises:
            KeyError: If an expected field is missing from ``payload``.
            NotImplementedError: Until the API field names are known.
        """
        raise NotImplementedError("Field mapping defined once API spec exists.")
