"""
database.py
------------
Tiny SQLite wrapper. Keeping this in plain SQL (no ORM) on purpose:
the project only needs 3 tables, and it's easier to explain in the
code walkthrough / oral exam if there's no ORM magic hiding the queries.
"""

import sqlite3
from contextlib import contextmanager

DB_PATH = "study_bot.db"


def init_db():
    """Create tables if they don't exist yet. Called once at startup."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                subject TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role TEXT NOT NULL,          -- 'user' or 'assistant'
                content TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)
        conn.commit()


@contextmanager
def get_conn():
    """Context manager so every query auto-closes its connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
