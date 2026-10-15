import importlib
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugin.video.dinotv"


class FakeAddon:
    def __init__(self, *args):
        self.settings = {"m3u_path": "", "history_size": "20", "schedule_days": "14", "favorite_teams": ""}
    def getAddonInfo(self, key):
        return {"path": str(PLUGIN), "profile": _PROFILE, "icon": str(PLUGIN / "resources/icon.png"), "fanart": str(PLUGIN / "resources/fanart.jpg")}.get(key, "")
    def getSetting(self, key): return self.settings.get(key, "")
    def getSettingBool(self, key): return key == "allow_external_links"
    def setSetting(self, key, value): self.settings[key] = value
    def openSettings(self): pass


class FakeListItem:
    def __init__(self, label="", path=""): self.label, self.path = label, path
    def setArt(self, value): pass
    def setInfo(self, kind, value): pass
    def setProperty(self, key, value): pass
    def addContextMenuItems(self, value): pass


def install_kodi_stubs(profile):
    global _PROFILE
    _PROFILE = profile
    sys.modules["xbmc"] = types.SimpleNamespace(LOGINFO=1, LOGERROR=4, log=lambda *args: None, executebuiltin=lambda *args: None,
                                                 getCondVisibility=lambda value: False, Keyboard=lambda *args: None)
    sys.modules["xbmcaddon"] = types.SimpleNamespace(Addon=FakeAddon)
    sys.modules["xbmcgui"] = types.SimpleNamespace(ListItem=FakeListItem, Dialog=lambda: types.SimpleNamespace())
    state = {"items": [], "ended": False}
    sys.modules["xbmcplugin"] = types.SimpleNamespace(
        SORT_METHOD_UNSORTED=0, addDirectoryItem=lambda handle, url, item, folder: state["items"].append((url, item.label, folder)),
        setContent=lambda *args: None, addSortMethod=lambda *args: None,
        endOfDirectory=lambda *args, **kwargs: state.update(ended=True), setResolvedUrl=lambda *args: None)
    sys.modules["xbmcvfs"] = types.SimpleNamespace(translatePath=lambda value: value)
    return state


class RoutingTests(unittest.TestCase):
    def test_root_has_exact_remote_friendly_ten_entries(self):
        with tempfile.TemporaryDirectory() as profile:
            state = install_kodi_stubs(profile)
            sys.path.insert(0, str(PLUGIN))
            for name in ("resources.lib.compat", "resources.lib.router"):
                sys.modules.pop(name, None)
            router = importlib.import_module("resources.lib.router")
            router.DinoTV("plugin://plugin.video.dinotv", 7).root()
            labels = [item[1] for item in state["items"]]
            self.assertEqual(labels, ["Live NFL", "NFL-Spielplan", "Deutsche Sender", "US-Sender",
                                      "NFL Network & RedZone", "College Football", "Highlights & Replays",
                                      "Favoriten", "Eigene Streams", "Einstellungen"])
            self.assertTrue(all(item[2] for item in state["items"]))
            self.assertTrue(state["ended"])


if __name__ == "__main__":
    unittest.main()
