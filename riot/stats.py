"""Flatten the raw match JSON in league.db into relational tables in stats.db.

league.db stays the source of truth; stats.db is a derived copy that can be
deleted and rebuilt at any time. It is a separate file so a build never holds
a lock on league.db for long: the crawler may be writing to it at the same time.
"""
import json
import logging
import sqlite3
from collections import Counter

from riot import config

log = logging.getLogger(__name__)

STATS_DB_PATH = config.DB_PATH.parent / "stats.db"
REMAKE_SECONDS = 300
BATCH = 200  # matches per read from league.db; keeps each read lock short

SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    match_id TEXT PRIMARY KEY,
    game_creation INTEGER,                   -- ms since epoch
    game_duration INTEGER,                   -- seconds
    patch TEXT,                              -- e.g. 16.20
    match_tier TEXT,                         -- most common seed tier among the players
    remake INTEGER NOT NULL                  -- 1 = shorter than 5 min, no participants stored
);
CREATE TABLE IF NOT EXISTS participants (
    match_id TEXT NOT NULL,
    puuid TEXT NOT NULL,
    riot_id TEXT,
    team_id INTEGER,
    team_position TEXT,                      -- TOP JUNGLE MIDDLE BOTTOM UTILITY, or ''
    champion_id INTEGER,
    champion_name TEXT,
    win INTEGER,
    kills INTEGER,
    deaths INTEGER,
    assists INTEGER,
    total_cs INTEGER,
    gold_earned INTEGER,
    damage_to_champions INTEGER,
    vision_score INTEGER,
    PRIMARY KEY (match_id, puuid)
);
CREATE TABLE IF NOT EXISTS bans (
    match_id TEXT NOT NULL,
    team_id INTEGER,
    champion_id INTEGER
);
CREATE TABLE IF NOT EXISTS champions (
    champion_id INTEGER PRIMARY KEY,
    champion_name TEXT
);
CREATE INDEX IF NOT EXISTS idx_participants_champion ON participants (champion_name, team_position);
CREATE INDEX IF NOT EXISTS idx_participants_puuid ON participants (puuid);
CREATE INDEX IF NOT EXISTS idx_bans_match ON bans (match_id);
CREATE INDEX IF NOT EXISTS idx_games_filter ON games (patch, match_tier);
"""


def patch_of(game_version):
    """'16.20.824.8524' -> '16.20'. A few matches have an empty gameVersion; those get None."""
    parts = (game_version or "").split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else None


def flatten(match, seed_tiers):
    """One raw match-v5 dict -> (game row, participant rows, ban rows)."""
    info = match["info"]
    match_id = match["metadata"]["matchId"]
    players = info["participants"]
    tiers = Counter(seed_tiers[p["puuid"]] for p in players if p["puuid"] in seed_tiers)
    remake = info["gameDuration"] < REMAKE_SECONDS
    game = (
        match_id, info["gameCreation"], info["gameDuration"], patch_of(info["gameVersion"]),
        tiers.most_common(1)[0][0] if tiers else None, int(remake),
    )
    if remake:
        return game, [], []
    participants = [
        (
            match_id, p["puuid"], f'{p.get("riotIdGameName", "")}#{p.get("riotIdTagline", "")}',
            p["teamId"], p.get("teamPosition") or "", p["championId"], p["championName"], int(p["win"]),
            p["kills"], p["deaths"], p["assists"], p["totalMinionsKilled"] + p["neutralMinionsKilled"],
            p["goldEarned"], p["totalDamageDealtToChampions"], p["visionScore"],
        )
        for p in players
    ]
    bans = [
        (match_id, team["teamId"], ban["championId"])
        for team in info["teams"] for ban in team.get("bans", []) if ban["championId"] > 0
    ]
    return game, participants, bans


def build(source=config.DB_PATH, target=STATS_DB_PATH, rebuild=False):
    """Add every fetched match that isn't in stats.db yet. Returns the number of matches added."""
    if rebuild and target.exists():
        target.unlink()
    target.parent.mkdir(parents=True, exist_ok=True)
    out = sqlite3.connect(target)
    src = sqlite3.connect(f"file:{source}?mode=ro", uri=True, timeout=30)
    try:
        out.executescript(SCHEMA)
        seed_tiers = dict(src.execute("SELECT puuid, tier FROM players").fetchall())
        done = {row[0] for row in out.execute("SELECT match_id FROM games")}
        # Only match_id, so SQLite scans the small primary-key index instead of the 7 GB of JSON.
        todo = [row[0] for row in src.execute("SELECT match_id FROM matches").fetchall() if row[0] not in done]
        log.info("%d nieuwe matches om te verwerken", len(todo))

        added = 0
        for start in range(0, len(todo), BATCH):
            ids = todo[start:start + BATCH]
            rows = src.execute(
                f"SELECT json FROM matches WHERE status = 'done' AND match_id IN ({', '.join('?' * len(ids))})",
                ids,
            ).fetchall()
            added += len(rows)
            games, participants, bans = [], [], []
            for (data,) in rows:
                game, ps, bs = flatten(json.loads(data), seed_tiers)
                games.append(game)
                participants += ps
                bans += bs
            out.executemany("INSERT INTO games VALUES (?, ?, ?, ?, ?, ?)", games)
            out.executemany(f"INSERT INTO participants VALUES ({', '.join('?' * 15)})", participants)
            out.executemany("INSERT INTO bans VALUES (?, ?, ?)", bans)
            out.executemany(
                "INSERT OR IGNORE INTO champions VALUES (?, ?)", {(p[5], p[6]) for p in participants}
            )
            out.commit()
            if (start // BATCH) % 50 == 49:
                log.info("%d / %d matches verwerkt", start + len(ids), len(todo))
        return added
    finally:
        src.close()
        out.close()


def connect(path=STATS_DB_PATH):
    """Read-only connection to stats.db, for analysis and the dashboard."""
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)
