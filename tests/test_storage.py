import tempfile
import unittest
from pathlib import Path

from riot.storage import Storage


class StorageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.storage = Storage(Path(self.tmp.name) / "test.db")

    def tearDown(self):
        self.storage.conn.close()
        self.tmp.cleanup()

    def test_seed_pages_advance_until_empty(self):
        self.assertEqual(self.storage.next_seed_page("GOLD", "I"), 1)
        self.storage.mark_seed_page("GOLD", "I", 1, 205)
        self.assertEqual(self.storage.next_seed_page("GOLD", "I"), 2)
        self.storage.mark_seed_page("GOLD", "I", 2, 0)
        self.assertIsNone(self.storage.next_seed_page("GOLD", "I"))
        self.assertEqual(self.storage.next_seed_page("GOLD", "II"), 1)

    def test_next_player_filters_on_tier(self):
        self.storage.add_players([{"puuid": "a"}], "GOLD", "I")
        self.storage.add_players([{"puuid": "b"}], "SILVER", "I")
        self.assertEqual(self.storage.next_player(["SILVER"]), "b")
        self.storage.mark_player_done("b")
        self.assertIsNone(self.storage.next_player(["SILVER"]))
        self.assertEqual(self.storage.next_player(), "a")

    def test_match_ids_are_deduplicated(self):
        self.assertEqual(self.storage.add_match_ids(["m1", "m2"]), 2)
        self.assertEqual(self.storage.add_match_ids(["m2", "m3"]), 1)
        self.storage.save_match("m1", {"x": 1})
        self.storage.save_match("m2", None)
        stats = self.storage.stats()
        self.assertEqual(stats["matches_done"], 1)
        self.assertEqual(stats["matches_pending"], 1)


if __name__ == "__main__":
    unittest.main()
