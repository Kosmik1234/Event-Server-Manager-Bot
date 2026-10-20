import json

from storage import Event, JsonEventStore


def make_event(channel_id=1, **kw) -> Event:
    return Event(channel_id=channel_id, guild_id=10, title="Fest", **kw)


def test_save_and_get(tmp_path):
    store = JsonEventStore(str(tmp_path / "events.json"))
    store.save(make_event(1, thread_id=100))
    assert store.get_by_channel(1).title == "Fest"
    assert store.get_by_thread(100).channel_id == 1
    assert store.get_by_channel(2) is None
    assert store.get_by_thread(999) is None


def test_persists_across_instances(tmp_path):
    path = str(tmp_path / "events.json")
    JsonEventStore(path).save(make_event(1, date="15.11.2026", extra={"tickets": "http://x"}))
    loaded = JsonEventStore(path).get_by_channel(1)
    assert loaded.date == "15.11.2026"
    assert loaded.extra == {"tickets": "http://x"}


def test_delete_and_all(tmp_path):
    store = JsonEventStore(str(tmp_path / "events.json"))
    store.save(make_event(1))
    store.save(make_event(2))
    store.delete(1)
    store.delete(404)  # deleting an unknown event is a no-op
    assert [e.channel_id for e in store.all()] == [2]


def test_file_from_before_extra_existed_still_loads(tmp_path):
    path = tmp_path / "events.json"
    path.write_text(json.dumps({"1": {"channel_id": 1, "guild_id": 10, "title": "Old"}}), encoding="utf-8")
    event = JsonEventStore(str(path)).get_by_channel(1)
    assert event.title == "Old"
    assert event.extra == {}


def test_extra_is_not_shared_between_events():
    a, b = make_event(1), make_event(2)
    a.extra["k"] = "v"
    assert b.extra == {}


def test_creates_missing_directory(tmp_path):
    store = JsonEventStore(str(tmp_path / "nested" / "dir" / "events.json"))
    store.save(make_event(1))
    assert (tmp_path / "nested" / "dir" / "events.json").exists()
