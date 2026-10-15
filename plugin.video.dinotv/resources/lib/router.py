import json
import os
import sys
from urllib.parse import parse_qs, urlencode

from .channels import ChannelError, apply_order, load_catalog, load_m3u, merge_channels, user_channel
from .compat import KODI, addon, log, profile_path, xbmc, xbmcgui, xbmcplugin
from .playback import PlaybackError, open_external, play
from .schedule import ScheduleClient, ScheduleError
from .storage import Storage


STATUS_LABELS = {
    "playable": "Direkt in Kodi abspielbar (Benutzerquelle)",
    "official_external": "Offizieller externer Anbieter",
    "subscription_required": "Zugang oder Abo erforderlich",
    "external_only": "Nur externer Link",
    "unsupported": "Derzeit nicht unterstützt",
}

BROADCAST_ALIASES = {
    "FOX": "us-fox", "CBS": "us-cbs", "NBC": "us-nbc", "ESPN": "us-espn", "ESPN2": "us-espn",
    "NFL NETWORK": "nfl-network", "NFL NET": "nfl-network", "NFLN": "nfl-network",
    "ABC": "us-espn", "AMAZON PRIME VIDEO": "us-prime", "PRIME VIDEO": "us-prime",
}


class DinoTV:
    def __init__(self, base_url, handle):
        self.base_url = base_url
        self.handle = handle
        self.addon = addon()
        self.profile = profile_path()
        self.storage = Storage(self.profile)
        catalog_path = os.path.join(self.addon.getAddonInfo("path"), "resources", "data", "channels.json")
        builtin = load_catalog(catalog_path)
        data = self.storage.load()
        playlist = load_m3u(self.addon.getSetting("m3u_path"))
        self.channels = merge_channels(builtin, data["user_channels"], playlist)
        self.channel_map = {item["id"]: item for item in self.channels}

    def url(self, action="root", **params):
        query = {"action": action}
        query.update({key: str(value) for key, value in params.items()})
        return self.base_url + "?" + urlencode(query)

    def folder(self, label, action, icon="DefaultFolder.png", **params):
        item = xbmcgui.ListItem(label=label)
        item.setArt({"icon": icon, "thumb": icon})
        xbmcplugin.addDirectoryItem(self.handle, self.url(action, **params), item, True)

    def command(self, label, action, icon="DefaultAddonService.png", **params):
        item = xbmcgui.ListItem(label=label)
        item.setArt({"icon": icon, "thumb": icon})
        xbmcplugin.addDirectoryItem(self.handle, self.url(action, **params), item, False)

    def root(self):
        entries = [
            ("Live NFL", "channels", {"category": "live"}),
            ("NFL-Spielplan", "schedule", {}),
            ("Deutsche Sender", "channels", {"category": "german"}),
            ("US-Sender", "channels", {"category": "us"}),
            ("NFL Network & RedZone", "channels", {"category": "nfl"}),
            ("College Football", "channels", {"category": "college"}),
            ("Highlights & Replays", "channels", {"category": "highlights"}),
            ("Favoriten", "favorites", {}),
            ("Eigene Streams", "custom", {}),
            ("Einstellungen", "settings", {}),
        ]
        for label, action, params in entries:
            self.folder(label, action, **params)
        self._finish("videos")

    def list_channels(self, category=None, favorite_only=False, history_only=False):
        data = self.storage.load()
        if history_only:
            channels = data["history"]
        elif favorite_only:
            channels = [self.channel_map[item] for item in data["favorite_channels"] if item in self.channel_map]
        elif category == "live":
            channels = [item for item in self.channels if item.get("category") in {"german", "us", "nfl", "custom"}]
        else:
            channels = [item for item in self.channels if item.get("category") == category]
        channels = apply_order(channels, data["channel_order"])
        if not channels:
            self._notice_item("Keine Einträge vorhanden")
        for channel in channels:
            self._channel_item(channel, channel["id"] in data["favorite_channels"])
        self._finish("videos")

    def _channel_item(self, channel, favorite=False):
        status = STATUS_LABELS.get(channel.get("status"), "Status unbekannt")
        label = "{}{}  [COLOR gray]– {}[/COLOR]".format("★ " if favorite else "", channel.get("name", "Unbekannt"), status)
        item = xbmcgui.ListItem(label=label)
        item.setInfo("video", {"title": channel.get("name", ""), "plot": self._channel_plot(channel)})
        art = channel.get("logo") or self.addon.getAddonInfo("icon")
        item.setArt({"thumb": art, "icon": art, "fanart": self.addon.getAddonInfo("fanart")})
        if channel.get("status") == "playable":
            item.setProperty("IsPlayable", "true")
        favorite_label = "Aus Favoriten entfernen" if favorite else "Zu Favoriten hinzufügen"
        contexts = [
            (favorite_label, "RunPlugin({})".format(self.url("toggle_favorite", id=channel["id"]))),
            ("Nach oben", "RunPlugin({})".format(self.url("move", id=channel["id"], direction=-1))),
            ("Nach unten", "RunPlugin({})".format(self.url("move", id=channel["id"], direction=1))),
        ]
        if channel.get("category") == "custom":
            contexts.append(("Eigene Quelle löschen", "RunPlugin({})".format(self.url("delete_custom", id=channel["id"]))))
        item.addContextMenuItems(contexts)
        xbmcplugin.addDirectoryItem(self.handle, self.url("open", id=channel["id"]), item, False)

    def _channel_plot(self, channel):
        return "[B]Anbieter:[/B] {provider}\n[B]Zugang:[/B] {access}\n[B]Status:[/B] {status}\n[B]DRM:[/B] {drm}\n[B]Zuletzt geprüft:[/B] {last_verified}".format(
            provider=channel.get("provider", "unbekannt"), access=channel.get("access", "unbekannt"),
            status=STATUS_LABELS.get(channel.get("status"), "unbekannt"), drm=channel.get("drm", "unbekannt"),
            last_verified=channel.get("last_verified", "unbekannt"),
        )

    def open_channel(self, channel_id):
        channel = self.channel_map.get(channel_id)
        if not channel:
            self.dialog("Quelle wurde nicht gefunden.")
            return
        if channel.get("status") == "playable":
            try:
                limit = _int_setting(self.addon.getSetting("history_size"), 20)
                self.storage.add_history(channel, limit)
                play(self.handle, channel)
            except PlaybackError as exc:
                self.dialog(str(exc) + "\n\nÖffne 'Live NFL' für verfügbare Alternativen.")
            return
        if channel.get("stream_type") == "external" and channel.get("url"):
            try:
                allow = self.addon.getSettingBool("allow_external_links")
                self.storage.add_history(channel, _int_setting(self.addon.getSetting("history_size"), 20))
                open_external(channel["url"], allow)
            except PlaybackError as exc:
                self.dialog(str(exc))
            return
        self.dialog("{}\n\n{}".format(STATUS_LABELS.get(channel.get("status"), "Nicht verfügbar"), channel.get("access", "")))

    def schedule(self, force=False):
        try:
            games = ScheduleClient(self.profile).get_games(_int_setting(self.addon.getSetting("schedule_days"), 14), force)
        except ScheduleError as exc:
            self.dialog(str(exc))
            games = []
        favorite_teams = {item.strip().upper() for item in self.addon.getSetting("favorite_teams").split(",") if item.strip()}
        games.sort(key=lambda game: (not ({game["home"]["abbr"], game["away"]["abbr"]} & favorite_teams), game["kickoff"]))
        for game in games:
            score = ""
            if game["completed"]:
                score = "  {}:{}".format(game["away"]["score"], game["home"]["score"])
            broadcasts = ", ".join(game["broadcasts"]) if game["broadcasts"] else "Senderzuordnung unbekannt"
            label = "{} – {} @ {}{}".format(game["kickoff_display"], game["away"]["name"], game["home"]["name"], score)
            item = xbmcgui.ListItem(label=label)
            item.setInfo("video", {"title": game["name"], "plot": "[B]Status:[/B] {}\n[B]Übertragung:[/B] {}".format(game["status"], broadcasts)})
            logo = game["away"].get("logo") or self.addon.getAddonInfo("icon")
            item.setArt({"thumb": logo, "icon": logo, "fanart": self.addon.getAddonInfo("fanart")})
            xbmcplugin.addDirectoryItem(self.handle, self.url("game", id=game["id"]), item, True)
        if not games:
            self._notice_item("Keine NFL-Spiele im gewählten Zeitraum gefunden")
        self._finish("videos")

    def game(self, game_id):
        try:
            games = ScheduleClient(self.profile).get_games(_int_setting(self.addon.getSetting("schedule_days"), 14))
        except ScheduleError as exc:
            self._notice_item(str(exc))
            self._finish("videos")
            return
        game = next((item for item in games if item["id"] == game_id), None)
        if not game:
            self._notice_item("Spiel nicht mehr im aktuellen Spielplan")
            self._finish("videos")
            return
        matched = []
        for name in game["broadcasts"]:
            channel_id = BROADCAST_ALIASES.get(name.upper())
            if channel_id and channel_id in self.channel_map and channel_id not in matched:
                matched.append(channel_id)
        if not game["broadcasts"]:
            self._notice_item("Senderzuordnung unbekannt – es wird nichts geraten")
        elif not matched:
            self._notice_item("Bestätigt: {} – kein direkter Kodi-Weg hinterlegt".format(", ".join(game["broadcasts"])))
        for channel_id in matched:
            self._channel_item(self.channel_map[channel_id], channel_id in self.storage.load()["favorite_channels"])
        if "de-dazn-gamepass" in self.channel_map:
            channel = dict(self.channel_map["de-dazn-gamepass"])
            channel["name"] = "NFL Game Pass – Verfügbarkeit für dieses Spiel prüfen"
            self._channel_item(channel, False)
        self._finish("videos")

    def favorites(self):
        self.folder("Lieblingssender", "channels", favorite="1")
        self.folder("Zuletzt verwendet", "history")
        self.command("Lieblingsteams festlegen", "open_settings")
        self._finish("videos")

    def custom(self):
        self.command("Neue HTTPS-/Plugin-Quelle anlegen", "add_custom")
        self.command("M3U-Datei in Einstellungen auswählen", "open_settings")
        self.folder("Meine Quellen", "channels", category="custom")
        self._finish("videos")

    def settings_menu(self):
        self.command("Kodi-Einstellungen öffnen", "open_settings")
        self.folder("Spielplan jetzt aktualisieren", "refresh_schedule")
        self.command("Sichere Einstellungen exportieren", "export")
        self.command("Sichere Einstellungen importieren", "import")
        self.command("Lokale DinoTV-Daten zurücksetzen", "reset")
        self._finish("files")

    def add_custom(self):
        name = self._keyboard("Name der Quelle")
        if not name:
            return
        url = self._keyboard("Autorisierte HTTPS-, HLS-, DASH- oder Plugin-URL")
        if not url:
            return
        try:
            channel = user_channel(name, url)
            self.storage.add_user_channel(channel)
            xbmcgui.Dialog().notification("DinoTV", "Quelle gespeichert", self.addon.getAddonInfo("icon"), 3000)
            xbmc.executebuiltin("Container.Refresh")
        except ChannelError as exc:
            self.dialog(str(exc))

    def dispatch(self, action, params):
        channel_id = params.get("id", [""])[0]
        if action == "root": self.root()
        elif action == "channels": self.list_channels(params.get("category", [None])[0], params.get("favorite", [""])[0] == "1")
        elif action == "favorites": self.favorites()
        elif action == "history": self.list_channels(history_only=True)
        elif action == "custom": self.custom()
        elif action == "settings": self.settings_menu()
        elif action == "open": self.open_channel(channel_id)
        elif action == "schedule": self.schedule()
        elif action == "refresh_schedule": self.schedule(True)
        elif action == "game": self.game(channel_id)
        elif action == "toggle_favorite":
            self.storage.toggle_favorite(channel_id); xbmc.executebuiltin("Container.Refresh")
        elif action == "move":
            self.storage.move_channel(channel_id, int(params.get("direction", ["0"])[0])); xbmc.executebuiltin("Container.Refresh")
        elif action == "delete_custom":
            if xbmcgui.Dialog().yesno("DinoTV", "Eigene Quelle wirklich löschen?"):
                self.storage.remove_user_channel(channel_id); xbmc.executebuiltin("Container.Refresh")
        elif action == "add_custom": self.add_custom()
        elif action == "open_settings": self.addon.openSettings()
        elif action == "export":
            path = self.storage.export_safe(self.addon.getSetting("favorite_teams")); self.dialog("Export gespeichert:\n{}".format(path))
        elif action == "import": self._import_settings()
        elif action == "reset": self._reset()
        else: self.dialog("Unbekannte DinoTV-Aktion: {}".format(action))

    def _import_settings(self):
        default_path = os.path.join(self.profile, "dinotv-settings-export.json")
        path = xbmcgui.Dialog().browseSingle(1, "DinoTV-Export wählen", "files", ".json", False, False, default_path)
        if not path: return
        try:
            teams = self.storage.import_safe(path)
            self.addon.setSetting("favorite_teams", teams)
            self.dialog("Einstellungen wurden importiert. Persönliche Stream-URLs waren nicht Teil des Exports.")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            self.dialog("Import fehlgeschlagen: {}".format(exc))

    def _reset(self):
        if xbmcgui.Dialog().yesno("DinoTV", "Favoriten, Verlauf, Reihenfolge und eigene Quellen lokal löschen?"):
            self.storage.reset(); self.dialog("Lokale DinoTV-Daten wurden zurückgesetzt.")

    def _keyboard(self, heading):
        keyboard = xbmc.Keyboard("", heading)
        keyboard.doModal()
        return keyboard.getText().strip() if keyboard.isConfirmed() else ""

    def _notice_item(self, text):
        item = xbmcgui.ListItem(label="[COLOR gray]{}[/COLOR]".format(text))
        xbmcplugin.addDirectoryItem(self.handle, "", item, False)

    def dialog(self, message):
        xbmcgui.Dialog().ok("DinoTV", message)

    def _finish(self, content):
        xbmcplugin.setContent(self.handle, content)
        xbmcplugin.addSortMethod(self.handle, xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.endOfDirectory(self.handle, cacheToDisc=False)


def _int_setting(value, default):
    try: return int(value)
    except (TypeError, ValueError): return default


def run(argv=None):
    if not KODI:
        raise RuntimeError("DinoTV main.py muss von Kodi gestartet werden")
    argv = argv or sys.argv
    base_url = argv[0]
    handle = int(argv[1])
    params = parse_qs(argv[2][1:] if len(argv) > 2 and argv[2].startswith("?") else "")
    action = params.get("action", ["root"])[0]
    try:
        DinoTV(base_url, handle).dispatch(action, params)
    except Exception as exc:
        log("Unbehandelter Fehler: {!r}".format(exc), xbmc.LOGERROR)
        xbmcgui.Dialog().ok("DinoTV", "Ein unerwarteter Fehler ist aufgetreten. Details stehen im Kodi-Protokoll.")
