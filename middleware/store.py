"""L2 儲存層：SQLite 落地 telemetry 並查詢近期視窗。"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS telemetry (
    node          TEXT    NOT NULL,
    ts            INTEGER NOT NULL,
    moisture_raw  INTEGER,
    light_raw     INTEGER,
    temp_c        REAL,
    humidity_pct  REAL,
    sim           INTEGER DEFAULT 0,
    PRIMARY KEY (node, ts)
);
CREATE INDEX IF NOT EXISTS idx_node_ts ON telemetry(node, ts);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def insert(conn: sqlite3.Connection, rec: dict) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO telemetry "
        "(node, ts, moisture_raw, light_raw, temp_c, humidity_pct, sim) "
        "VALUES (:node, :ts, :moisture_raw, :light_raw, :temp_c, :humidity_pct, :sim)",
        {
            "node": rec["node"],
            "ts": int(rec["ts"]),
            "moisture_raw": rec.get("moisture_raw"),
            "light_raw": rec.get("light_raw"),
            "temp_c": rec.get("temp_c"),
            "humidity_pct": rec.get("humidity_pct"),
            "sim": 1 if rec.get("sim") else 0,
        },
    )
    conn.commit()


def recent(conn: sqlite3.Connection, node: str, since_ts: int) -> list[dict]:
    cur = conn.execute(
        "SELECT * FROM telemetry WHERE node = ? AND ts >= ? ORDER BY ts ASC",
        (node, int(since_ts)),
    )
    return [dict(r) for r in cur.fetchall()]
