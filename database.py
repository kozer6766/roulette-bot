import sqlite3
from datetime import datetime

DB_PATH = "roulette.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS spins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number INTEGER NOT NULL,
            color TEXT NOT NULL,
            user_id INTEGER,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()


def get_color(number):
    if number == 0:
        return "green"
    red_numbers = {1, 3, 5, 7, 9, 12, 14, 16, 18,
                   19, 21, 23, 25, 27, 30, 32, 34, 36}
    return "red" if number in red_numbers else "black"


def add_spin(number, user_id):
    color = get_color(number)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO spins (number, color, user_id, timestamp) VALUES (?, ?, ?, ?)",
        (number, color, user_id, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    return color


def get_all_spins():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT number, color, timestamp FROM spins ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_last_spins(limit=10):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT number, color FROM spins ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def clear_spins():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM spins")
    conn.commit()
    conn.close()