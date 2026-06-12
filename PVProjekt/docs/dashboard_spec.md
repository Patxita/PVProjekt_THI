# PV Dashboard — Metrics & KPI Specification

## Raw metrics (collected every ~5 s, stored in Prometheus)
| Metric                      | Type    | Unit | Meaning                                                       |
|-----------------------------|---------|------|---------------------------------------------------------------|
| pv_power_watts              | Gauge   | W    | Instantaneous PV generation                                   |
| consumption_power_watts     | Gauge   | W    | Instantaneous building consumption                            |
| grid_import_power_watts     | Gauge   | W    | Instantaneous power drawn from the grid                       |
| self_consumption_watts      | Gauge   | W    | PV power consumed on-site = min(pv, consumption)              |
| autarky_ratio               | Gauge   | 0–1  | Share of consumption covered by PV                            |
| pv_energy_wh_total          | Counter | Wh   | Cumulative energy generated                                   |
| consumption_energy_wh_total | Counter | Wh   | Cumulative energy consumed                                    |
| grid_import_energy_wh_total | Counter | Wh   | Cumulative energy imported                                    |
| grid_export_power_watts     | Gauge   | W    | Surplus PV power fed into the grid = max(0, pv − consumption) |
| grid_export_energy_wh_total | Counter | Wh   | Cumulative energy fed into the grid                           |

## KPIs shown on the dashboard
| KPI                                                 | Derived from                                                              | Panel       |
|-----------------------------------------------------|---------------------------------------------------------------------------|-------------|
| Current generation / consumption / grid import (kW) | the three power gauges                                                    | Stat        |
| Autarky (%)                                         | autarky_ratio × 100                                                       | Gauge       |
| Today's generation vs. consumption curve            | the two power gauges over time                                            | Time series |
| Energy generated/consumed/imported (kWh)            | increase(<counter>[$__range])                                             | Stat        |
| Energy generated per day                            | increase(pv_energy_wh_total[1d])                                          | Bar chart   |
| Grid feed-in (current + cumulative)                 | grid_export_power_watts / increase(grid_export_energy_wh_total[$__range]) | Stat        |

## Design rationale
- Store raw measurements (W), derive KPIs on read (kWh, %, …).
- Prometheus is the time-series store; Grafana is the visualization layer.
- Counters + increase() give correct per-period totals even across restarts.