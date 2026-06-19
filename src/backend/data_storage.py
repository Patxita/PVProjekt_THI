"""SQLite storage layer for the PV monitoring pipeline.

Persists each cleaned :class:`PVReading` as one row and reads readings back
by time range. This is the single module that knows SQL; the rest of the
backend depends only on :class:`PVReading`.

Design principle (store raw, derive on read): only the raw instantaneous
power values are stored. Energy (Wh), autarky, etc. are computed later by the
calculation layer from these rows.
"""

import sqlite3
from datetime import datetime

from src.backend.models import PVReading

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS readings (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp         TEXT    NOT NULL,
    pv_power          REAL    NOT NULL,
    consumption_power REAL    NOT NULL,
    grid_import_power REAL    NOT NULL
);
"""

_CREATE_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_readings_timestamp ON readings (timestamp);"
)


class SQLiteStorage:
    """Stores and retrieves :class:`PVReading` rows in a SQLite database.

    Attributes:
        conn (sqlite3.Connection): Open connection to the database file.
    """

    def __init__(self, db_path: str) -> None:
        """Open (or create) the database and ensure the schema exists.

        Args:
            db_path: Filesystem path to the SQLite file, e.g.
                ``"data/pv.db"``. Created if it does not yet exist.
        """
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(_CREATE_TABLE_SQL)
        self.conn.execute(_CREATE_INDEX_SQL)
        self.conn.commit()

    def insert(self, reading: PVReading) -> None:
        """Append one reading as a new row.

        Args:
            reading: A cleaned :class:`PVReading` with power values in W.
        """
        self.conn.execute(
            "INSERT INTO readings "
            "(timestamp, pv_power, consumption_power, grid_import_power) "
            "VALUES (?, ?, ?, ?)",
            (
                reading.timestamp.isoformat(),
                reading.pv_power,
                reading.consumption_power,
                reading.grid_import_power,
            ),
        )
        self.conn.commit()

    def query_range(self, start: datetime, end: datetime) -> list[PVReading]:
        """Return readings in the half-open interval ``[start, end)``.

        Args:
            start: Inclusive lower bound (UTC).
            end: Exclusive upper bound (UTC).

        Returns:
            list[PVReading]: Matching readings, oldest first; empty if none.
        """
        cursor = self.conn.execute(
            "SELECT timestamp, pv_power, consumption_power, grid_import_power "
            "FROM readings WHERE timestamp >= ? AND timestamp < ? "
            "ORDER BY timestamp",
            (start.isoformat(), end.isoformat()),
        )
        return [self._row_to_reading(row) for row in cursor.fetchall()]

    def latest(self) -> PVReading | None:
        """Return the most recent reading, or ``None`` if the table is empty.

        Returns:
            PVReading | None: The newest reading, or ``None`` when no rows
            exist yet.
        """
        row = self.conn.execute(
            "SELECT timestamp, pv_power, consumption_power, grid_import_power "
            "FROM readings ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return self._row_to_reading(row)

    def close(self) -> None:
        """Close the underlying database connection."""
        self.conn.close()

    def _row_to_reading(self, row: tuple) -> PVReading:
        """Convert a database row tuple into a :class:`PVReading`.

        Args:
            row: A ``(timestamp, pv_power, consumption_power,
                grid_import_power)`` tuple as returned by a SELECT.

        Returns:
            PVReading: The reconstructed reading.
        """
        return PVReading(
            timestamp=datetime.fromisoformat(row[0]),
            pv_power=row[1],
            consumption_power=row[2],
            grid_import_power=row[3],
        )