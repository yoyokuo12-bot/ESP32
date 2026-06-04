"""L2 儲存層：SQLite 落地 telemetry 並查詢近期視窗。"""
from __future__ import annotations

import json
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

CREATE TABLE IF NOT EXISTS diaries (
    node   TEXT    NOT NULL,
    ts     INTEGER NOT NULL,
    state  TEXT    NOT NULL,
    diary  TEXT    NOT NULL,
    stats  TEXT,
    PRIMARY KEY (node, ts)
);
CREATE INDEX IF NOT EXISTS idx_diary_node_ts ON diaries(node, ts);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    # 舊 DB 遷移：若 diaries 缺 stats 欄位則補上
    cols = [r[1] for r in conn.execute("PRAGMA table_info(diaries)").fetchall()]
    if "stats" not in cols:
        conn.execute("ALTER TABLE diaries ADD COLUMN stats TEXT")
        conn.commit()
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


def recent_by_count(conn: sqlite3.Connection, node: str, limit: int = 60) -> list[dict]:
    """取最近 limit 筆 telemetry（回傳依時間遞增）。"""
    cur = conn.execute(
        "SELECT * FROM telemetry WHERE node = ? ORDER BY ts DESC LIMIT ?",
        (node, int(limit)),
    )
    return list(reversed([dict(r) for r in cur.fetchall()]))


def nodes(conn: sqlite3.Connection) -> list[str]:
    cur = conn.execute("SELECT DISTINCT node FROM telemetry ORDER BY node")
    return [r["node"] for r in cur.fetchall()]


def insert_diary(conn: sqlite3.Connection, pkt: dict) -> None:
    """pkt = {node, ts, state, diary, (stats)}（L3 輸出，stats 選填）。"""
    stats = pkt.get("stats")
    conn.execute(
        "INSERT OR REPLACE INTO diaries (node, ts, state, diary, stats) VALUES (?, ?, ?, ?, ?)",
        (pkt["node"], int(pkt["ts"]), pkt["state"], pkt["diary"],
         json.dumps(stats, ensure_ascii=False) if stats is not None else None),
    )
    conn.commit()


def recent_diaries(conn: sqlite3.Connection, node: str | None = None,
                   limit: int = 50) -> list[dict]:
    """最新在前。"""
    if node:
        cur = conn.execute(
            "SELECT * FROM diaries WHERE node = ? ORDER BY ts DESC LIMIT ?",
            (node, int(limit)),
        )
    else:
        cur = conn.execute("SELECT * FROM diaries ORDER BY ts DESC LIMIT ?", (int(limit),))
    rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        if r.get("stats"):
            try:
                r["stats"] = json.loads(r["stats"])
            except Exception:
                r["stats"] = None
    return rows
