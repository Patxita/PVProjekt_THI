"""Client for the THI live PV API.

Fetches readings from the real PV API and adapts them into the project's
:class:`PVReading` contract. Implements the :class:`PVDataSource` interface,
so it is a drop-in replacement for :class:`MockPVSource` once the API is
available.

The endpoint URL and credentials are read from environment variables
and never hard-coded. The client fetches live data from the THI PV API
and converts the API payload into the project's PVReading contract.
"""

from datetime import datetime

import requests

from src.backend.config import API_KEY, API_URL
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
        self.url = url or API_URL
        if not self.url:
            raise ValueError("No API URL provided and PV_API_URL is unset.")
        self.timeout = timeout

    def fetch(self) -> PVReading:
        """Fetch the most recent reading from the API.

        Returns:
            PVReading: The latest measurement, with all power values in W.

        Raises:
            ConnectionError: If the API cannot be reached.
        """
        try:
            response = requests.get(
                self.url,
                headers={
                    "X-API-Key": API_KEY,
                },
                timeout=self.timeout,
                verify=False, # THI self-signed certificate
            )

            response.raise_for_status()

            payload = response.json()

            if "data" not in payload:
                raise ValueError("Invalid API response: missing 'data'")

            if "collected_at" not in payload:
                raise ValueError(
                    "Invalid API response: missing 'collected_at'"
                )

            return self._parse(payload)

        except requests.RequestException as exc:
            raise ConnectionError(
                f"Could not reach PV API: {exc}"
            ) from exc



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
        timestamp = datetime.fromisoformat(
            payload["collected_at"]
        )

        pv_power = 0.0
        consumption_power = 0.0

        for item in payload["data"]:
            value = float(item.get("value",0))

            if item["type"] == "generation":
                pv_power += value

            elif item["type"] == "consumption":
                consumption_power += value

        # Grid import is not provided by the API.
        # It is derived as the remaining demand not covered by PV generation.
        grid_import_power = max(
            0.0,
            consumption_power - pv_power,
        )

        return PVReading(
            timestamp=timestamp,
            pv_power=pv_power,
            consumption_power=consumption_power,
            grid_import_power=grid_import_power,
        )