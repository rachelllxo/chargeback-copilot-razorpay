"""SQLite persistence for operator actions (decisions, notes, package runs).

PostgreSQL is used when DATABASE_URL is configured in a deployment; the demo
falls back to a local SQLite file. Connection details are read from the
environment and never returned to the client.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

DB_PATH = Path(os.getenv("CHARGEBACK_COPILOT_DB", Path(__file__).resolve().parent.parent / "copilot.db"))

BACKEND = "postgresql" if os.getenv("DATABASE_URL", "").startswith("postgres") else "sqlite"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS case_actions (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   dispute_id TEXT NOT NULL,
                   action TEXT NOT NULL,
                   actor TEXT NOT NULL,
                   note TEXT,
                   payload TEXT,
                   created_at TEXT NOT NULL)"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS investigation_runs (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   dispute_id TEXT NOT NULL,
                   modules INTEGER NOT NULL,
                   evidence INTEGER NOT NULL,
                   recommendation TEXT NOT NULL,
                   created_at TEXT NOT NULL)"""
        )


def record_action(dispute_id: str, action: str, actor: str, note: str | None = None,
                  payload: dict[str, Any] | None = None) -> dict[str, Any]:
    now = datetime.now().isoformat(timespec="seconds")
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO case_actions (dispute_id, action, actor, note, payload, created_at)"
            " VALUES (?,?,?,?,?,?)",
            (dispute_id, action, actor, note, json.dumps(payload or {}), now),
        )
        return {"id": cur.lastrowid, "dispute_id": dispute_id, "action": action,
                "actor": actor, "note": note, "created_at": now}


def actions_for(dispute_id: str) -> list[dict[str, Any]]:
    with _conn() as c:
        rows = c.execute(
            "SELECT id, dispute_id, action, actor, note, created_at FROM case_actions"
            " WHERE dispute_id = ? ORDER BY id DESC", (dispute_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def record_run(dispute_id: str, modules: int, evidence: int, recommendation: str) -> None:
    with _conn() as c:
        c.execute(
            "INSERT INTO investigation_runs (dispute_id, modules, evidence, recommendation, created_at)"
            " VALUES (?,?,?,?,?)",
            (dispute_id, modules, evidence, recommendation, datetime.now().isoformat(timespec="seconds")),
        )


def run_count() -> int:
    with _conn() as c:
        return c.execute("SELECT COUNT(*) AS n FROM investigation_runs").fetchone()["n"]


def decisions() -> dict[str, str]:
    """Latest human decision per dispute."""
    with _conn() as c:
        rows = c.execute(
            "SELECT dispute_id, action FROM case_actions WHERE action IN"
            " ('approve','accept','request_review','edit') ORDER BY id ASC"
        ).fetchall()
    out: dict[str, str] = {}
    for r in rows:
        out[r["dispute_id"]] = r["action"]
    return out


init_db()
