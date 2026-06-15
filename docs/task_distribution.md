## Team

| Name                  | Git-Identität                                    |
|-----------------------|--------------------------------------------------|
| Franziska Pudelek     | `Franziska Pudelek <frp0526@thi.de>` (`Patxita`) |
| Natalia Aldrett Gomez | `z00547vv <naa1438@thi.de>`                      |

## Architecture

Project: PV Monitoring Dashboard — THI

Stack: **SQLite** (data storage) + **Streamlit** (frontend). The earlier
Prometheus + Grafana setup was dropped — the assignment explicitly forbids
Grafana ("kein Grafana") and requires named data-storage and calculation
modules plus pie charts.

```
THI API ──▶ ApiClient ──▶ DataCleaner ──▶ SQLite store   (collector loop, every 5 s)
                                              │
                                              ▼
                          Calculation module (day / month / year + ratios)
                                              │
                                              ▼
                                    Streamlit dashboard
```

## Task Distribution

### Natalia — Data ingestion & calculation

| #  | Task                                                                            |
|----|---------------------------------------------------------------------------------|
| N1 | Live API client — implement `fetch()` + `_parse()` against the real endpoint    |
| N2 | Data cleaning — adapt `DataCleaner` to the real payload, error handling/logging  |
| N3 | Calculation module — current values, day/month/year totals, PV-to-total ratios   |
| N4 | Tests for client, cleaner, metrics + end-to-end integration test (with F2)       |

### Franziska — Storage, frontend, Docker, CI/CD

| #  | Task                                                                            |
|----|---------------------------------------------------------------------------------|
| F1 | SQLite storage module — schema, `insert(reading)`, range query helpers           |
| F2 | Storage tests — insert + range queries (pairs with N4's integration test)        |
| F3 | Streamlit dashboard — metric cards, generation/consumption time series, pie charts |
| F4 | Collection loop — wire `main.py` to `ApiClient` + SQLite store                    |
| F5 | Docker — docker-compose (collector + Streamlit + shared volume) + Dockerfile(s)  |
| F6 | CI/CD pipeline — ruff + black + pytest + docker build + deploy step               |

### Shared

| #  | Task                                                                            |
|----|---------------------------------------------------------------------------------|
| S1 | Git workflow — feature branches + pull requests (no direct commits to `main`)    |
| S2 | Cleanup — remove `grafana/`, `prometheus/`, `prometheus-client` dependency        |
| S3 | Documentation — dashboard spec, README install guide, dashboard screenshot        |

**Shared contract:** F1 (SQLite schema) and N3 (calculation module return shapes)
are the interfaces both tracks depend on — agreed jointly before parallel work begins.

## Collaboration

- Git workflow: feature branches merged into `main` via pull request
- Communication: mostly in-person sessions