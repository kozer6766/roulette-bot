import sqlite3
import json
from datetime import datetime

DB_PATH = "roulette.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Существующая таблица сохраняется без удаления старых записей.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS spins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number INTEGER NOT NULL,
            color TEXT NOT NULL,
            user_id INTEGER,
            timestamp TEXT
        )
    """)

    # Таблица для сохранённых прогнозов.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            candidates TEXT NOT NULL,
            method TEXT,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            actual_number INTEGER,
            hit INTEGER,
            evaluated_at TEXT
        )
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_predictions_user_status
        ON predictions (user_id, status)
    """)

    conn.commit()
    conn.close()


def get_color(number):
    if number == 0:
        return "green"

    red_numbers = {
        1, 3, 5, 7, 9, 12, 14, 16, 18,
        19, 21, 23, 25, 27, 30, 32, 34, 36
    }

    return "red" if number in red_numbers else "black"


def add_spin(number, user_id):
    if not isinstance(number, int) or not 0 <= number <= 36:
        raise ValueError("Число рулетки должно быть от 0 до 36.")

    color = get_color(number)
    now = datetime.now().isoformat()

    conn = get_connection()
    cur = conn.cursor()

    # Записываем новый результат.
    cur.execute(
        """
        INSERT INTO spins (number, color, user_id, timestamp)
        VALUES (?, ?, ?, ?)
        """,
        (number, color, user_id, now)
    )

    # Проверяем все сохранённые прогнозы этого пользователя,
    # ожидающие следующего результата.
    if user_id is not None:
        cur.execute(
            """
            SELECT id, candidates
            FROM predictions
            WHERE user_id = ? AND status = 'pending'
            """,
            (user_id,)
        )
        
        pending_predictions = cur.fetchall()

        for prediction in pending_predictions:
            try:
                candidates = json.loads(prediction["candidates"])
                hit = int(number in candidates)
            except (ValueError, TypeError, json.JSONDecodeError):
                # Не оцениваем запись с повреждённым списком чисел.
                continue

            cur.execute(
                """
                UPDATE predictions
                SET status = 'evaluated',
                    actual_number = ?,
                    hit = ?,
                    evaluated_at = ?
                WHERE id = ? AND status = 'pending'
                """,
                (number, hit, now, prediction["id"])
            )

    conn.commit()
    conn.close()

    return color


def save_prediction(user_id, candidates, method="unknown"):
    if user_id is None:
        raise ValueError("Не удалось определить пользователя.")

    # Оставляем только уникальные целые числа в диапазоне 0–36.
    clean_candidates = []
    for number in candidates:
        if (
            isinstance(number, int)
            and not isinstance(number, bool)
            and 0 <= number <= 36
            and number not in clean_candidates
        ):
            clean_candidates.append(number)

    if not clean_candidates:
        raise ValueError("Список кандидатов пуст.")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO predictions
            (user_id, candidates, method, created_at, status)
        VALUES (?, ?, ?, ?, 'pending')
        """,
        (
            user_id,
            json.dumps(clean_candidates),
            str(method),
            datetime.now().isoformat()
        )
    )

prediction_id = cur.lastrowid
    conn.commit()
    conn.close()

    return prediction_id


def get_prediction_stats(user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            COUNT(*) AS total,
            COALESCE(SUM(CASE WHEN hit = 1 THEN 1 ELSE 0 END), 0) AS hits,
            COALESCE(SUM(CASE WHEN hit = 0 THEN 1 ELSE 0 END), 0) AS misses,
            COALESCE(SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END), 0)
                AS pending
        FROM predictions
        WHERE user_id = ?
        """,
        (user_id,)
    )

    row = cur.fetchone()
    total = row["total"]
    hits = row["hits"]
    misses = row["misses"]
    pending = row["pending"]
    evaluated = hits + misses

    cur.execute(
        """
        SELECT candidates, method, created_at, actual_number, hit, status
        FROM predictions
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 10
        """,
        (user_id,)
    )

    recent_rows = cur.fetchall()
    conn.close()

    recent = []
    for item in recent_rows:
        recent.append({
            "candidates": json.loads(item["candidates"]),
            "method": item["method"],
            "created_at": item["created_at"],
            "actual_number": item["actual_number"],
            "hit": item["hit"],
            "status": item["status"]
        })

    return {
        "total": total,
        "evaluated": evaluated,
        "hits": hits,
        "misses": misses,
        "pending": pending,
        "hit_rate": round(hits / evaluated * 100, 1) if evaluated else 0.0,
        "recent": recent
    }


def get_all_spins():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT number, color, timestamp FROM spins ORDER BY id DESC"
    )

    rows = cur.fetchall()
    result = [tuple(row) for row in rows]
    conn.close()

    return result


def get_last_spins(limit=10):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT number, color
        FROM spins
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,)
    )

    rows = cur.fetchall()
    result = [tuple(row) for row in rows]
    conn.close()

    return result


def clear_spins():
    conn = get_connection()
    cur = conn.cursor()

    # Очищаем результаты и историю проверки прогнозов.
    cur.execute("DELETE FROM spins")
    cur.execute("DELETE FROM predictions")

    conn.commit()
    conn.close()
