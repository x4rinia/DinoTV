import json
import os
import tempfile
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen


SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"


class ScheduleError(RuntimeError):
    pass


class ScheduleClient:
    def __init__(self, cache_dir, opener=urlopen, now=time.time):
        self.cache_path = os.path.join(cache_dir, "schedule-cache.json")
        self.opener = opener
        self.now = now

    def get_games(self, days=14, force=False):
        if not force:
            cached = self._read_cache(max_age=1800)
            if cached is not None:
                return cached
        today = datetime.fromtimestamp(self.now(), timezone.utc).date()
        final_day = today + timedelta(days=days)
        try:
            games_by_id = {}
            for year in range(today.year, final_day.year + 1):
                query = urlencode({"dates": str(year), "limit": 1000})
                request = Request(SCOREBOARD_URL + "?" + query, headers={"User-Agent": "DinoTV/0.1.0 (+https://github.com/x4rinia/DinoTV)"})
                with self.opener(request, timeout=12) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                for game in parse_scoreboard(payload):
                    kickoff = datetime.fromisoformat(game["kickoff"]).astimezone(timezone.utc).date() if game["kickoff"] else None
                    if kickoff is not None and today <= kickoff <= final_day:
                        games_by_id[game["id"]] = game
            games = sorted(games_by_id.values(), key=lambda item: item["kickoff"])
            self._write_cache(games)
            return games
        except Exception as exc:
            stale = self._read_cache(max_age=None)
            if stale is not None:
                return stale
            raise ScheduleError("NFL-Spielplan konnte nicht geladen werden: {}".format(exc)) from exc

    def _read_cache(self, max_age):
        try:
            if max_age is not None and self.now() - os.path.getmtime(self.cache_path) > max_age:
                return None
            with open(self.cache_path, "r", encoding="utf-8") as handle:
                value = json.load(handle)
            return value if isinstance(value, list) else None
        except (OSError, ValueError, json.JSONDecodeError):
            return None

    def _write_cache(self, games):
        directory = os.path.dirname(self.cache_path)
        os.makedirs(directory, exist_ok=True)
        fd, path = tempfile.mkstemp(prefix="schedule-", suffix=".json", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(games, handle, ensure_ascii=False, indent=2)
            os.replace(path, self.cache_path)
        finally:
            if os.path.exists(path):
                os.unlink(path)


def parse_scoreboard(payload):
    games = []
    for event in payload.get("events", []):
        competition = (event.get("competitions") or [{}])[0]
        competitors = competition.get("competitors", [])
        home = next((item for item in competitors if item.get("homeAway") == "home"), {})
        away = next((item for item in competitors if item.get("homeAway") == "away"), {})
        if not home or not away:
            continue
        broadcasts = []
        for broadcast in competition.get("broadcasts", []):
            broadcasts.extend(str(name) for name in broadcast.get("names", []) if name)
        for geo in competition.get("geoBroadcasts", []):
            media = geo.get("media", {})
            if media.get("shortName"):
                broadcasts.append(str(media["shortName"]))
        start = _parse_datetime(event.get("date", ""))
        status = event.get("status", {}).get("type", {})
        games.append({
            "id": str(event.get("id", "")),
            "name": event.get("name") or "{} vs. {}".format(_team_name(away), _team_name(home)),
            "kickoff": start.isoformat() if start else "",
            "kickoff_display": start.strftime("%a, %d.%m.%Y %H:%M Uhr") if start else "Zeit unbekannt",
            "home": _team(home), "away": _team(away),
            "status": status.get("description") or status.get("detail") or "Status unbekannt",
            "completed": bool(status.get("completed")),
            "broadcasts": sorted(set(broadcasts), key=str.casefold),
        })
    return sorted(games, key=lambda item: item["kickoff"])


def _parse_datetime(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        return _to_berlin(parsed)
    except ValueError:
        return None


def _to_berlin(utc_value):
    """Convert UTC to Europe/Berlin without relying on an OS tzdata package.

    EU daylight saving time runs from 01:00 UTC on the final Sunday in March
    until 01:00 UTC on the final Sunday in October.
    """
    year = utc_value.year
    start = datetime(year, 3, _last_sunday(year, 3), 1, tzinfo=timezone.utc)
    end = datetime(year, 10, _last_sunday(year, 10), 1, tzinfo=timezone.utc)
    offset = 2 if start <= utc_value < end else 1
    return utc_value.astimezone(timezone(timedelta(hours=offset), name="Europe/Berlin"))


def _last_sunday(year, month):
    if month == 12:
        following = datetime(year + 1, 1, 1)
    else:
        following = datetime(year, month + 1, 1)
    last_day = following - timedelta(days=1)
    return last_day.day - ((last_day.weekday() + 1) % 7)


def _team_name(competitor):
    return competitor.get("team", {}).get("displayName", "Unbekannt")


def _team(competitor):
    team = competitor.get("team", {})
    logos = team.get("logos") or []
    return {
        "id": str(team.get("id", "")), "name": team.get("displayName", "Unbekannt"),
        "abbr": team.get("abbreviation", ""), "logo": logos[0].get("href", "") if logos else "",
        "score": str(competitor.get("score", "")),
    }
