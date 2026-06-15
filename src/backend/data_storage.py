"""Prometheus exporter — the project's data-storage layer.

In this architecture Prometheus itself is the time-series database, so this
module does not persist data to files. Instead it defines the metrics,
updates them from each cleaned :class:`PVReading`, and exposes them on an
HTTP ``/metrics`` endpoint that a Prometheus server scrapes every few
seconds.

Metric design:
    * Gauges hold instantaneous power values (W) and the autarky ratio.
    * Counters hold cumulative energy (Wh); Grafana derives per-day totals
      from them with PromQL ``increase()``.
"""

from prometheus_client import REGISTRY, Counter, Gauge, start_http_server

from src.backend.metrics import MetricsCalculator
from src.backend.models import PVReading


class PrometheusExporter:
    """Defines, updates, and serves the project's Prometheus metrics.

    Attributes:
        port (int): TCP port on which the ``/metrics`` endpoint is served.
        calculator (MetricsCalculator): Computes derived KPIs and energy
            increments from each reading.
    """

    def __init__(
        self,
        port: int = 8000,
        calculator: MetricsCalculator | None = None,
        registry=REGISTRY,
    ) -> None:
        """Create the exporter and register all metrics.

        Args:
            port: TCP port for the ``/metrics`` HTTP endpoint.
            calculator: KPI calculator; a default one is created if omitted.
            registry: Prometheus registry to register metrics in. Defaults
                to the global one; tests pass a fresh registry for isolation.
        """
        self.port = port
        self.calculator = calculator or MetricsCalculator()

        self.pv_power = Gauge(
            "pv_power_watts", "Current PV generation in W.", registry=registry
        )
        self.consumption_power = Gauge(
            "consumption_power_watts",
            "Current building consumption in W.",
            registry=registry,
        )
        self.grid_import_power = Gauge(
            "grid_import_power_watts",
            "Current power drawn from the grid in W.",
            registry=registry,
        )
        self.self_consumption = Gauge(
            "self_consumption_watts",
            "PV power consumed on-site in W.",
            registry=registry,
        )
        self.autarky = Gauge(
            "autarky_ratio",
            "Share of consumption covered by PV (0-1).",
            registry=registry,
        )
        self.grid_export_power = Gauge(
            "grid_export_power_watts",
            "Current surplus power fed into the grid in W.",
            registry=registry,
        )

        self.pv_energy = Counter(
            "pv_energy_wh_total",
            "Cumulative PV energy generated in Wh.",
            registry=registry,
        )
        self.consumption_energy = Counter(
            "consumption_energy_wh_total",
            "Cumulative energy consumed in Wh.",
            registry=registry,
        )
        self.grid_import_energy = Counter(
            "grid_import_energy_wh_total",
            "Cumulative energy imported in Wh.",
            registry=registry,
        )
        self.grid_export_energy = Counter(
            "grid_export_energy_wh_total",
            "Cumulative energy fed into the grid in Wh.",
            registry=registry,
        )

    def start(self) -> None:
        """Start the background HTTP server exposing ``/metrics``.

        Non-blocking: ``prometheus_client`` serves the endpoint on its own
        thread, so the collection loop can continue afterwards.
        """
        start_http_server(self.port)

    def record(self, reading: PVReading, interval_s: float) -> None:
        """Update all metrics from one cleaned reading.

        Gauges are set to the reading's instantaneous values; counters are
        incremented by the energy produced/consumed during the elapsed
        interval (instantaneous power is taken as the interval average).

        Args:
            reading: A cleaned :class:`PVReading` with power values in W.
            interval_s: Seconds since the previous reading, used to convert
                power (W) into an energy increment (Wh).
        """
        export_w = self.calculator.grid_export_w(reading)

        self.pv_power.set(reading.pv_power)
        self.consumption_power.set(reading.consumption_power)
        self.grid_import_power.set(reading.grid_import_power)
        self.grid_export_power.set(export_w)
        self.self_consumption.set(self.calculator.self_consumption_w(reading))
        self.autarky.set(self.calculator.autarky_ratio(reading))

        inc = self.calculator.energy_increment_wh
        self.pv_energy.inc(inc(reading.pv_power, interval_s))
        self.consumption_energy.inc(inc(reading.consumption_power, interval_s))
        self.grid_import_energy.inc(inc(reading.grid_import_power, interval_s))
        self.grid_export_energy.inc(inc(export_w, interval_s))
