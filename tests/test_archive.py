"""The hourly sweep, run against fake Discord objects."""
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import AsyncMock, MagicMock

import discord

import config
from cogs.archive import ArchiveSweepCog
from guild_settings import GuildSettingsStore
from storage import Event, JsonEventStore

GUILD, EVENT_CAT, ARCHIVE_CAT, CHANNEL = 1, 10, 99, 500
PAST, FUTURE = "01.01.2000", "01.01.2999"


def run_sweep(tmp_path, date, *, archive_exists=True, archive_link=True, in_category=True, edit_error=None):
    store = JsonEventStore(str(tmp_path / "events.json"))
    store.save(Event(channel_id=CHANNEL, guild_id=GUILD, title="Fest", date=date))
    settings = GuildSettingsStore(str(tmp_path / "settings.json"))
    if archive_link:
        settings.add_category(GUILD, EVENT_CAT)
        settings.set_archive(GUILD, EVENT_CAT, ARCHIVE_CAT)

    archive = MagicMock(spec=discord.CategoryChannel)
    archive.name = "archive"
    channel = MagicMock()
    channel.name = "fest"
    channel.category_id = EVENT_CAT if in_category else None
    channel.edit = AsyncMock(side_effect=edit_error)
    guild = MagicMock()
    guild.id = GUILD
    guild.get_channel.side_effect = lambda cid: {CHANNEL: channel, ARCHIVE_CAT: archive if archive_exists else None}.get(cid)
    bot = MagicMock()
    bot.store, bot.guild_settings = store, settings
    bot.get_guild.return_value = guild

    asyncio.run(ArchiveSweepCog(bot).sweep.coro(ArchiveSweepCog(bot)))
    return channel, archive


def test_past_event_is_moved_to_archive(tmp_path):
    channel, archive = run_sweep(tmp_path, PAST)
    channel.edit.assert_awaited_once()
    assert channel.edit.await_args.kwargs["category"] is archive


def test_future_event_stays(tmp_path):
    channel, _ = run_sweep(tmp_path, FUTURE)
    channel.edit.assert_not_awaited()


def test_event_happening_today_is_not_archived_yet(tmp_path):
    today = datetime.now(ZoneInfo(config.TIMEZONE)).strftime("%d.%m.%Y")
    channel, _ = run_sweep(tmp_path, today)
    channel.edit.assert_not_awaited()


def test_unreadable_or_empty_date_is_never_archived(tmp_path):
    for date in ("", "wkrótce", "15/11/2026"):
        channel, _ = run_sweep(tmp_path, date)
        channel.edit.assert_not_awaited()


def test_no_archive_linked(tmp_path):
    channel, _ = run_sweep(tmp_path, PAST, archive_link=False)
    channel.edit.assert_not_awaited()


def test_archive_category_was_deleted(tmp_path):
    channel, _ = run_sweep(tmp_path, PAST, archive_exists=False)
    channel.edit.assert_not_awaited()


def test_channel_without_category(tmp_path):
    channel, _ = run_sweep(tmp_path, PAST, in_category=False)
    channel.edit.assert_not_awaited()


def test_move_failure_is_swallowed(tmp_path):
    # e.g. archive category is full; the sweep must keep going instead of crashing
    response = MagicMock(status=400, reason="full")
    channel, _ = run_sweep(tmp_path, PAST, edit_error=discord.HTTPException(response, "full"))
    channel.edit.assert_awaited_once()
