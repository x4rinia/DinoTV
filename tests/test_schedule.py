import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugin.video.dinotv"))

from resources.lib.schedule import parse_scoreboard


class ScheduleTests(unittest.TestCase):
    def test_parse_game_converts_to_berlin_and_preserves_confirmed_broadcast(self):
        payload = {"events": [{
            "id": "401", "name": "Away at Home", "date": "2026-10-18T17:00:00Z",
            "status": {"type": {"description": "Scheduled", "completed": False}},
            "competitions": [{
                "broadcasts": [{"names": ["FOX"]}],
                "competitors": [
                    {"homeAway": "home", "score": "0", "team": {"id": "1", "displayName": "Home", "abbreviation": "HOM", "logos": [{"href": "https://img/home.png"}]}},
                    {"homeAway": "away", "score": "0", "team": {"id": "2", "displayName": "Away", "abbreviation": "AWY", "logos": []}},
                ]}]}]}
        game = parse_scoreboard(payload)[0]
        self.assertEqual(game["kickoff_display"], "Sun, 18.10.2026 19:00 Uhr")
        self.assertEqual(game["broadcasts"], ["FOX"])
        self.assertEqual(game["home"]["logo"], "https://img/home.png")

    def test_missing_broadcast_stays_unknown(self):
        payload = {"events": [{"id": "1", "date": "2026-10-18T17:00:00Z", "competitions": [{"competitors": [
            {"homeAway": "home", "team": {"displayName": "H"}}, {"homeAway": "away", "team": {"displayName": "A"}}
        ]}]}]}
        self.assertEqual(parse_scoreboard(payload)[0]["broadcasts"], [])


if __name__ == "__main__":
    unittest.main()
