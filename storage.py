"""Event persistence.

The bot only talks to the `EventStore` interface. To move to SQLite/Postgres
later, write another class with the same methods and swap it in main.py.
"""
import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Event:
    channel_id: int
    guild_id: int
    # Details are only known for events made with /create-event; for channels created by
    # hand, title is the channel name and the rest stay empty.
    title: str = ""
    date: str = ""
    location: str = ""
    description: str = ""
    creator_id: int | None = None
    message_id: int | None = None  # the announcement embed (set after it's posted)
    thread_id: int | None = None  # the updates thread (set by the auto-thread listener)
    join_message_id: int | None = None  # pinned message with the Join/Leave buttons and participant count
    extra: dict[str, str] = field(default_factory=dict)  # custom fields for announcement templates (/set-field)


class EventStore(ABC):
    @abstractmethod
    def save(self, event: Event) -> None: ...

    @abstractmethod
    def get_by_channel(self, channel_id: int) -> Event | None: ...

    @abstractmethod
    def get_by_thread(self, thread_id: int) -> Event | None: ...

    @abstractmethod
    def delete(self, channel_id: int) -> None: ...

    @abstractmethod
    def all(self) -> list[Event]: ...


class JsonEventStore(EventStore):
    """Keeps all events in one JSON file, keyed by channel ID. Fine for small bots."""

    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._events: dict[str, Event] = {}
        if self.path.exists():
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self._events = {k: Event(**v) for k, v in raw.items()}

    def _flush(self) -> None:
        data = {k: asdict(v) for k, v in self._events.items()}
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def save(self, event: Event) -> None:
        self._events[str(event.channel_id)] = event
        self._flush()

    def get_by_channel(self, channel_id: int) -> Event | None:
        return self._events.get(str(channel_id))

    def get_by_thread(self, thread_id: int) -> Event | None:
        return next((e for e in self._events.values() if e.thread_id == thread_id), None)

    def delete(self, channel_id: int) -> None:
        self._events.pop(str(channel_id), None)
        self._flush()

    def all(self) -> list[Event]:
        return list(self._events.values())
