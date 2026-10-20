"""Fakes for Discord objects. Command and button callbacks are called directly with a fake
Interaction, so no connection to Discord is needed."""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from guild_settings import GuildSettingsStore
from storage import JsonEventStore

GUILD_ID = 1


def run(coro):
    # Views/modals need a running event loop even to be constructed.
    return asyncio.run(coro)


def http_error(status=500) -> discord.HTTPException:
    return discord.HTTPException(MagicMock(status=status, reason="boom"), "boom")


def not_found() -> discord.NotFound:
    return discord.NotFound(MagicMock(status=404, reason="missing"), "missing")


def make_category(category_id: int) -> MagicMock:
    category = MagicMock(spec=discord.CategoryChannel)
    category.id = category_id
    category.mention = f"<#{category_id}>"
    return category


def make_text_channel(channel_id: int = 5, category_id: int | None = 10, name: str = "fest") -> MagicMock:
    channel = MagicMock(spec=discord.TextChannel)
    channel.id = channel_id
    channel.name = name
    channel.category_id = category_id
    channel.mention = f"<#{channel_id}>"
    channel.guild = MagicMock(spec=discord.Guild)
    channel.guild.id = GUILD_ID
    channel.create_thread = AsyncMock()
    channel.send = AsyncMock()
    channel.get_partial_message = MagicMock()
    return channel


@pytest.fixture
def bot(tmp_path):
    bot = MagicMock()
    bot.store = JsonEventStore(str(tmp_path / "events.json"))
    bot.guild_settings = GuildSettingsStore(str(tmp_path / "settings.json"))
    bot.lang.return_value = "en"
    return bot


@pytest.fixture
def make_interaction():
    def factory(*, channel_id: int = 5, channel=None) -> MagicMock:
        interaction = MagicMock()
        interaction.guild_id = GUILD_ID
        interaction.guild = MagicMock(spec=discord.Guild)
        interaction.guild.id = GUILD_ID
        interaction.guild.get_channel.return_value = None
        interaction.channel_id = channel_id
        interaction.channel = channel
        interaction.user = MagicMock(spec=discord.Member)
        interaction.user.id = 42
        interaction.response.send_message = AsyncMock()
        interaction.response.defer = AsyncMock()
        interaction.response.send_modal = AsyncMock()
        interaction.followup.send = AsyncMock()
        return interaction

    return factory


def reply(interaction) -> str:
    """The text the bot answered with, whether directly or after defer()."""
    for send in (interaction.response.send_message, interaction.followup.send):
        if send.await_count:
            return send.await_args.args[0] if send.await_args.args else send.await_args.kwargs.get("content", "")
    raise AssertionError("the bot did not reply")


def was_ephemeral(interaction) -> bool:
    for send in (interaction.response.send_message, interaction.followup.send):
        if send.await_count:
            return send.await_args.kwargs.get("ephemeral", False)
    raise AssertionError("the bot did not reply")
