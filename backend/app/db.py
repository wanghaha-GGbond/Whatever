"""
数据库持久化层。

优先使用 DATABASE_URL（PostgreSQL / Render Postgres），未配置时回退到本地 SQLite。
保持原有函数签名，便于 routes.py 直接复用。
"""

import json
import os
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import Integer, String, Text, create_engine, func, inspect, select, text
from sqlalchemy.orm import Mapped, Session, declarative_base, mapped_column, sessionmaker

Base = declarative_base()


def _normalize_database_url(url: str) -> str:
    raw = url.strip()
    if raw.startswith("postgres://"):
        return "postgresql+psycopg://" + raw[len("postgres://"):]
    if raw.startswith("postgresql://") and "+" not in raw.split("://", 1)[0]:
        return "postgresql+psycopg://" + raw[len("postgresql://"):]
    return raw


def _build_engine():
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        normalized = _normalize_database_url(database_url)
        return create_engine(normalized, pool_pre_ping=True)

    app_env = (os.getenv("APP_ENV") or "").strip().lower()
    if app_env in {"production", "prod"}:
        raise RuntimeError("DATABASE_URL is required in production environment")

    db_path = Path(os.getenv("DB_PATH", Path(__file__).parent.parent / "data" / "p003.db"))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )


_ENGINE = _build_engine()
SessionLocal = sessionmaker(bind=_ENGINE, autoflush=False, autocommit=False, expire_on_commit=False)


class SessionRow(Base):
    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    prompt: Mapped[str] = mapped_column(Text, default="")
    intent: Mapped[str] = mapped_column(Text, default="{}")
    location: Mapped[str] = mapped_column(Text, default="")
    address_name: Mapped[str] = mapped_column(Text, default="")
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    candidates: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[str] = mapped_column(Text, default="")


class PickRow(Base):
    __tablename__ = "picks"

    pick_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    picked: Mapped[str] = mapped_column(Text)


class HistoryRow(Base):
    __tablename__ = "history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    pick_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[str] = mapped_column(Text)
    conditions: Mapped[str] = mapped_column(Text)
    satisfaction: Mapped[int] = mapped_column(Integer)
    went: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[str] = mapped_column(Text, default="[]")
    actual_cost: Mapped[int | None] = mapped_column(Integer, nullable=True)
    transport_used: Mapped[str] = mapped_column(String(64), nullable=True)


class UserPrefRow(Base):
    __tablename__ = "user_prefs"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    budget_avg: Mapped[int | None] = mapped_column(Integer, nullable=True)
    transport: Mapped[str | None] = mapped_column(String(64), nullable=True)
    type_weights: Mapped[str] = mapped_column(Text, default="{}")
    top_persona: Mapped[str | None] = mapped_column(String(64), nullable=True)
    visit_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[str | None] = mapped_column(Text, nullable=True)


class EventRow(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_name: Mapped[str] = mapped_column(String(128), index=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    properties: Mapped[str] = mapped_column(Text, default="{}")
    ts: Mapped[str] = mapped_column(Text, index=True)


def init_db() -> None:
    Base.metadata.create_all(_ENGINE)
    _ensure_legacy_columns()


def _ensure_legacy_columns() -> None:
    insp = inspect(_ENGINE)

    def has_column(table: str, column: str) -> bool:
        try:
            cols = insp.get_columns(table)
        except Exception:
            return False
        return any(c.get("name") == column for c in cols)

    with _ENGINE.begin() as conn:
        if has_column("picks", "pick_id") and not has_column("picks", "user_id"):
            conn.execute(text("ALTER TABLE picks ADD COLUMN user_id TEXT"))

        if has_column("history", "id") and not has_column("history", "user_id"):
            conn.execute(text("ALTER TABLE history ADD COLUMN user_id TEXT"))
        if has_column("history", "id") and not has_column("history", "went"):
            conn.execute(text("ALTER TABLE history ADD COLUMN went INTEGER DEFAULT 1"))
        if has_column("history", "id") and not has_column("history", "title"):
            conn.execute(text("ALTER TABLE history ADD COLUMN title TEXT DEFAULT ''"))
        if has_column("history", "id") and not has_column("history", "content"):
            conn.execute(text("ALTER TABLE history ADD COLUMN content TEXT DEFAULT ''"))
        if has_column("history", "id") and not has_column("history", "tags"):
            conn.execute(text("ALTER TABLE history ADD COLUMN tags TEXT DEFAULT '[]'"))
        if has_column("history", "id") and not has_column("history", "actual_cost"):
            conn.execute(text("ALTER TABLE history ADD COLUMN actual_cost INTEGER"))
        if has_column("history", "id") and not has_column("history", "transport_used"):
            conn.execute(text("ALTER TABLE history ADD COLUMN transport_used TEXT"))


@contextmanager
def _session_scope():
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _loads_json(raw: str | None, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


# ─── Sessions ────────────────────────────────────────────────────────────────

def session_set(session_id: str, data: dict) -> None:
    with _session_scope() as db:
        row = db.get(SessionRow, session_id)
        if not row:
            row = SessionRow(session_id=session_id)
        row.prompt = data.get("prompt", "")
        row.intent = json.dumps(data.get("intent", {}), ensure_ascii=False)
        row.location = data.get("location", "")
        row.address_name = data.get("address_name", "")
        row.user_id = data.get("user_id")
        row.candidates = json.dumps(data.get("candidates", []), ensure_ascii=False)
        row.created_at = data.get("created_at", "")
        db.add(row)


def session_get(session_id: str) -> dict | None:
    with _session_scope() as db:
        row = db.get(SessionRow, session_id)
        if not row:
            return None
        return {
            "prompt": row.prompt,
            "intent": _loads_json(row.intent, {}),
            "location": row.location,
            "address_name": row.address_name,
            "user_id": row.user_id,
            "candidates": _loads_json(row.candidates, []),
            "created_at": row.created_at,
        }


def session_set_candidates(session_id: str, candidates: list) -> None:
    with _session_scope() as db:
        row = db.get(SessionRow, session_id)
        if not row:
            return
        row.candidates = json.dumps(candidates, ensure_ascii=False)
        db.add(row)


# ─── Picks ───────────────────────────────────────────────────────────────────

def pick_set(pick_id: str, session_id: str, picked: dict) -> None:
    with _session_scope() as db:
        row = db.get(PickRow, pick_id)
        if not row:
            row = PickRow(pick_id=pick_id, session_id=session_id, picked="{}")

        session_row = db.get(SessionRow, session_id)
        row.session_id = session_id
        row.user_id = session_row.user_id if session_row else None
        row.picked = json.dumps(picked, ensure_ascii=False)
        db.add(row)


def pick_get(pick_id: str) -> dict | None:
    with _session_scope() as db:
        row = db.get(PickRow, pick_id)
        if not row:
            return None
        return {
            "session_id": row.session_id,
            "picked": _loads_json(row.picked, {}),
        }


# ─── History ─────────────────────────────────────────────────────────────────

def history_insert(
    pick_id: str,
    name: str,
    timestamp: str,
    conditions: str,
    satisfaction: int,
    user_id: str | None = None,
    went: bool = True,
    title: str = "",
    content: str = "",
    tags: list[str] | None = None,
    actual_cost: int | None = None,
    transport_used: str | None = None,
) -> None:
    tags_json = json.dumps(tags or [], ensure_ascii=False)
    with _session_scope() as db:
        db.add(
            HistoryRow(
                user_id=user_id,
                pick_id=pick_id,
                name=name,
                timestamp=timestamp,
                conditions=conditions,
                satisfaction=satisfaction,
                went=1 if went else 0,
                title=title,
                content=content,
                tags=tags_json,
                actual_cost=actual_cost,
                transport_used=transport_used,
            )
        )


def history_list(page: int = 1, page_size: int = 20, user_id: str | None = None) -> tuple[list[dict], int]:
    offset = max(0, (page - 1) * page_size)
    with _session_scope() as db:
        q = select(HistoryRow)
        q_count = select(func.count()).select_from(HistoryRow)

        if user_id:
            q = q.where(HistoryRow.user_id == user_id)
            q_count = q_count.where(HistoryRow.user_id == user_id)

        q = q.order_by(HistoryRow.id.desc()).limit(page_size).offset(offset)

        total = int(db.execute(q_count).scalar_one())
        rows = db.execute(q).scalars().all()

        items = [
            {
                "pick_id": r.pick_id,
                "name": r.name,
                "timestamp": r.timestamp,
                "conditions": r.conditions,
                "satisfaction": r.satisfaction,
                "went": bool(r.went),
                "title": r.title,
                "content": r.content,
                "tags": _loads_json(r.tags, []),
                "actual_cost": r.actual_cost,
                "transport_used": r.transport_used,
            }
            for r in rows
        ]
        return items, total


# ─── User Preferences ─────────────────────────────────────────────────────────

def prefs_get(user_id: str) -> dict | None:
    with _session_scope() as db:
        row = db.get(UserPrefRow, user_id)
        if not row:
            return None
        return {
            "budget_avg": row.budget_avg,
            "transport": row.transport,
            "type_weights": _loads_json(row.type_weights, {}),
            "top_persona": row.top_persona,
            "visit_count": row.visit_count,
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
        "budget_avg": None,
        "transport": None,
        "type_weights": {},
        "top_persona": None,
        "visit_count": 0,
    }

    if transport:
        prefs["transport"] = transport
    if budget is not None:
        prefs["budget_avg"] = (
            budget
            if prefs["budget_avg"] is None
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

    with _session_scope() as db:
        row = db.get(UserPrefRow, user_id)
        if not row:
            row = UserPrefRow(user_id=user_id)
        row.budget_avg = prefs["budget_avg"]
        row.transport = prefs["transport"]
        row.type_weights = json.dumps(prefs["type_weights"], ensure_ascii=False)
        row.top_persona = prefs["top_persona"]
        row.visit_count = prefs["visit_count"]
        row.updated_at = datetime.now().isoformat()
        db.add(row)


# ─── Events ───────────────────────────────────────────────────────────────────

def events_insert_batch(events: list[dict]) -> None:
    with _session_scope() as db:
        for e in events:
            db.add(
                EventRow(
                    event_name=e.get("event_name", ""),
                    session_id=e.get("session_id"),
                    user_id=e.get("user_id"),
                    properties=json.dumps(e.get("properties", {}), ensure_ascii=False),
                    ts=e.get("ts", datetime.now().isoformat()),
                )
            )


def dashboard_metrics(days: int = 7) -> dict:
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    with _session_scope() as db:
        def count(event_name: str, distinct_session: bool = False) -> int:
            if distinct_session:
                q = select(func.count(func.distinct(EventRow.session_id))).where(
                    EventRow.event_name == event_name,
                    EventRow.ts >= cutoff,
                )
            else:
                q = select(func.count()).select_from(EventRow).where(
                    EventRow.event_name == event_name,
                    EventRow.ts >= cutoff,
                )
            return int(db.execute(q).scalar_one())

        sessions = count("session_start")
        picks = count("pick_drawn")
        nav = count("nav_clicked")
        redraw = count("redraw_clicked")
        persona = count("persona_tab_clicked", distinct_session=True)
        feedback = count("feedback_submitted")
        total_hist = int(db.execute(select(func.count()).select_from(HistoryRow)).scalar_one())

    def rate(n, d):
        return round(n / d, 4) if d else None

    return {
        "period_days": days,
        "sessions": sessions,
        "picks": picks,
        "completion_rate": rate(picks, sessions),
        "nav_rate": rate(nav, picks),
        "redraw_rate": rate(redraw, picks),
        "persona_rate": rate(persona, picks),
        "feedback_rate": rate(feedback, picks),
        "total_history": total_hist,
    }
