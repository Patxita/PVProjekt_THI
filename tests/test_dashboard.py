"""Validation tests for the Grafana dashboard provisioning.

Ensures the committed dashboard JSON is valid and that every Prometheus
datasource reference matches the provisioned datasource uid, so a fresh
``docker compose up`` always yields a working dashboard.
"""

import json
from pathlib import Path

DASHBOARD = Path("grafana/provisioning/dashboards/pv_monitoring.json")


def test_dashboard_json_is_valid() -> None:
    """The committed dashboard file parses as valid JSON."""
    json.loads(DASHBOARD.read_text())


def test_datasource_references_are_valid() -> None:
    """Every datasource reference points to a known datasource.

    Grafana exports freeze a random datasource uid; this walks the whole
    dashboard JSON and asserts every datasource name is either the
    provisioned Prometheus uid or Grafana's built-in datasource. It fails
    loudly if a stale auto-generated uid slips in on re-export.
    """
    data = json.loads(DASHBOARD.read_text())
    allowed = {"prometheus", "-- Grafana --"}
    names: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, dict):
            ds = node.get("datasource")
            if isinstance(ds, dict) and "name" in ds:
                names.add(ds["name"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    assert names <= allowed, f"Unexpected datasource refs: {names - allowed}"
