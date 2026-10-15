"""Small Kodi compatibility boundary so domain modules remain locally testable."""

try:
    import xbmc  # type: ignore
    import xbmcaddon  # type: ignore
    import xbmcgui  # type: ignore
    import xbmcplugin  # type: ignore
    import xbmcvfs  # type: ignore
    KODI = True
except ImportError:  # pragma: no cover - used by the local test mode
    xbmc = xbmcaddon = xbmcgui = xbmcplugin = xbmcvfs = None
    KODI = False


def log(message, level=None):
    if KODI:
        xbmc.log("[DinoTV] {}".format(message), level or xbmc.LOGINFO)
    else:
        print("[DinoTV] {}".format(message))


def addon():
    if not KODI:
        raise RuntimeError("Kodi API ist außerhalb von Kodi nicht verfügbar")
    return xbmcaddon.Addon()


def profile_path():
    if KODI:
        return xbmcvfs.translatePath(addon().getAddonInfo("profile"))
    import os
    return os.environ.get("DINOTV_PROFILE", os.path.join(os.getcwd(), "dinotv-data"))

