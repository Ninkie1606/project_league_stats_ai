import tempfile
import unittest
from pathlib import Path

from dashboard import queries
from riot import stats
from riot.storage import Storage

ROLES = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
BLUE = ["Garen", "LeeSin", "Ahri", "Jinx", "Lulu"]
RED = ["Darius", "Vi", "Zed", "Caitlyn", "Thresh"]
CHAMPION_IDS = {name: i + 1 for i, name in enumerate(BLUE + RED)}


def make_match(match_id, blue, red, blue_wins, duration=1800):
    """A minimal match-v5 dict. `blue` / `red` are 5 champion names in role order."""
    participants = []
    for team_id, champs, win in ((100, blue, blue_wins), (200, red, not blue_wins)):
        for role, champ in zip(ROLES, champs):
            participants.append({
                "puuid": f"{match_id}-{team_id}-{role}" if champ != "Ahri" else "ahri-player",
                "riotIdGameName": "AhriMain" if champ == "Ahri" else champ, "riotIdTagline": "EUW",
                "teamId": team_id, "teamPosition": role, "championId": CHAMPION_IDS[champ], "championName": champ,
                "win": win, "kills": 2, "deaths": 1, "assists": 3, "totalMinionsKilled": 150,
                "neutralMinionsKilled": 0, "goldEarned": 10000, "totalDamageDealtToChampions": 15000,
                "visionScore": 20,
            })
    return {
        "metadata": {"matchId": match_id},
        "info": {
            "gameCreation": 1_760_000_000_000, "gameDuration": duration, "gameVersion": "16.20.824.8524",
            "participants": participants,
            "teams": [{"teamId": 100, "bans": [{"championId": CHAMPION_IDS["LeeSin"]}, {"championId": -1}]},
                      {"teamId": 200, "bans": []}],
        },
    }


class StatsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.source = Path(self.tmp.name) / "league.db"
        self.target = Path(self.tmp.name) / "stats.db"
        storage = Storage(self.source)
        storage.add_players([{"puuid": "ahri-player"}], "GOLD", "I")
        matches = [
            make_match("M1", BLUE, RED, blue_wins=True),
            make_match("M2", BLUE, RED, blue_wins=False),
            make_match("M3", BLUE, RED, blue_wins=True),
            make_match("REMAKE", BLUE, RED, blue_wins=True, duration=200),
        ]
        storage.add_match_ids([m["metadata"]["matchId"] for m in matches] + ["PENDING"])
        for m in matches:
            storage.save_match(m["metadata"]["matchId"], m)
        storage.conn.close()
        self.added = stats.build(self.source, self.target)
        self.conn = stats.connect(self.target)

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def count(self, table):
        return self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def test_flatten_and_remake(self):
        self.assertEqual(self.added, 4)
        self.assertEqual(self.count("games"), 4)
        self.assertEqual(self.count("participants"), 30)  # remake has no participants
        self.assertEqual(self.count("bans"), 3)           # -1 (no ban) is skipped
        tier, patch = self.conn.execute("SELECT match_tier, patch FROM games WHERE match_id = 'M1'").fetchone()
        self.assertEqual((tier, patch), ("GOLD", "16.20"))

    def test_build_is_incremental(self):
        self.assertEqual(stats.build(self.source, self.target), 0)
        self.assertEqual(self.count("participants"), 30)
        self.assertEqual(stats.build(self.source, self.target, rebuild=True), 4)

    def test_champion_table(self):
        df = queries.champion_table(self.conn, "MIDDLE", [], [], 1).set_index("champion_name")
        self.assertAlmostEqual(df.loc["Ahri", "win_rate"], 2 / 3)
        self.assertAlmostEqual(df.loc["Ahri", "pick_rate"], 1.0)
        self.assertAlmostEqual(df.loc["Ahri", "kda"], 5.0)
        self.assertAlmostEqual(df.loc["Ahri", "cs_per_min"], 5.0)
        bans = queries.champion_table(self.conn, None, [], [], 1).set_index("champion_name")["ban_rate"]
        self.assertAlmostEqual(bans["LeeSin"], 1.0)
        self.assertNotIn("Garen", df.index)

    def test_matchups_and_synergy(self):
        m = queries.matchups(self.conn, "Ahri", "MIDDLE", [], [], 1)
        self.assertEqual(m["opponent"].tolist(), ["Zed"])
        self.assertAlmostEqual(m["win_rate"].iloc[0], 2 / 3)
        s = queries.synergy(self.conn, "Jinx", "BOTTOM", "UTILITY", [], [], 1)
        self.assertEqual(s["teammate"].tolist(), ["Lulu"])
        self.assertEqual(s["games"].iloc[0], 3)
        self.assertEqual(len(queries.synergy(self.conn, "Jinx", "BOTTOM", None, [], [], 1)), 4)

    def test_player(self):
        hits = queries.find_players(self.conn, "ahrimain")
        self.assertEqual(hits["riot_id"].tolist(), ["AhriMain#EUW"])
        self.assertEqual(len(queries.player_matches(self.conn, "ahri-player")), 3)


if __name__ == "__main__":
    unittest.main()
