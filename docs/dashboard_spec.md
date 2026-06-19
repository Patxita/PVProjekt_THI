# Dashboard Specification

This document describes the metrics, KPIs, and graphics displayed on the PV monitoring dashboard (`app.py`).

---

## Overview

The dashboard is built with **Streamlit** and auto-refreshes every **5 seconds**.
All data is read from a local **SQLite database** (`data/pv.db`) populated by the collector (`src/main.py`).
All timestamps are in **UTC**. All power values are in **W**, all energy values in **Wh**.

---

## Metric Cards

### Current values (latest reading)

| Metric | Unit | Description |
|--------|------|-------------|
| PV generation | W | Instantaneous power currently produced by the panels |
| Consumption | W | Instantaneous power currently consumed by the building |
| Grid import | W | Instantaneous power currently drawn from the external grid |
| Autarky (now) | % | Share of current consumption covered by PV: `min(pv, consumption) / consumption × 100` |

### Today's totals

| Metric | Unit | Description |
|--------|------|-------------|
| PV generated (today) | Wh | Cumulative PV energy since midnight UTC |
| Consumed (today) | Wh | Cumulative consumption energy since midnight UTC |
| Grid import (today) | Wh | Cumulative grid import energy since midnight UTC |
| Autarky (today) | % | `sum(self_consumption) / sum(consumption) × 100` over all readings today |

### Monthly & yearly totals

| Metric | Unit | Description |
|--------|------|-------------|
| PV generated (month) | Wh | Cumulative PV energy since the 1st of the current month |
| Consumed (month) | Wh | Cumulative consumption since the 1st of the current month |
| PV generated (year) | Wh | Cumulative PV energy since January 1st of the current year |
| Consumed (year) | Wh | Cumulative consumption since January 1st of the current year |

---

## Graphics

### Time-series chart

- **Title:** Today's generation (Wh) and consumption (W)
- **X-axis:** Time (UTC)
- **Left Y-axis:** Cumulative PV energy generated today (Wh) — filled area, orange
- **Right Y-axis:** Instantaneous consumption power (W) — line, blue
- **Data range:** Midnight UTC to now (today only)

### Pie charts (× 3)

One pie chart each for **today**, **this month**, and **this year**.

| Slice | Colour | Description |
|-------|--------|-------------|
| PV (self-consumption) | Orange | Share of total consumption covered by PV |
| Grid import | Blue | Share of total consumption drawn from the grid |

- **KPI shown:** PV-vs-total consumption ratio (autarky)
- **Calculation:** `sum(min(pv, consumption)) / sum(consumption)` over all readings in the period

---

## Data pipeline

```
API (every 5 s)
    → src/backend/client.py       # fetch raw reading
    → src/backend/data_cleaner.py # validate & repair
    → src/backend/data_storage.py # persist to SQLite
    → app.py (Streamlit)          # read & visualise
```

Energy values (Wh) are **never stored** — they are always derived on read by multiplying the stored power (W) by the sampling interval (5 s / 3600).
