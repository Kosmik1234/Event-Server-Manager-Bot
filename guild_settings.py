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
        self._flush()
        return True
