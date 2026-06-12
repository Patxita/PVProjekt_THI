"""Application entry point: the PV data collection loop.

Wires the pipeline together — data source -> cleaner -> exporter — and runs
it forever, fetching a reading every ``INTERVAL_S`` seconds. While the real
PV API is unavailable, :class:`MockPVSource` is used; swapping in
:class:`ApiClient` is a one-line change because both implement
:class:`PVDataSource`.
"""

import time

from src.backend.data_cleaner import DataCleaner
from src.backend.data_storage import PrometheusExporter
from src.backend.mock_source import MockPVSource

INTERVAL_S = 5
EXPORTER_PORT = 8000


def main() -> None:
    """Start the exporter and run the collection loop until interrupted."""
    source = MockPVSource()  # swap for ApiClient() once the API exists
    cleaner = DataCleaner()
    exporter = PrometheusExporter(port=EXPORTER_PORT)
    exporter.start()
    print(f"Exporter live on http://localhost:{EXPORTER_PORT}/metrics")

    while True:
        reading = source.fetch()
        cleaned = cleaner.clean(reading)
        if cleaned is not None:
            exporter.record(cleaned, INTERVAL_S)
        time.sleep(INTERVAL_S)


if __name__ == "__main__":
    main()
