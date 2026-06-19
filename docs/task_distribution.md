# Task Distribution

## 🟦 Natalia — Data ingestion & calculation

| # | Task | File(s) | Status |
|---|------|---------|--------|
| N1 | Implement the live API client — `fetch()` + `_parse()` against the real endpoint | `src/backend/client.py` | ⏳ In progress |
| N2 | Adjust DataCleaner for the real payload (types, missing values, units) + error handling/logging | `src/backend/data_cleaner.py` | ⏳ In progress |
| N3 | Calculation module — current values + day/month/year totals + PV-to-total consumption ratios | `src/backend/metrics.py` | ⚠️ Partial |
| N4 | Tests for client, cleaner, metrics (+ end-to-end fetch→clean→store→aggregate integration test) | `tests/` | ⚠️ Partial |

## 🟥 Franziska — Storage, frontend, Docker, CI/CD

| # | Task | File(s) | Status |
|---|------|---------|--------|
| F1 | Build the SQLite storage module — schema, `insert(reading)`, query helpers by time range | `src/backend/data_storage.py` | ✅ Done |
| F2 | Storage tests — unit tests for insert + range queries | `tests/test_data_storage.py` | ✅ Done |
| F3 | Streamlit dashboard — metric cards, time-series chart, 3 pie charts, auto-refresh | `app.py` | ✅ Done |
| F4 | Collection loop — wire `main.py` to use `ApiClient` + SQLite store | `src/main.py` | ✅ Done |
| F5 | Docker — rewrite docker-compose (collector + Streamlit + shared volume, no Grafana/Prometheus) + Dockerfile | `docker-compose.yml`, `Dockerfile` | ✅ Done |
| F6 | CI/CD pipeline — ruff + black + pytest + docker build | `.github/workflows/ci.yml` | ✅ Done |

## 🟩 Shared

| # | Task | Status |
|---|------|--------|
| S1 | Switch to feature branches + PRs (stop committing to `main`) | ✅ Done |
| S2 | Cleanup — delete `grafana/`, `prometheus/`, remove `prometheus-client` dep | ✅ Done |
| S3 | Docs — rewrite `dashboard_spec.md`, update `task_distribution.md`, README install, dashboard screenshot | ✅ Done |
