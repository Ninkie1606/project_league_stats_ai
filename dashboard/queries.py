"""SQL for the dashboard. Every function takes a connection to stats.db and returns a DataFrame.

Rates are fractions (0.53 = 53%). `patches` / `tiers` are lists; empty means "all".
"""
import pandas as pd

ROLES = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
TIERS = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", "EMERALD", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"]


def _games_filter(patches, tiers):
    """SQL selecting the match_ids that pass the sidebar filters, plus its parameters."""
    sql, params = "SELECT match_id FROM games WHERE remake = 0", []
    if patches:
        sql += f" AND patch IN ({', '.join('?' * len(patches))})"
        params += list(patches)
    if tiers:
        sql += f" AND match_tier IN ({', '.join('?' * len(tiers))})"
        params += list(tiers)
    return sql, params


def overview(conn):
    return pd.read_sql(
        "SELECT patch, match_tier, COUNT(*) AS games FROM games WHERE remake = 0 GROUP BY 1, 2", conn
    )


def filter_options(conn):
    patches = [r[0] for r in conn.execute("SELECT DISTINCT patch FROM games WHERE patch IS NOT NULL")]
    patches.sort(key=lambda p: tuple(int(x) for x in p.split(".")), reverse=True)  # 16.20 before 16.9
    tiers = [r[0] for r in conn.execute("SELECT DISTINCT match_tier FROM games WHERE match_tier IS NOT NULL")]
    tiers.sort(key=TIERS.index)
    champions = [r[0] for r in conn.execute("SELECT champion_name FROM champions ORDER BY champion_name")]
    return patches, tiers, champions


def total_games(conn, patches, tiers):
    games, params = _games_filter(patches, tiers)
    return conn.execute(f"SELECT COUNT(*) FROM ({games})", params).fetchone()[0]


def champion_table(conn, role, patches, tiers, min_games):
    """Win, pick and ban rate per champion, in one role (or all roles if role is None)."""
    games, params = _games_filter(patches, tiers)
    role_sql = "AND p.team_position = ?" if role else ""
    role_params = [role] if role else []
    df = pd.read_sql(
        f"""
        WITH g AS ({games}),
        n AS (SELECT COUNT(*) AS total FROM g),
        picks AS (
            SELECT p.champion_name, COUNT(*) AS games, AVG(p.win) AS win_rate,
                   (SUM(p.kills) + SUM(p.assists)) * 1.0 / MAX(SUM(p.deaths), 1) AS kda,
                   SUM(p.total_cs) * 60.0 / SUM(ga.game_duration) AS cs_per_min
            FROM participants p JOIN games ga USING (match_id)
            WHERE p.match_id IN g {role_sql}
            GROUP BY p.champion_name
        ),
        banned AS (
            SELECT c.champion_name, COUNT(DISTINCT b.match_id) AS bans
            FROM bans b JOIN champions c USING (champion_id)
            WHERE b.match_id IN g
            GROUP BY c.champion_name
        )
        SELECT picks.*, picks.games * 1.0 / n.total AS pick_rate,
               COALESCE(banned.bans, 0) * 1.0 / n.total AS ban_rate
        FROM picks CROSS JOIN n LEFT JOIN banned USING (champion_name)
        WHERE picks.games >= ?
        ORDER BY picks.games DESC
        """,
        conn, params=params + role_params + [min_games],
    )
    return df


def main_role(conn, champion):
    row = conn.execute(
        "SELECT team_position FROM participants WHERE champion_name = ? AND team_position != '' "
        "GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 1",
        (champion,),
    ).fetchone()
    return row[0] if row else None


def matchups(conn, champion, role, patches, tiers, min_games):
    """Win rate of `champion` against each enemy in the same role."""
    games, params = _games_filter(patches, tiers)
    return pd.read_sql(
        f"""
        SELECT enemy.champion_name AS opponent, COUNT(*) AS games, AVG(me.win) AS win_rate,
               AVG(me.gold_earned - enemy.gold_earned) AS gold_diff
        FROM participants me
        JOIN participants enemy
          ON enemy.match_id = me.match_id AND enemy.team_position = me.team_position
         AND enemy.team_id != me.team_id
        WHERE me.champion_name = ? AND me.team_position = ? AND me.match_id IN ({games})
        GROUP BY enemy.champion_name
        HAVING COUNT(*) >= ?
        ORDER BY win_rate DESC
        """,
        conn, params=[champion, role] + params + [min_games],
    )


def synergy(conn, champion, role, partner_role, patches, tiers, min_games):
    """Win rate of `champion` (in `role`) with each teammate (optionally only in `partner_role`)."""
    games, params = _games_filter(patches, tiers)
    partner_sql = "AND mate.team_position = ?" if partner_role else ""
    return pd.read_sql(
        f"""
        SELECT mate.champion_name AS teammate, mate.team_position AS teammate_role,
               COUNT(*) AS games, AVG(me.win) AS win_rate
        FROM participants me
        JOIN participants mate
          ON mate.match_id = me.match_id AND mate.team_id = me.team_id AND mate.puuid != me.puuid
        WHERE me.champion_name = ? AND me.team_position = ? {partner_sql} AND me.match_id IN ({games})
        GROUP BY mate.champion_name, mate.team_position
        HAVING COUNT(*) >= ?
        ORDER BY win_rate DESC
        """,
        conn, params=[champion, role] + ([partner_role] if partner_role else []) + params + [min_games],
    )


def find_players(conn, text, limit=20):
    """Players whose Riot ID contains `text`, with their most recent Riot ID.

    SQLite takes the bare `riot_id` column from the row that holds MAX(game_creation).
    """
    return pd.read_sql(
        """
        SELECT p.puuid, p.riot_id, COUNT(*) AS games, MAX(g.game_creation) AS last_played
        FROM participants p
        JOIN (SELECT puuid FROM participants WHERE riot_id LIKE ? GROUP BY puuid LIMIT ?) hit USING (puuid)
        JOIN games g USING (match_id)
        GROUP BY p.puuid
        ORDER BY games DESC
        """,
        conn, params=[f"%{text}%", limit],
    )


def player_matches(conn, puuid):
    df = pd.read_sql(
        """
        SELECT g.match_id, g.game_creation, g.game_duration, g.patch, p.champion_name, p.team_position,
               p.win, p.kills, p.deaths, p.assists, p.total_cs, p.vision_score
        FROM participants p JOIN games g USING (match_id)
        WHERE p.puuid = ?
        ORDER BY g.game_creation DESC
        """,
        conn, params=[puuid],
    )
    df["date"] = pd.to_datetime(df["game_creation"], unit="ms")
    return df
