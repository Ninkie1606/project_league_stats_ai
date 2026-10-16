"""SQLite storage for raw API responses.

Each row is committed immediately, so a crawl can be stopped at any moment
(Ctrl+C, expired key) and resumed without fetching anything twice.
"""
import json
import sqlite3
import time

from riot import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS players (
    puuid TEXT PRIMARY KEY,
    tier TEXT,
    division TEXT,
    league_points INTEGER,
    seeded_at REAL,
    ids_fetched_at REAL
);
CREATE TABLE IF NOT EXISTS matches (
    match_id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending | done | missing
    json TEXT,
    fetched_at REAL
);
CREATE TABLE IF NOT EXISTS timelines (
    match_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,                    -- done | missing
    json TEXT,
    fetched_at REAL
);
"""


class Storage:
    def __init__(self, path=config.DB_PATH):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.executescript(SCHEMA)

    # --- players ---

    def add_players(self, entries, tier, division):
        now = time.time()
        self.conn.executemany(
            "INSERT OR IGNORE INTO players (puuid, tier, division, league_points, seeded_at) "
            "VALUES (?, ?, ?, ?, ?)",
            [(e["puuid"], tier, division, e.get("leaguePoints"), now) for e in entries if e.get("puuid")],
        )
        self.conn.commit()

    def has_players(self, tier, division):
        row = self.conn.execute(
            "SELECT 1 FROM players WHERE tier = ? AND division = ? LIMIT 1", (tier, division)
        ).fetchone()
        return row is not None

    def next_player(self):
        """A random player whose match IDs haven't been fetched yet."""
        row = self.conn.execute(
            "SELECT puuid FROM players WHERE ids_fetched_at IS NULL ORDER BY RANDOM() LIMIT 1"
        ).fetchone()
        return row[0] if row else None

    def mark_player_done(self, puuid):
        self.conn.execute("UPDATE players SET ids_fetched_at = ? WHERE puuid = ?", (time.time(), puuid))
        self.conn.commit()

    # --- matches ---

    def add_match_ids(self, match_ids):
        cur = self.conn.executemany(
            "INSERT OR IGNORE INTO matches (match_id) VALUES (?)", [(m,) for m in match_ids]
        )
        self.conn.commit()
        return cur.rowcount

    def next_pending_match(self):
        row = self.conn.execute("SELECT match_id FROM matches WHERE status = 'pending' LIMIT 1").fetchone()
        return row[0] if row else None

    def save_match(self, match_id, data):
        status = "done" if data is not None else "missing"
        self.conn.execute(
            "UPDATE matches SET status = ?, json = ?, fetched_at = ? WHERE match_id = ?",
            (status, json.dumps(data) if data is not None else None, time.time(), match_id),
        )
        self.conn.commit()

    # --- timelines ---

    def next_match_without_timeline(self):
        row = self.conn.execute(
            "SELECT m.match_id FROM matches m LEFT JOIN timelines t USING (match_id) "
            "WHERE m.status = 'done' AND t.match_id IS NULL LIMIT 1"
        ).fetchone()
        return row[0] if row else None

    def save_timeline(self, match_id, data):
        status = "done" if data is not None else "missing"
        self.conn.execute(
            "INSERT OR REPLACE INTO timelines (match_id, status, json, fetched_at) VALUES (?, ?, ?, ?)",
            (match_id, status, json.dumps(data) if data is not None else None, time.time()),
        )
        self.conn.commit()

    # --- reading ---

    def stats(self):
        q = lambda sql: self.conn.execute(sql).fetchone()[0]
        return {
            "players": q("SELECT COUNT(*) FROM players"),
            "players_done": q("SELECT COUNT(*) FROM players WHERE ids_fetched_at IS NOT NULL"),
            "matches_done": q("SELECT COUNT(*) FROM matches WHERE status = 'done'"),
            "matches_pending": q("SELECT COUNT(*) FROM matches WHERE status = 'pending'"),
            "timelines_done": q("SELECT COUNT(*) FROM timelines WHERE status = 'done'"),
        }


def load_matches(path=config.DB_PATH):
    """All fetched matches as a list of dicts (the raw match-v5 JSON)."""
    conn = sqlite3.connect(path)
    try:
        rows = conn.execute("SELECT json FROM matches WHERE status = 'done'").fetchall()
    finally:
        conn.close()
    return [json.loads(r[0]) for r in rows]


def load_timelines(path=config.DB_PATH):
    """All fetched timelines as {match_id: timeline dict}."""
    conn = sqlite3.connect(path)
    try:
        rows = conn.execute("SELECT match_id, json FROM timelines WHERE status = 'done'").fetchall()
    finally:
        conn.close()
    return {match_id: json.loads(data) for match_id, data in rows}
