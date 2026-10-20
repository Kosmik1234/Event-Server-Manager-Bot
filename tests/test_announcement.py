import asyncio
from unittest.mock import AsyncMock, MagicMock

import discord

from cogs.events import build_embed, refresh_announcement
from guild_settings import GuildSettingsStore
from storage import Event


def make_event(**kw) -> Event:
    return Event(channel_id=5, guild_id=1, title="Fest", date="15.11.2026", location="Warsaw", description="Fun", **kw)


def test_embed_uses_default_template_without_custom_one():
    embed = build_embed(make_event(), "en")
    assert embed.description == "# Fest\nFun\n\n**📅 When:** 15.11.2026\n**📍 Where:** Warsaw"


def test_embed_uses_custom_template():
    embed = build_embed(make_event(extra={"tickets": "http://x"}), "en", "**{title}**\n🎟 {tickets}")
    assert embed.description == "**Fest**\n🎟 http://x"


def _bot_and_guild(tmp_path, template=None):
    settings = GuildSettingsStore(str(tmp_path / "s.json"))
    if template:
        settings.set_template(1, template)
    partial = MagicMock(edit=AsyncMock())
    channel = MagicMock()
    channel.get_partial_message.return_value = partial
    guild = MagicMock(id=1)
    guild.get_channel.return_value = channel
    bot = MagicMock(guild_settings=settings)
    bot.lang.return_value = "en"
    return bot, guild, partial


def test_refresh_edits_announcement_with_server_template(tmp_path):
    bot, guild, partial = _bot_and_guild(tmp_path, "{title} / {date}")
    asyncio.run(refresh_announcement(bot, make_event(message_id=7), guild))
    assert partial.edit.await_args.kwargs["embed"].description == "Fest / 15.11.2026"


def test_refresh_skips_channels_without_announcement(tmp_path):
    bot, guild, partial = _bot_and_guild(tmp_path)
    asyncio.run(refresh_announcement(bot, make_event(message_id=None), guild))
    partial.edit.assert_not_awaited()


def test_refresh_survives_discord_errors(tmp_path):
    bot, guild, partial = _bot_and_guild(tmp_path)
    partial.edit.side_effect = discord.HTTPException(MagicMock(status=500, reason="boom"), "boom")
    asyncio.run(refresh_announcement(bot, make_event(message_id=7), guild))  # must not raise
