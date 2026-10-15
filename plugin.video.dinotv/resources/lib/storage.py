import json
import os
import tempfile
from copy import deepcopy


DEFAULT_DATA = {
    "schema_version": 1,
    "favorite_channels": [],
    "channel_order": [],
    "history": [],
    "user_channels": [],
}


class Storage:
    def __init__(self, profile_dir):
        self.profile_dir = profile_dir
        self.path = os.path.join(profile_dir, "userdata.json")

    def load(self):
        os.makedirs(self.profile_dir, exist_ok=True)
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if not isinstance(data, dict):
                raise ValueError("Root element must be an object")
        except (OSError, ValueError, json.JSONDecodeError):
            data = {}
        result = deepcopy(DEFAULT_DATA)
        for key in result:
            if key in data and isinstance(data[key], type(result[key])):
                result[key] = data[key]
        return result

    def save(self, data):
        os.makedirs(self.profile_dir, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(prefix="dinotv-", suffix=".json", dir=self.profile_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
            os.replace(temp_path, self.path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def toggle_favorite(self, channel_id):
        data = self.load()
        values = data["favorite_channels"]
        if channel_id in values:
            values.remove(channel_id)
            enabled = False
        else:
            values.append(channel_id)
            enabled = True
        self.save(data)
        return enabled

    def add_history(self, channel, limit=20):
        data = self.load()
        entry = {key: channel.get(key, "") for key in ("id", "name", "stream_type", "url", "status")}
        data["history"] = [item for item in data["history"] if item.get("id") != entry["id"]]
        if limit > 0:
            data["history"].insert(0, entry)
            data["history"] = data["history"][:limit]
        else:
            data["history"] = []
        self.save(data)

    def add_user_channel(self, channel):
        data = self.load()
        data["user_channels"] = [item for item in data["user_channels"] if item.get("id") != channel["id"]]
        data["user_channels"].append(channel)
        self.save(data)

    def remove_user_channel(self, channel_id):
        data = self.load()
        data["user_channels"] = [item for item in data["user_channels"] if item.get("id") != channel_id]
        data["favorite_channels"] = [item for item in data["favorite_channels"] if item != channel_id]
        data["channel_order"] = [item for item in data["channel_order"] if item != channel_id]
        self.save(data)

    def move_channel(self, channel_id, direction):
        data = self.load()
        order = data["channel_order"]
        if channel_id not in order:
            order.append(channel_id)
        index = order.index(channel_id)
        target = max(0, min(len(order) - 1, index + direction))
        order[index], order[target] = order[target], order[index]
        self.save(data)

    def reset(self):
        self.save(deepcopy(DEFAULT_DATA))

    def export_safe(self, favorite_teams=""):
        data = self.load()
        exported = {
            "schema_version": 1,
            "favorite_channels": data["favorite_channels"],
            "channel_order": data["channel_order"],
            "favorite_teams": favorite_teams,
            "notice": "Persönliche Stream-URLs und Verlauf wurden absichtlich nicht exportiert.",
        }
        path = os.path.join(self.profile_dir, "dinotv-settings-export.json")
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(exported, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        return path

    def import_safe(self, path):
        with open(path, "r", encoding="utf-8") as handle:
            imported = json.load(handle)
        if imported.get("schema_version") != 1:
            raise ValueError("Nicht unterstützte Exportversion")
        data = self.load()
        data["favorite_channels"] = _string_list(imported.get("favorite_channels", []))
        data["channel_order"] = _string_list(imported.get("channel_order", []))
        self.save(data)
        return str(imported.get("favorite_teams", ""))


def _string_list(value):
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("Ungültige Liste im Export")
    return value
