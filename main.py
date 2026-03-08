from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("DB_PATH", str(BASE_DIR / "data.db")))
STATIC_DIR = BASE_DIR / "static"
APP_TZ = ZoneInfo("Asia/Shanghai")

app = FastAPI(title="Simple Message Board", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ItemIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=5000)
    image: str = Field(default="", max_length=5000)
    timestamp: str = Field(..., min_length=1, max_length=64)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                image TEXT NOT NULL,
                event_ts INTEGER NOT NULL,
                day TEXT NOT NULL,
                created_ts INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_items_day ON items(day)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_items_event_ts ON items(event_ts)"
        )
        conn.commit()


def parse_timestamp(raw_value: str) -> datetime:
    value = raw_value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="timestamp 必须是 ISO-8601 格式") from exc

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=APP_TZ)
    return dt.astimezone(timezone.utc)


def prune_old_data(conn: sqlite3.Connection) -> None:
    cutoff = int((datetime.now(timezone.utc) - timedelta(days=7)).timestamp())
    conn.execute("DELETE FROM items WHERE event_ts < ?", (cutoff,))
    conn.commit()


def to_local_iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(APP_TZ).isoformat()


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    with get_conn() as conn:
        prune_old_data(conn)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/items")
def create_item(item: ItemIn) -> dict:
    event_utc = parse_timestamp(item.timestamp)
    now_utc = datetime.now(timezone.utc)
    if event_utc < now_utc - timedelta(days=7):
        raise HTTPException(status_code=400, detail="仅允许写入最近 7 天内的数据")

    event_ts = int(event_utc.timestamp())
    day_text = event_utc.astimezone(APP_TZ).date().isoformat()
    created_ts = int(now_utc.timestamp())

    with get_conn() as conn:
        prune_old_data(conn)
        cur = conn.execute(
            """
            INSERT INTO items(title, content, image, event_ts, day, created_ts)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (item.title.strip(), item.content.strip(), item.image.strip(), event_ts, day_text, created_ts),
        )
        conn.commit()

    return {"ok": True, "id": cur.lastrowid}


@app.get("/api/days")
def get_days() -> dict:
    with get_conn() as conn:
        prune_old_data(conn)
        rows = conn.execute(
            "SELECT DISTINCT day FROM items ORDER BY day DESC"
        ).fetchall()
    return {"days": [row["day"] for row in rows]}


@app.get("/api/items")
def get_items(day: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")) -> dict:
    with get_conn() as conn:
        prune_old_data(conn)
        selected_day = day
        if not selected_day:
            row = conn.execute(
                "SELECT day FROM items ORDER BY day DESC LIMIT 1"
            ).fetchone()
            if not row:
                return {"day": None, "items": []}
            selected_day = row["day"]

        rows = conn.execute(
            """
            SELECT id, title, content, image, event_ts
            FROM items
            WHERE day = ?
            ORDER BY event_ts DESC, id DESC
            """,
            (selected_day,),
        ).fetchall()

    return {
        "day": selected_day,
        "items": [
            {
                "id": row["id"],
                "title": row["title"],
                "content": row["content"],
                "image": row["image"],
                "timestamp": to_local_iso(row["event_ts"]),
            }
            for row in rows
        ],
    }
