import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugin.video.dinotv"))

from resources.lib.channels import (ChannelError, detect_stream_type, load_catalog, parse_m3u,
                                    user_channel, validate_catalog, validate_stream_url)


class ChannelTests(unittest.TestCase):
    def test_builtin_catalog_is_valid_and_has_no_playable_claims(self):
        channels = load_catalog(ROOT / "plugin.video.dinotv/resources/data/channels.json")
        self.assertGreaterEqual(len(channels), 20)
        self.assertFalse(any(item["status"] == "playable" for item in channels))
        self.assertTrue(all(not item["url"] or item["url"].startswith("https://") for item in channels))

    def test_stream_detection_and_https_policy(self):
        self.assertEqual(detect_stream_type("https://example.test/live.m3u8?token=x"), "hls")
        self.assertEqual(detect_stream_type("https://example.test/live.mpd"), "dash")
        self.assertEqual(detect_stream_type("plugin://plugin.video.example/play/1"), "plugin")
        with self.assertRaises(ChannelError):
            validate_stream_url("http://example.test/live.m3u8")
        with self.assertRaises(ChannelError):
            validate_stream_url("https://example.test/video.mp4")

    def test_parse_m3u_skips_insecure_and_unknown_entries(self):
        channels = parse_m3u("""#EXTM3U
#EXTINF:-1 tvg-logo="https://img.test/logo.png",Legal HLS
https://media.test/live.m3u8
#EXTINF:-1,Insecure
http://media.test/live.m3u8
#EXTINF:-1,Unknown
https://media.test/video.mp4
""")
        self.assertEqual([item["name"] for item in channels], ["Legal HLS"])
        self.assertEqual(channels[0]["logo"], "https://img.test/logo.png")

    def test_duplicate_ids_are_rejected(self):
        channel = user_channel("One", "https://media.test/one.m3u8")
        with self.assertRaises(ChannelError):
            validate_catalog([channel, dict(channel)])


if __name__ == "__main__":
    unittest.main()
