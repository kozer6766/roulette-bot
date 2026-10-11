
import json
import sqlite3
from datetime import datetime

DB_PATH = "roulette.db"

RED_NUMBERS = {
    1, 3, 5, 7, 9, 12, 14, 16, 18,
    19, 21, 23, 25, 27, 30, 32, 34, 36,
}


def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS spins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                number INTEGER NOT NULL,
                color TEXT NOT NULL,
                user_id INTEGER,
                timestamp TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                candidates TEXT NOT NULL,
                method TEXT NOT NULL DEFAULT 'unknown',
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                actual_number INTEGER,
                hit INTEGER,
                evaluated_at TEXT
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_predictions_user_status
            ON predictions (user_id, status)
        """)


def get_color(number):
    number = int(number)

    if not 0 <= number <= 36:
        raise ValueError("Число должно быть от 0 до 36.")

    if number == 0:
        return "green"

    return "red" if number in RED_NUMBERS else "black"


def add_spin(number, user_id=None):
    number = int(number)

    if not 0 <= number <= 36:
        raise ValueError("Число должно быть от 0 до 36.")

    color = get_color(number)
    now = datetime.now().isoformat(timespec="seconds")

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO spins (number, color, user_id, timestamp)
            VALUES (?, ?, ?, ?)
        """, (number, color, user_id, now))

        # Проверяем сохранённые прогнозы этого пользователя.
        if user_id is not None:
            pending = conn.execute("""
                SELECT id, candidates
                FROM predictions
                WHERE user_id = ? AND status = 'pending'
            """, (user_id,)).fetchall()

            for prediction in pending:
                try:
                    candidates = json.loads(
                        prediction["candidates"]
                    )
                    hit = int(number in candidates)
                except (TypeError, ValueError, json.JSONDecodeError):
                    hit = 0

                conn.execute("""
                    UPDATE predictions
                    SET status = 'evaluated',
                        actual_number = ?,
                        hit = ?,
                        evaluated_at = ?
                    WHERE id = ?
                """, (
                    number,
                    hit,
                    now,
                    prediction["id"],
                ))

    return color


def save_prediction(user_id, candidates, method="unknown"):
    if user_id is None:
        raise ValueError("Для прогноза нужен user_id.")

    cleaned = []

    for value in candidates:
        if isinstance(value, dict):
            value = value.get("number")

        if value is None:
            continue

        number = int(value)

        if 0 <= number <= 36 and number not in cleaned:
            cleaned.append(number)

    if not cleaned:
        raise ValueError("Список кандидатов пуст.")

    now = datetime.now().isoformat(timespec="seconds")

    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO predictions (
                user_id, candidates, method, created_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            int(user_id),
            json.dumps(cleaned),
            str(method),
            now,
        ))

        return cursor.lastrowid


def get_prediction_stats(user_id):
    with get_connection() as conn:
        counts = conn.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(
                    CASE WHEN status = 'evaluated'
                    THEN 1 ELSE 0 END
                ) AS evaluated,
                SUM(
                    CASE WHEN status = 'evaluated' AND hit = 1
                    THEN 1 ELSE 0 END
                ) AS hits,
                SUM(
                    CASE WHEN status = 'evaluated' AND hit = 0
                    THEN 1 ELSE 0 END
                ) AS misses,
                SUM(
                    CASE WHEN status = 'pending'
                    THEN 1 ELSE 0 END
                ) AS pending
            FROM predictions
            WHERE user_id = ?
        """, (user_id,)).fetchone()

        recent_rows = conn.execute("""
            SELECT id, candidates, method, created_at, status,
                   actual_number, hit, evaluated_at
            FROM predictions
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 10
        """, (user_id,)).fetchall()

    total = int(counts["total"] or 0)
    evaluated = int(counts["evaluated"] or 0)
    hits = int(counts["hits"] or 0)
    misses = int(counts["misses"] or 0)
    pending = int(counts["pending"] or 0)

    hit_rate = hits / evaluated * 100 if evaluated else 0.0

    recent = []

    for row in recent_rows:
        item = dict(row)

        try:
            item["candidates"] = json.loads(item["candidates"])
        except (TypeError, ValueError, json.JSONDecodeError):
            item["candidates"] = []

        recent.append(item)

    return {
        "total": total,
        "evaluated": evaluated,
        "hits": hits,
        "misses": misses,
        "pending": pending,
        "hit_rate": round(hit_rate, 2),
        "recent": recent,
    }


def get_all_spins():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT number, color, timestamp
            FROM spins
            ORDER BY id DESC
        """).fetchall()

    return [
        (row["number"], row["color"], row["timestamp"])
        for row in rows
    ]


def get_last_spins(limit=10):
    limit = max(0, int(limit))

    with get_connection() as conn:
        rows = conn.execute("""
            SELECT number, color
            FROM spins
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()

    return [
        (row["number"], row["color"])
        for row in rows
    ]


def clear_spins():
    with get_connection() as conn:
        conn.execute("DELETE FROM spins")
        conn.execute("DELETE FROM predictions")

