"""Streamlit dashboard for the PV monitoring system.

Displays real-time and historical metrics fetched from the SQLite database.
Auto-refreshes every 5 seconds to stay in sync with the collector.

Layout
------
- Header metric cards: current generation/consumption/grid power
- Tab 1 (Today): today's totals, monthly/yearly totals, time-series chart,
  pie charts
- Tab 2 (Historical): date picker, daily summary table, CSV export

Notes:
-----
All energy (Wh) and autarky values are derived on read from the raw power
readings stored by ``src/main.py``; they are never stored themselves.
"""

import logging
import time
from datetime import date, datetime, timedelta, timezone
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
REFRESH_INTERVAL_S = 5
COLLECTION_INTERVAL_S = 5
CEST = timezone(timedelta(hours=2))

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
    """Open a :class:`SQLiteStorage` connection.

    Returns:
        SQLiteStorage: A connection to the database at ``DB_PATH``.
    """
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    return SQLiteStorage(DB_PATH)


def _day_range(for_date: date | None = None) -> tuple[datetime, datetime]:
    """Return midnight-to-end-of-day for a given date in UTC.

    Args:
        for_date: The date to use. Defaults to today.

    Returns:
        tuple[datetime, datetime]: ``(start_of_day, end_of_day)`` UTC-aware.
    """
    d = for_date or date.today()
    start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    end = datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc)
    return start, end


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
        grid_power, pv_energy_wh.
    """
    if not readings:
        return pd.DataFrame(
            columns=[
                "timestamp",
                "pv_power",
                "consumption_power",
                "grid_power",
                "pv_energy_wh",
            ]
        )
    df = pd.DataFrame(
        {
            "timestamp": [r.timestamp for r in readings],
            "pv_power": [r.pv_power for r in readings],
            "consumption_power": [r.consumption_power for r in readings],
            "grid_power": [r.grid_power for r in readings],
        }
    )
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


def _timeseries_chart(df: pd.DataFrame) -> go.Figure:
    """Build a dual-axis time-series chart for generation and consumption.

    Args:
        df: DataFrame with columns ``timestamp``, ``pv_energy_wh``,
            ``consumption_power`` as produced by :func:`_readings_to_df`.

    Returns:
        go.Figure: A Plotly dual-axis line chart.
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["pv_energy_wh"],
            name="PV generation (Wh)",
            line=dict(color="#f5a623", width=2),
            fill="tozeroy",
            fillcolor="rgba(245,166,35,0.15)",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["consumption_power"],
            name="Consumption (W)",
            line=dict(color="#4a90d9", width=2),
        ),
        secondary_y=True,
    )
    fig.update_yaxes(title_text="Generated energy (Wh)", secondary_y=False)
    fig.update_yaxes(title_text="Consumption (W)", secondary_y=True)
    fig.update_xaxes(title_text="Time (CEST)")
    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=20, b=40),
        hovermode="x unified",
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
    # Latest reading – metric cards (always visible, above tabs)
    # ------------------------------------------------------------------
    latest = store.latest()
    st.subheader("⚡ Current values")

    if latest is None:
        st.info(
            "No readings yet. Start the collector (`python -m src.main`) and refresh."
        )
        store.close()
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("PV generation", f"{latest.pv_power:,.0f} W")
    col2.metric("Consumption", f"{latest.consumption_power:,.0f} W")
    grid_label = "Grid export ↑" if latest.grid_power < 0 else "Grid import ↓"
    col3.metric(grid_label, f"{abs(latest.grid_power):,.0f} W")
    col4.metric("Autarky (now)", f"{calc.autarky_ratio(latest) * 100:.1f} %")

    last_reading_cest = latest.timestamp.astimezone(CEST).strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"Last reading: {last_reading_cest} CEST")

    st.divider()

    # ------------------------------------------------------------------
    # Tabs
    # ------------------------------------------------------------------
    tab1, tab2 = st.tabs(["📅 Today", "🔍 Historical"])

    # ==================================================================
    # TAB 1 — Today
    # ==================================================================
    with tab1:
        day_start, day_end = _day_range()
        day_readings = store.query_range(day_start, day_end)

        # Today's totals
        st.subheader("📅 Today's totals")
        c1, c2, c3, c4 = st.columns(4)

        if day_readings:
            day_df = _readings_to_df(day_readings)
            day_summary = calc.period_summary(day_readings, COLLECTION_INTERVAL_S)
            total_gen_wh = day_summary["generation_wh"]
            total_cons_wh = day_summary["consumption_wh"]
            day_autarky = day_summary["autarky"] * 100
            total_import_wh = (
                day_df["grid_power"] * COLLECTION_INTERVAL_S / 3600.0
            ).sum()
            c1.metric("PV generated (today)", f"{total_gen_wh:,.0f} Wh")
            c2.metric("Consumed (today)", f"{total_cons_wh:,.0f} Wh")
            c3.metric("Grid import (today)", f"{total_import_wh:,.0f} Wh")
            c4.metric("Autarky (today)", f"{day_autarky:.1f} %")
        else:
            day_df = pd.DataFrame()
            c1.metric("PV generated (today)", "– Wh")
            c2.metric("Consumed (today)", "– Wh")
            c3.metric("Grid import (today)", "– Wh")
            c4.metric("Autarky (today)", "– %")

        # Monthly & yearly totals
        st.subheader("📆 Monthly & yearly totals")
        m1, m2, y1, y2 = st.columns(4)

        month_readings = store.query_range(*_month_range())
        year_readings = store.query_range(*_year_range())
        month_summary = calc.period_summary(month_readings, COLLECTION_INTERVAL_S)
        year_summary = calc.period_summary(year_readings, COLLECTION_INTERVAL_S)

        m1.metric("PV generated (month)", f"{month_summary['generation_wh']:,.0f} Wh")
        m2.metric("Consumed (month)", f"{month_summary['consumption_wh']:,.0f} Wh")
        y1.metric("PV generated (year)", f"{year_summary['generation_wh']:,.0f} Wh")
        y2.metric("Consumed (year)", f"{year_summary['consumption_wh']:,.0f} Wh")

        st.divider()

        # Time-series chart
        st.subheader("📈 Today's generation (Wh) and consumption (W)")
        if day_readings and not day_df.empty:
            st.plotly_chart(
                _timeseries_chart(day_df), width="stretch", key="today_chart"
            )
        else:
            st.info("No data for today yet.")

        st.divider()

        # Pie charts
        st.subheader("🥧 PV self-coverage ratio")
        pc1, pc2, pc3 = st.columns(3)
        pc1.plotly_chart(_autarky_pie(day_readings, calc, "Today"), width="stretch")
        pc2.plotly_chart(
            _autarky_pie(month_readings, calc, "This month"), width="stretch"
        )
        pc3.plotly_chart(
            _autarky_pie(year_readings, calc, "This year"), width="stretch"
        )

    # ==================================================================
    # TAB 2 — Historical
    # ==================================================================
    with tab2:

        # Date picker
        st.subheader("🔍 Historical data view")
        selected_date = st.date_input(
            "Select a date to inspect",
            value=date.today(),
            max_value=date.today(),
        )

        hist_start, hist_end = _day_range(selected_date)
        hist_readings = store.query_range(hist_start, hist_end)

        if hist_readings:
            hist_df = _readings_to_df(hist_readings)
            h1, h2, h3, h4 = st.columns(4)
            hist_gen_wh = hist_df["pv_energy_wh"].iloc[-1]
            hist_cons_wh = (
                hist_df["consumption_power"] * COLLECTION_INTERVAL_S / 3600.0
            ).sum()
            hist_self = sum(calc.self_consumption_w(r) for r in hist_readings)
            hist_cons = sum(r.consumption_power for r in hist_readings)
            hist_autarky = (hist_self / hist_cons * 100) if hist_cons > 0 else 100.0
            h1.metric("PV generated", f"{hist_gen_wh:,.0f} Wh")
            h2.metric("Consumed", f"{hist_cons_wh:,.0f} Wh")
            h3.metric("Autarky", f"{hist_autarky:.1f} %")
            h4.metric("Readings", f"{len(hist_readings)}")
            st.plotly_chart(
                _timeseries_chart(hist_df), width="stretch", key="hist_chart"
            )
        else:
            hist_df = pd.DataFrame()
            st.info(f"No data available for {selected_date}.")

        st.divider()

        # Daily summary table
        st.subheader("📊 Daily summary — last 7 days")
        summary_rows = []
        for days_ago in range(7):
            d = date.today() - timedelta(days=days_ago)
            d_start, d_end = _day_range(d)
            d_readings = store.query_range(d_start, d_end)
            if d_readings:
                d_summary = calc.period_summary(d_readings, COLLECTION_INTERVAL_S)
                summary_rows.append(
                    {
                        "Date": d.strftime("%Y-%m-%d"),
                        "PV generated (Wh)": f"{d_summary['generation_wh']:,.0f}",
                        "Consumed (Wh)": f"{d_summary['consumption_wh']:,.0f}",
                        "Autarky (%)": f"{d_summary['autarky'] * 100:.1f}",
                        "Readings": len(d_readings),
                    }
                )
            else:
                summary_rows.append(
                    {
                        "Date": d.strftime("%Y-%m-%d"),
                        "PV generated (Wh)": "–",
                        "Consumed (Wh)": "–",
                        "Autarky (%)": "–",
                        "Readings": 0,
                    }
                )
        st.dataframe(pd.DataFrame(summary_rows), width="stretch", hide_index=True)

        st.divider()

        # CSV export
        st.subheader("💾 Export data")
        export_col1, export_col2 = st.columns(2)

        with export_col1:
            day_start2, day_end2 = _day_range()
            today_readings = store.query_range(day_start2, day_end2)
            if today_readings:
                export_df = _readings_to_df(today_readings)[
                    ["timestamp", "pv_power", "consumption_power", "grid_power"]
                ]
                csv_bytes = export_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="⬇️ Download today's data as CSV",
                    data=csv_bytes,
                    file_name=f"pv_data_{date.today()}.csv",
                    mime="text/csv",
                )
            else:
                st.info("No data for today to export.")

        with export_col2:
            if hist_readings:
                hist_export_df = _readings_to_df(hist_readings)[
                    ["timestamp", "pv_power", "consumption_power", "grid_power"]
                ]
                hist_csv = hist_export_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label=f"⬇️ Download {selected_date} data as CSV",
                    data=hist_csv,
                    file_name=f"pv_data_{selected_date}.csv",
                    mime="text/csv",
                )
            else:
                st.info("No data for selected date to export.")

    store.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

render_dashboard()

time.sleep(REFRESH_INTERVAL_S)
st.rerun()
