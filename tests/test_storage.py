import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugin.video.dinotv"))

from resources.lib.storage import Storage


class StorageTests(unittest.TestCase):
    def test_favorites_history_and_safe_export(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = Storage(directory)
            self.assertTrue(storage.toggle_favorite("de-rtl"))
            self.assertFalse(storage.toggle_favorite("de-rtl"))
            channel = {"id": "secret", "name": "Mine", "url": "https://secret.test/a.m3u8", "stream_type": "hls", "status": "playable"}
            storage.add_user_channel(channel)
            storage.add_history(channel, limit=2)
            export_path = storage.export_safe("WAS")
            exported = json.loads(Path(export_path).read_text(encoding="utf-8"))
            self.assertNotIn("user_channels", exported)
            self.assertNotIn("history", exported)
            self.assertNotIn("secret.test", json.dumps(exported))
            self.assertEqual(exported["favorite_teams"], "WAS")

    def test_broken_json_recovers_with_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "userdata.json").write_text("not json", encoding="utf-8")
            self.assertEqual(Storage(directory).load()["favorite_channels"], [])


if __name__ == "__main__":
    unittest.main()
