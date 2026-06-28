# Dashboard Specification

This document describes the metrics, KPIs, and graphics displayed on the PV monitoring dashboard (`app.py`).

---

## Overview

The dashboard is built with **Streamlit** and auto-refreshes every **5 seconds**.
All data is read from a local **SQLite database** (`data/pv.db`) populated by the collector (`src/main.py`).
All timestamps are displayed in **CEST (UTC+2)**. All power values are in **W**, all energy values in **Wh**.

---

## Layout

The dashboard is divided into two sections:

- **Above the tabs (always visible):** title, current values metric cards
- **Tab 1 — 📅 Today:** today's totals, monthly/yearly totals, time-series chart, pie charts
- **Tab 2 — 🔍 Historical:** date picker, daily summary table, CSV export

Screenshots: see `docs/images/dashboard_screenshot_today.png` and `docs/images/dashboard_screenshot_historical.png`.

---

## Metric Cards

### Current values (latest reading, always visible)

| Metric | Unit | Description |
|--------|------|-------------|
| PV generation | W | Instantaneous power currently produced by the panels |
| Consumption | W | Instantaneous power currently consumed by the building |
| Grid import / Grid export | W | Instantaneous grid power. Positive = importing from grid; negative = exporting to grid (feed-in). Label switches automatically. |
| Autarky (now) | % | Share of current consumption covered by PV: `min(pv, consumption) / consumption × 100` |

### Today's totals (Tab 1)

| Metric | Unit | Description |
|--------|------|-------------|
| PV generated (today) | Wh | Cumulative PV energy since midnight UTC |
| Consumed (today) | Wh | Cumulative consumption energy since midnight UTC |
| Grid import (today) | Wh | Cumulative grid power since midnight (can be negative when net feed-in) |
| Autarky (today) | % | `sum(self_consumption) / sum(consumption) × 100` over all readings today |

### Monthly & yearly totals (Tab 1)

| Metric | Unit | Description |
|--------|------|-------------|
| PV generated (month) | Wh | Cumulative PV energy since the 1st of the current month |
| Consumed (month) | Wh | Cumulative consumption since the 1st of the current month |
| PV generated (year) | Wh | Cumulative PV energy since January 1st of the current year |
| Consumed (year) | Wh | Cumulative consumption since January 1st of the current year |

---

## Graphics

### Time-series chart (Tab 1 and Tab 2)

- **X-axis:** Time (CEST)
- **Left Y-axis:** Cumulative PV energy generated (Wh) — filled area, orange
- **Right Y-axis:** Instantaneous consumption power (W) — line, blue
- **Tab 1:** shows today's data only (midnight to now)
- **Tab 2:** shows data for the selected date

### Pie charts × 3 (Tab 1)

One pie chart each for **today**, **this month**, and **this year**.

| Slice | Colour | Description |
|-------|--------|-------------|
| PV (self-consumption) | Orange | Share of total consumption covered by PV |
| Grid import | Blue | Share of total consumption drawn from the grid |

- **KPI shown:** PV-vs-total consumption ratio (autarky)
- **Calculation:** `sum(min(pv, consumption)) / sum(consumption)` over all readings in the period

---

## Historical tab (Tab 2)

| Feature | Description |
|---------|-------------|
| Date picker | Select any past date to inspect its data |
| Summary metrics | PV generated, consumed, autarky, and reading count for the selected date |
| Time-series chart | Generation (Wh) and consumption (W) for the selected date |
| Daily summary table | Last 7 days — generation, consumption, autarky, and reading count per day |
| CSV export | Download today's or any selected day's raw readings as a CSV file |

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

Grid power is stored as-is and can be negative when the university feeds surplus energy back into the grid.
