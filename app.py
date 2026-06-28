"""Streamlit dashboard for the PV monitoring system.

Displays real-time and historical metrics fetched from the SQLite database.
Auto-refreshes every 5 seconds to stay in sync with the collector.

Layout
------
- Header metric cards: current generation/consumption/grid-import
- Time-series chart: today's generation (Wh cumulative) and consumption (W)
- Three pie charts: PV-vs-total ratio for today / current month / current year

Notes:
------
All energy (Wh) and autarky values are derived on read from the raw power
readings stored by ``src/main.py``; they are never stored themselves.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from src.backend.data_storage import SQLiteStorage
from src.backend.metrics import MetricsCalculator

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DB_PATH = "data/pv.db"
REFRESH_INTERVAL_S = 5  # seconds between auto-refresh calls
COLLECTION_INTERVAL_S = 5  # assumed interval between readings (for Wh calc)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="PV Dashboard – THI",
    page_icon="☀️",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_store() -> SQLiteStorage:
    """Open a cached :class:`SQLiteStorage` connection.

    Returns:
        SQLiteStorage: A connection to the database at ``DB_PATH``.
    """
    Path(DB_PATH).parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    return SQLiteStorage(DB_PATH)


def _day_range() -> tuple[datetime, datetime]:
    """Return midnight-to-now for today in UTC.

    Returns:
        tuple[datetime, datetime]: ``(start_of_day, now)`` both UTC-aware.
    """
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, now


def _month_range() -> tuple[datetime, datetime]:
    """Return first-of-month-to-now for the current month in UTC.

    Returns:
        tuple[datetime, datetime]: ``(start_of_month, now)`` both UTC-aware.
    """
    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, now


def _year_range() -> tuple[datetime, datetime]:
    """Return first-of-year-to-now for the current year in UTC.

    Returns:
        tuple[datetime, datetime]: ``(start_of_year, now)`` both UTC-aware.
    """
    now = datetime.now(timezone.utc)
    start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, now


def _readings_to_df(
    readings: list, interval_s: float = COLLECTION_INTERVAL_S
) -> pd.DataFrame:
    """Convert a list of :class:`PVReading` objects to a pandas DataFrame.

    Adds a cumulative ``pv_energy_wh`` column computed from power and the
    sampling interval so the time-series chart can show generated energy.

    Args:
        readings: Ordered list of :class:`PVReading` objects (oldest first).
        interval_s: Assumed time between consecutive readings in seconds.

    Returns:
        pd.DataFrame: Columns: timestamp, pv_power, consumption_power,
        grid_import_power, pv_energy_wh.
    """
    if not readings:
        return pd.DataFrame(
            columns=[
                "timestamp",
                "pv_power",
                "consumption_power",
                "grid_import_power",
                "pv_energy_wh",
            ]
        )
    df = pd.DataFrame(
        {
            "timestamp": [r.timestamp for r in readings],
            "pv_power": [r.pv_power for r in readings],
            "consumption_power": [r.consumption_power for r in readings],
            "grid_import_power": [r.grid_import_power for r in readings],
        }
    )
    # Cumulative energy in Wh (power × interval / 3600)
    df["pv_energy_wh"] = (df["pv_power"] * interval_s / 3600.0).cumsum()
    return df


def _autarky_pie(
    readings: list,
    calc: MetricsCalculator,
    title: str,
) -> go.Figure:
    """Build a pie chart showing PV self-coverage vs. grid usage.

    Args:
        readings: The readings to aggregate.
        calc: A :class:`MetricsCalculator` instance.
        title: Chart title shown above the pie.

    Returns:
        go.Figure: A Plotly pie chart. Returns a placeholder chart when no
        readings are available.
    """
    if not readings:
        fig = go.Figure(go.Pie(labels=["No data"], values=[1], hole=0.4))
        fig.update_layout(title_text=title, showlegend=False)
        return fig

    total_consumption = sum(r.consumption_power for r in readings)
    total_self = sum(calc.self_consumption_w(r) for r in readings)
    grid_portion = max(0.0, total_consumption - total_self)

    labels = ["PV (self-consumption)", "Grid import"]
    values = [total_self, grid_portion]
    colors = ["#f5a623", "#4a90d9"]

    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            marker_colors=colors,
            textinfo="percent+label",
        )
    )
    fig.update_layout(
        title_text=title,
        showlegend=False,
        margin=dict(t=40, b=10, l=10, r=10),
    )
    return fig


# ---------------------------------------------------------------------------
# Main dashboard
# ---------------------------------------------------------------------------


def render_dashboard() -> None:
    """Render the complete PV monitoring dashboard.

    Loads data from SQLite, calculates KPIs, and renders all widgets.
    Called once per Streamlit script run (including auto-refresh).
    """
    store = _load_store()
    calc = MetricsCalculator()

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------
    st.title("☀️ PV Monitoring Dashboard – THI Ingolstadt")
    st.caption("Data refreshes every 5 seconds  |  All times CEST (UTC+2)")
    # ------------------------------------------------------------------
    # Latest reading – metric cards
    # ------------------------------------------------------------------
    latest = store.latest()
    st.subheader("⚡ Current values")

    if latest is None:
        st.info(
            "No readings yet. Start the collector" "(`python -m src.main`) and refresh."
        )
        store.close()
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("PV generation", f"{latest.pv_power:,.0f} W")
    col2.metric("Consumption", f"{latest.consumption_power:,.0f} W")
    col3.metric("Grid import", f"{latest.grid_import_power:,.0f} W")
    col4.metric(
        "Autarky (now)",
        f"{calc.autarky_ratio(latest) * 100:.1f} %",
    )
    from datetime import timedelta, timezone
    CEST = timezone(timedelta(hours=2))
    last_reading_cest = latest.timestamp.astimezone(CEST).strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"Last reading: {last_reading_cest} CEST")
    st.divider()

    # ------------------------------------------------------------------
    # Today's aggregates
    # ------------------------------------------------------------------
    day_start, now = _day_range()
    day_readings = store.query_range(day_start, now)

    st.subheader("📅 Today's totals")
    c1, c2, c3, c4 = st.columns(4)

    if day_readings:
        day_df = _readings_to_df(day_readings)

        day_summary = calc.period_summary(
            day_readings,
            COLLECTION_INTERVAL_S,
        )

        total_gen_wh = day_summary["generation_wh"]

        total_cons_wh = day_summary["consumption_wh"]

        day_autarky = day_summary["autarky"] * 100

        total_import_wh = (
            day_df["grid_import_power"] * COLLECTION_INTERVAL_S / 3600.0
        ).sum()
        c1.metric("PV generated (today)", f"{total_gen_wh:,.0f} Wh")
        c2.metric("Consumed (today)", f"{total_cons_wh:,.0f} Wh")
        c3.metric("Grid import (today)", f"{total_import_wh:,.0f} Wh")
        c4.metric("Autarky (today)", f"{day_autarky:.1f} %")
    else:
        c1.metric("PV generated (today)", "– Wh")
        c2.metric("Consumed (today)", "– Wh")
        c3.metric("Grid import (today)", "– Wh")
        c4.metric("Autarky (today)", "– %")

    # ------------------------------------------------------------------
    # Monthly & yearly aggregates
    # ------------------------------------------------------------------
    st.subheader("📆 Monthly & yearly totals")
    m1, m2, y1, y2 = st.columns(4)

    month_readings = store.query_range(*_month_range())
    year_readings = store.query_range(*_year_range())

    month_summary = calc.period_summary(
        month_readings,
        COLLECTION_INTERVAL_S,
    )

    year_summary = calc.period_summary(
        year_readings,
        COLLECTION_INTERVAL_S,
    )

    m1.metric("PV generated (month)", f"{month_summary['generation_wh']:,.0f} Wh")
    m2.metric("Consumed (month)", f"{month_summary['consumption_wh']:,.0f} Wh")
    y1.metric("PV generated (year)", f"{year_summary['generation_wh']:,.0f} Wh")
    y2.metric("Consumed (year)", f"{year_summary['consumption_wh']:,.0f} Wh")

    st.divider()

    # ------------------------------------------------------------------
    # Time-series chart: today's generation (Wh) + consumption (W)
    # ------------------------------------------------------------------
    st.subheader("📈 Today's generation (Wh) and consumption (W)")

    if day_readings and not day_df.empty:
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        fig.add_trace(
            go.Scatter(
                x=day_df["timestamp"],
                y=day_df["pv_energy_wh"],
                name="PV generation (Wh)",
                line=dict(color="#f5a623", width=2),
                fill="tozeroy",
                fillcolor="rgba(245,166,35,0.15)",
            ),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=day_df["timestamp"],
                y=day_df["consumption_power"],
                name="Consumption (W)",
                line=dict(color="#4a90d9", width=2),
            ),
            secondary_y=True,
        )

        fig.update_yaxes(title_text="Generated energy (Wh)", secondary_y=False)
        fig.update_yaxes(title_text="Consumption (W)", secondary_y=True)
        fig.update_xaxes(title_text="Time (UTC)")
        fig.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin=dict(t=20, b=40),
            hovermode="x unified",
        )
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No data for today yet.")

    st.divider()

    # ------------------------------------------------------------------
    # Pie charts: autarky for today / month / year
    # ------------------------------------------------------------------
    st.subheader("🥧 PV self-coverage ratio")
    pc1, pc2, pc3 = st.columns(3)

    pc1.plotly_chart(
        _autarky_pie(day_readings, calc, "Today"),
        width="stretch",
    )
    pc2.plotly_chart(
        _autarky_pie(month_readings, calc, "This month"),
        width="stretch",
    )
    pc3.plotly_chart(
        _autarky_pie(year_readings, calc, "This year"),
        width="stretch",
    )

    store.close()

    # Auto-refresh
    st.empty()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

render_dashboard()

# Trigger a periodic rerun so the dashboard updates automatically
import time  # noqa: E402 (import at bottom is intentional here)

time.sleep(REFRESH_INTERVAL_S)
st.rerun()
