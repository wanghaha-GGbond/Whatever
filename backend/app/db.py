"""
SQLite 持久化层（替换内存存储）。
数据库文件默认放在 backend/data/p003.db，通过 DB_PATH 环境变量覆盖。
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

_DB_PATH = Path(os.getenv("DB_PATH", Path(__file__).parent.parent / "data" / "p003.db"))


def init_db() -> None:
    """建表（幂等）。"""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id   TEXT PRIMARY KEY,
                prompt       TEXT,
                intent       TEXT,   -- JSON
                location     TEXT,
                address_name TEXT,
                user_id      TEXT,
                candidates   TEXT,   -- JSON array，candidates 存入后更新
                created_at   TEXT
            );

            CREATE TABLE IF NOT EXISTS picks (
                pick_id    TEXT PRIMARY KEY,
                session_id TEXT,
                picked     TEXT    -- JSON
            );

            CREATE TABLE IF NOT EXISTS history (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                pick_id      TEXT,
                name         TEXT,
                timestamp    TEXT,
                conditions   TEXT,
                satisfaction INTEGER
            );

            CREATE TABLE IF NOT EXISTS user_prefs (
                user_id      TEXT PRIMARY KEY,
                budget_avg   INTEGER,
                transport    TEXT,
                type_weights TEXT,
                top_persona  TEXT,
                visit_count  INTEGER DEFAULT 0,
                updated_at   TEXT
            );

            CREATE TABLE IF NOT EXISTS events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                event_name  TEXT NOT NULL,
                session_id  TEXT,
                user_id     TEXT,
                properties  TEXT,
                ts          TEXT NOT NULL
            );
        """)


@contextmanager
def _connect():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ─── Sessions ────────────────────────────────────────────────────────────────

def session_set(session_id: str, data: dict) -> None:
    with _connect() as conn:
        conn.execute("""
            INSERT INTO sessions (session_id, prompt, intent, location, address_name, user_id, candidates, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                prompt=excluded.prompt, intent=excluded.intent,
                location=excluded.location, address_name=excluded.address_name,
                user_id=excluded.user_id, candidates=excluded.candidates,
                created_at=excluded.created_at
        """, (
            session_id,
            data.get("prompt", ""),
            json.dumps(data.get("intent", {}), ensure_ascii=False),
            data.get("location", ""),
            data.get("address_name", ""),
            data.get("user_id"),
            json.dumps(data.get("candidates", []), ensure_ascii=False),
            data.get("created_at", ""),
        ))


def session_get(session_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
    if not row:
        return None
    return {
        "prompt":       row["prompt"],
        "intent":       json.loads(row["intent"] or "{}"),
        "location":     row["location"],
        "address_name": row["address_name"],
        "user_id":      row["user_id"],
        "candidates":   json.loads(row["candidates"] or "[]"),
        "created_at":   row["created_at"],
    }


def session_set_candidates(session_id: str, candidates: list) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE sessions SET candidates = ? WHERE session_id = ?",
            (json.dumps(candidates, ensure_ascii=False), session_id),
        )


# ─── Picks ───────────────────────────────────────────────────────────────────

def pick_set(pick_id: str, session_id: str, picked: dict) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO picks (pick_id, session_id, picked) VALUES (?, ?, ?)",
            (pick_id, session_id, json.dumps(picked, ensure_ascii=False)),
        )


def pick_get(pick_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM picks WHERE pick_id = ?", (pick_id,)
        ).fetchone()
    if not row:
        return None
    return {"session_id": row["session_id"], "picked": json.loads(row["picked"])}


# ─── History ─────────────────────────────────────────────────────────────────

def history_insert(pick_id: str, name: str, timestamp: str, conditions: str, satisfaction: int) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO history (pick_id, name, timestamp, conditions, satisfaction) VALUES (?, ?, ?, ?, ?)",
            (pick_id, name, timestamp, conditions, satisfaction),
        )


def history_list(page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
    offset = (page - 1) * page_size
    with _connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]
        rows = conn.execute(
            "SELECT pick_id, name, timestamp, conditions, satisfaction FROM history "
            "ORDER BY id DESC LIMIT ? OFFSET ?",
            (page_size, offset),
        ).fetchall()
    items = [dict(r) for r in rows]
    return items, total


# ─── User Preferences ─────────────────────────────────────────────────────────

def prefs_get(user_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM user_prefs WHERE user_id = ?", (user_id,)
        ).fetchone()
    if not row:
        return None
    return {
        "budget_avg":   row["budget_avg"],
        "transport":    row["transport"],
        "type_weights": json.loads(row["type_weights"] or "{}"),
        "top_persona":  row["top_persona"],
        "visit_count":  row["visit_count"],
    }


def prefs_update(
    user_id: str,
    *,
    transport: str | None = None,
    budget: int | None = None,
    poi_type: str | None = None,
    satisfaction: int = 3,
    persona: str | None = None,
) -> None:
    prefs = prefs_get(user_id) or {
        "budget_avg": None, "transport": None,
        "type_weights": {}, "top_persona": None, "visit_count": 0,
    }

    if transport:
        prefs["transport"] = transport
    if budget is not None:
        prefs["budget_avg"] = (
            budget if prefs["budget_avg"] is None
            else int(prefs["budget_avg"] * 0.7 + budget * 0.3)
        )
    if poi_type:
        tw = prefs["type_weights"]
        if satisfaction >= 4:
            tw[poi_type] = round(min(2.0, tw.get(poi_type, 1.0) + 0.15), 2)
        elif satisfaction <= 2:
            tw[poi_type] = round(max(0.3, tw.get(poi_type, 1.0) - 0.10), 2)
        prefs["type_weights"] = tw
    if persona:
        prefs["top_persona"] = persona
    prefs["visit_count"] = prefs.get("visit_count", 0) + 1

    with _connect() as conn:
        conn.execute("""
            INSERT INTO user_prefs (user_id, budget_avg, transport, type_weights, top_persona, visit_count, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                budget_avg=excluded.budget_avg, transport=excluded.transport,
                type_weights=excluded.type_weights, top_persona=excluded.top_persona,
                visit_count=excluded.visit_count, updated_at=excluded.updated_at
        """, (
            user_id,
            prefs["budget_avg"],
            prefs["transport"],
            json.dumps(prefs["type_weights"], ensure_ascii=False),
            prefs["top_persona"],
            prefs["visit_count"],
            datetime.now().isoformat(),
        ))


# ─── Events ───────────────────────────────────────────────────────────────────

def events_insert_batch(events: list[dict]) -> None:
    with _connect() as conn:
        conn.executemany(
            "INSERT INTO events (event_name, session_id, user_id, properties, ts) VALUES (?, ?, ?, ?, ?)",
            [
                (
                    e.get("event_name", ""),
                    e.get("session_id"),
                    e.get("user_id"),
                    json.dumps(e.get("properties", {}), ensure_ascii=False),
                    e.get("ts", datetime.now().isoformat()),
                )
                for e in events
            ],
        )


def dashboard_metrics(days: int = 7) -> dict:
    """计算最近 N 天的核心指标。"""
    from datetime import timedelta
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    with _connect() as conn:
        def count(event_name: str, distinct_session: bool = False) -> int:
            if distinct_session:
                return conn.execute(
                    "SELECT COUNT(DISTINCT session_id) FROM events WHERE event_name=? AND ts>=?",
                    (event_name, cutoff),
                ).fetchone()[0]
            return conn.execute(
                "SELECT COUNT(*) FROM events WHERE event_name=? AND ts>=?",
                (event_name, cutoff),
            ).fetchone()[0]

        sessions   = count("session_start")
        picks      = count("pick_drawn")
        nav        = count("nav_clicked")
        redraw     = count("redraw_clicked")
        persona    = count("persona_tab_clicked", distinct_session=True)
        feedback   = count("feedback_submitted")
        total_hist = conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]

    def rate(n, d):
        return round(n / d, 4) if d else None

    return {
        "period_days":        days,
        "sessions":           sessions,
        "picks":              picks,
        "completion_rate":    rate(picks, sessions),
        "nav_rate":           rate(nav, picks),
        "redraw_rate":        rate(redraw, picks),
        "persona_rate":       rate(persona, picks),
        "feedback_rate":      rate(feedback, picks),
        "total_history":      total_hist,
    }
