"""Per-guild configuration (currently: which categories event channels may be
created in). Kept in its own JSON file, keyed by guild ID, separate from event data.
"""
import json
from pathlib import Path


class GuildSettingsStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._settings: dict[str, dict] = {}
        if self.path.exists():
            self._settings = json.loads(self.path.read_text(encoding="utf-8"))

    def _flush(self) -> None:
        self.path.write_text(json.dumps(self._settings, indent=2), encoding="utf-8")

    def get_language(self, guild_id: int) -> str | None:
        """None if the server never chose one."""
        return self._settings.get(str(guild_id), {}).get("language")

    def set_language(self, guild_id: int, language: str) -> None:
        self._settings.setdefault(str(guild_id), {})["language"] = language
        self._flush()

    def get_categories(self, guild_id: int) -> list[int]:
        return self._settings.get(str(guild_id), {}).get("event_categories", [])

    def add_category(self, guild_id: int, category_id: int) -> bool:
        """Returns False if the category was already allowed."""
        categories = self._settings.setdefault(str(guild_id), {}).setdefault("event_categories", [])
        if category_id in categories:
            return False
        categories.append(category_id)
        self._flush()
        return True

    def remove_category(self, guild_id: int, category_id: int) -> bool:
        """Returns False if the category wasn't in the list."""
        categories = self._settings.setdefault(str(guild_id), {}).setdefault("event_categories", [])
        if category_id not in categories:
            return False
        categories.remove(category_id)
        self._settings[str(guild_id)].get("archives", {}).pop(str(category_id), None)  # its archive link is meaningless now
        self._flush()
        return True

    # archives: event category ID -> archive category ID. Several event categories may share
    # one archive; each event category has at most one.
    def get_archives(self, guild_id: int) -> dict[int, int]:
        raw = self._settings.get(str(guild_id), {}).get("archives", {})
        return {int(source): target for source, target in raw.items()}

    def set_archive(self, guild_id: int, source_id: int, archive_id: int) -> bool:
        """Returns False if the event category already has an archive."""
        archives = self._settings.setdefault(str(guild_id), {}).setdefault("archives", {})
        if str(source_id) in archives:
            return False
        archives[str(source_id)] = archive_id
        self._flush()
        return True

    def remove_archive(self, guild_id: int, source_id: int) -> bool:
        """Returns False if the event category had no archive."""
        archives = self._settings.get(str(guild_id), {}).get("archives", {})
        if archives.pop(str(source_id), None) is None:
            return False
        self._flush()
        return True
