import pytest

from guild_settings import GuildSettingsStore


@pytest.fixture
def path(tmp_path):
    return str(tmp_path / "settings.json")


def test_categories_add_remove(path):
    s = GuildSettingsStore(path)
    assert s.get_categories(1) == []
    assert s.add_category(1, 10) is True
    assert s.add_category(1, 10) is False  # duplicate
    assert s.get_categories(1) == [10]
    assert s.remove_category(1, 10) is True
    assert s.remove_category(1, 10) is False


def test_guilds_are_independent(path):
    s = GuildSettingsStore(path)
    s.add_category(1, 10)
    assert s.get_categories(2) == []


def test_archive_one_per_event_category_but_archive_can_be_shared(path):
    s = GuildSettingsStore(path)
    assert s.set_archive(1, 10, 99) is True
    assert s.set_archive(1, 10, 98) is False  # already has one
    assert s.set_archive(1, 11, 99) is True  # shared archive
    assert s.get_archives(1) == {10: 99, 11: 99}  # keys come back as ints
    assert s.remove_archive(1, 10) is True
    assert s.remove_archive(1, 10) is False


def test_removing_event_category_drops_its_archive_link(path):
    s = GuildSettingsStore(path)
    s.add_category(1, 10)
    s.set_archive(1, 10, 99)
    s.remove_category(1, 10)
    assert s.get_archives(1) == {}


def test_language(path):
    s = GuildSettingsStore(path)
    assert s.get_language(1) is None
    s.set_language(1, "pl")
    assert s.get_language(1) == "pl"


def test_template_set_and_reset(path):
    s = GuildSettingsStore(path)
    assert s.get_template(1) is None
    assert s.reset_template(1) is False
    s.set_template(1, "# {title}")
    assert s.get_template(1) == "# {title}"
    assert s.reset_template(1) is True
    assert s.get_template(1) is None


def test_everything_persists(path):
    s = GuildSettingsStore(path)
    s.add_category(1, 10)
    s.set_archive(1, 10, 99)
    s.set_language(1, "pl")
    s.set_template(1, "x {title}")
    s2 = GuildSettingsStore(path)
    assert s2.get_categories(1) == [10]
    assert s2.get_archives(1) == {10: 99}
    assert s2.get_language(1) == "pl"
    assert s2.get_template(1) == "x {title}"
