import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "wcigami.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    # Stores every historical WC goal-minute fingerprint occurrence
    c.execute("""
        CREATE TABLE IF NOT EXISTS fingerprints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fingerprint TEXT NOT NULL,
            match_date TEXT NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            score TEXT NOT NULL,
            year INTEGER NOT NULL
        )
    """)

    # Tracks which 2026 matches have already been tweeted
    c.execute("""
        CREATE TABLE IF NOT EXISTS tweeted_matches (
            fixture_id INTEGER PRIMARY KEY,
            tweeted_at TEXT NOT NULL
        )
    """)

    c.execute("CREATE INDEX IF NOT EXISTS idx_fingerprint ON fingerprints(fingerprint)")

    conn.commit()
    conn.close()
    print("Database initialised.")


def insert_fingerprint(fingerprint, match_date, home_team, away_team, score, year):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO fingerprints (fingerprint, match_date, home_team, away_team, score, year)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (fingerprint, match_date, home_team, away_team, score, year))
    conn.commit()
    conn.close()


def lookup_fingerprint(fingerprint):
    """
    Returns a dict with:
      - count: how many times this fingerprint has occurred
      - most_recent: the most recent occurrence (Row) or None
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM fingerprints
        WHERE fingerprint = ?
        ORDER BY match_date DESC
    """, (fingerprint,))
    rows = c.fetchall()
    conn.close()
    return {
        "count": len(rows),
        "most_recent": rows[0] if rows else None
    }


def mark_tweeted(fixture_id):
    from datetime import datetime, timezone
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO tweeted_matches (fixture_id, tweeted_at)
        VALUES (?, ?)
    """, (fixture_id, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    conn.close()


def already_tweeted(fixture_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT 1 FROM tweeted_matches WHERE fixture_id = ?", (fixture_id,))
    row = c.fetchone()
    conn.close()
    return row is not None
