#!/usr/bin/env python3
"""Optional network smoke check; does not claim or test any video playback."""
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugin.video.dinotv"))

from resources.lib.schedule import ScheduleClient


with tempfile.TemporaryDirectory() as directory:
    games = ScheduleClient(directory).get_games(days=14, force=True)
    print("NFL schedule API returned {} parsed games.".format(len(games)))
    for game in games[:3]:
        print("{} | {} | {}".format(game["kickoff_display"], game["name"], ", ".join(game["broadcasts"]) or "Sender unbekannt"))
