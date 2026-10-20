"""Every command is registered, and only the intended ones are open to everyone."""
import asyncio
import sys

import pytest

import main

PUBLIC = {"get-date", "event-category list", "archive-category list"}
COGS = ("events", "settings", "event_template", "join", "auto_thread", "recovery", "archive")


@pytest.fixture
def commands(tmp_path, monkeypatch):
    monkeypatch.setattr(main.config, "EVENTS_FILE", str(tmp_path / "e.json"))
    monkeypatch.setattr(main.config, "GUILD_SETTINGS_FILE", str(tmp_path / "s.json"))

    # load_extension replaces cogs.* in sys.modules with fresh copies, which would make
    # patch("cogs.x.y") in other tests hit a different module than the one their imports use.
    saved = {name: module for name, module in sys.modules.items() if name.startswith("cogs.")}

    async def load():
        bot = main.EventBot()
        for name in COGS:
            await bot.load_extension(f"cogs.{name}")
        return {c.qualified_name: c for c in bot.tree.walk_commands() if not hasattr(c, "commands")}

    yield asyncio.run(load())
    for name in [n for n in sys.modules if n.startswith("cogs.")]:
        del sys.modules[name]
    sys.modules.update(saved)


def test_all_expected_commands_exist(commands):
    assert set(commands) == {
        "create-event", "make-event", "set-date", "get-date", "set-field", "language",
        "event-category add", "event-category remove", "event-category list",
        "archive-category add", "archive-category remove", "archive-category list",
        "event-template edit", "event-template show", "event-template preview",
        "event-template reset", "event-template apply",
    }


def test_commands_that_change_or_reveal_config_require_admin_or_mod(commands):
    for name, command in commands.items():
        if name in PUBLIC:
            assert not command.checks, f"{name} should be public"
        else:
            assert command.checks, f"{name} has no permission check"
            assert command.default_permissions is not None, f"{name} is not hidden from regular members"


def test_all_commands_are_guild_only(commands):
    for name, command in commands.items():
        assert command.guild_only, name
