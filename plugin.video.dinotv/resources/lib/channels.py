import hashlib
import json
import os
import re
from urllib.parse import urlparse


REQUIRED_FIELDS = {"id", "name", "category", "provider", "stream_type", "url", "status"}
PLAYABLE_TYPES = {"hls", "dash", "m3u", "plugin"}
VALID_TYPES = PLAYABLE_TYPES | {"external", "none"}
VALID_STATUSES = {"playable", "official_external", "subscription_required", "external_only", "unsupported"}


class ChannelError(ValueError):
    pass


def load_catalog(path):
    with open(path, "r", encoding="utf-8") as handle:
        document = json.load(handle)
    channels = document.get("channels", [])
    validate_catalog(channels)
    return channels


def validate_catalog(channels):
    if not isinstance(channels, list):
        raise ChannelError("channels muss eine Liste sein")
    seen = set()
    for channel in channels:
        missing = REQUIRED_FIELDS.difference(channel)
        if missing:
            raise ChannelError("Fehlende Felder: {}".format(", ".join(sorted(missing))))
        if channel["id"] in seen:
            raise ChannelError("Doppelte Sender-ID: {}".format(channel["id"]))
        seen.add(channel["id"])
        if channel["stream_type"] not in VALID_TYPES:
            raise ChannelError("Unbekannter Streamtyp: {}".format(channel["stream_type"]))
        if channel["status"] not in VALID_STATUSES:
            raise ChannelError("Unbekannter Status: {}".format(channel["status"]))
        if channel["status"] == "playable":
            validate_stream_url(channel["url"], channel["stream_type"])
        if channel["stream_type"] == "external" and channel["url"] and not channel["url"].startswith("https://"):
            raise ChannelError("Externe Links müssen HTTPS verwenden")
    return True


def detect_stream_type(url):
    lower = url.lower().split("?", 1)[0]
    if url.startswith("plugin://"):
        return "plugin"
    if lower.endswith(".m3u8"):
        return "hls"
    if lower.endswith(".mpd"):
        return "dash"
    if lower.endswith(".m3u"):
        return "m3u"
    return ""


def validate_stream_url(url, stream_type=None):
    if not isinstance(url, str) or not url.strip():
        raise ChannelError("Leere Stream-URL")
    detected = stream_type or detect_stream_type(url)
    if detected not in PLAYABLE_TYPES:
        raise ChannelError("Nur HLS, DASH, M3U und Kodi-Plugin-URLs werden unterstützt")
    if detected == "plugin":
        if not url.startswith("plugin://"):
            raise ChannelError("Ungültige Kodi-Plugin-URL")
    else:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ChannelError("Netzwerkstreams müssen eine vollständige HTTPS-Adresse verwenden")
    return detected


def user_channel(name, url):
    stream_type = validate_stream_url(url)
    digest = hashlib.sha256((name + "\0" + url).encode("utf-8")).hexdigest()[:16]
    return {
        "id": "user-{}".format(digest), "name": name.strip(), "country": "", "language": "",
        "category": "custom", "provider": "Eigene autorisierte Quelle", "stream_type": stream_type,
        "url": url.strip(), "epg_id": "", "drm": "vom Benutzer festgelegt", "access": "Eigene Quelle",
        "status": "playable", "last_verified": "nicht automatisch geprüft",
    }


def parse_m3u(text):
    result, pending = [], {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#EXTINF:"):
            name = line.rsplit(",", 1)[-1].strip() or "M3U-Sender"
            logo_match = re.search(r'tvg-logo="([^"]*)"', line)
            pending = {"name": name, "logo": logo_match.group(1) if logo_match else ""}
        elif not line.startswith("#") and pending:
            try:
                channel = user_channel(pending["name"], line)
            except ChannelError:
                pending = {}
                continue
            channel["logo"] = pending.get("logo", "")
            result.append(channel)
            pending = {}
    return result


def load_m3u(path):
    if not path or not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8-sig", errors="replace") as handle:
        return parse_m3u(handle.read())


def merge_channels(builtin, user_channels, playlist_channels=()):
    merged = {}
    for channel in list(builtin) + list(user_channels) + list(playlist_channels):
        merged[channel["id"]] = channel
    return list(merged.values())


def apply_order(channels, order):
    positions = {channel_id: index for index, channel_id in enumerate(order)}
    return sorted(channels, key=lambda item: (positions.get(item["id"], len(positions)), item["name"].casefold()))
