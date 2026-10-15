from urllib.request import Request, urlopen

from .channels import ChannelError, validate_stream_url
from .compat import KODI, log, xbmc, xbmcaddon, xbmcgui, xbmcplugin


class PlaybackError(RuntimeError):
    pass


def preflight(url, opener=urlopen):
    request = Request(url, headers={"User-Agent": "DinoTV/0.1.0", "Range": "bytes=0-1023"})
    try:
        with opener(request, timeout=10) as response:
            status = getattr(response, "status", 200)
            if status >= 400:
                raise PlaybackError("HTTP-Status {}".format(status))
    except Exception as exc:
        raise PlaybackError("Quelle ist derzeit nicht erreichbar: {}".format(exc)) from exc


def play(handle, channel):
    if not KODI:
        raise PlaybackError("Wiedergabe ist nur innerhalb von Kodi möglich")
    try:
        stream_type = validate_stream_url(channel.get("url", ""), channel.get("stream_type"))
    except ChannelError as exc:
        raise PlaybackError(str(exc)) from exc
    url = channel["url"]
    item = xbmcgui.ListItem(label=channel.get("name", "DinoTV"), path=url)
    item.setProperty("IsPlayable", "true")
    item.setInfo("video", {"title": channel.get("name", "DinoTV")})
    if stream_type == "hls":
        preflight(url)
        item.setMimeType("application/vnd.apple.mpegurl")
        item.setContentLookup(False)
    elif stream_type == "dash":
        _require_inputstream()
        preflight(url)
        item.setMimeType("application/dash+xml")
        item.setProperty("inputstream", "inputstream.adaptive")
        item.setProperty("inputstream.adaptive.manifest_type", "mpd")
        item.setContentLookup(False)
    elif stream_type == "m3u":
        preflight(url)
        item.setMimeType("audio/x-mpegurl")
    xbmcplugin.setResolvedUrl(handle, True, item)


def _require_inputstream():
    try:
        dependency = xbmcaddon.Addon("inputstream.adaptive")
        if not dependency.getAddonInfo("version"):
            raise RuntimeError()
    except Exception as exc:
        raise PlaybackError("Für MPEG-DASH muss InputStream Adaptive installiert und aktiviert sein.") from exc


def open_external(url, allow=True):
    if not KODI:
        raise PlaybackError("Externe Links können nur innerhalb von Kodi geöffnet werden")
    if not allow:
        raise PlaybackError("Das Öffnen externer Anbieterlinks ist in den Einstellungen deaktiviert.")
    if not url.startswith("https://") or any(char in url for char in "\r\n"):
        raise PlaybackError("Ungültiger oder unsicherer externer Link")
    if xbmc.getCondVisibility("System.Platform.Android"):
        xbmc.executebuiltin("StartAndroidActivity(,android.intent.action.VIEW,,{})".format(url))
        return
    xbmcgui.Dialog().textviewer("Offizieller Anbieterlink", url, usemono=True)
    log("Externer Link angezeigt: {}".format(url))
