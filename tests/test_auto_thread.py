"""Thread + pinned message creation and the listeners that keep the counter fresh."""
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from cogs.auto_thread import AutoThreadCog, setup_event_channel
from conftest import GUILD_ID, http_error, make_text_channel, run
from storage import Event


def channel_with_thread(thread_id=77, join_message_id=88):
    channel = make_text_channel()
    channel.create_thread.return_value = MagicMock(id=thread_id, name="thread")
    join_message = MagicMock(id=join_message_id, pin=AsyncMock())
    channel.send.return_value = join_message
    return channel, join_message


def test_creates_private_thread_and_pinned_join_message(bot):
    channel, join_message = channel_with_thread()
    assert run(setup_event_channel(bot, channel)) == "ok"

    kwargs = channel.create_thread.await_args.kwargs
    assert kwargs["name"] == "fest-participants"
    assert kwargs["type"] == discord.ChannelType.private_thread
    assert kwargs["invitable"] is False and kwargs["slowmode_delay"] == 300
    join_message.pin.assert_awaited_once()

    event = bot.store.get_by_channel(channel.id)
    assert (event.thread_id, event.join_message_id, event.title) == (77, 88, "fest")


def test_thread_name_follows_server_language(bot):
    bot.lang.return_value = "pl"
    channel, _ = channel_with_thread()
    run(setup_event_channel(bot, channel))
    assert channel.create_thread.await_args.kwargs["name"] == "fest-uczestnicy"


def test_keeps_details_saved_by_create_event(bot):
    bot.store.save(Event(channel_id=5, guild_id=GUILD_ID, title="Fest", date="15.11.2026", message_id=7, creator_id=42))
    channel, _ = channel_with_thread()
    run(setup_event_channel(bot, channel))
    event = bot.store.get_by_channel(5)
    assert (event.date, event.message_id, event.creator_id, event.thread_id) == ("15.11.2026", 7, 42, 77)


def test_nobody_is_added_to_the_thread_automatically(bot):
    channel, _ = channel_with_thread()
    thread = channel.create_thread.return_value
    run(setup_event_channel(bot, channel))
    thread.add_user.assert_not_called()


def test_missing_permissions(bot):
    channel = make_text_channel()
    channel.create_thread.side_effect = discord.Forbidden(MagicMock(status=403, reason="no"), "no")
    assert run(setup_event_channel(bot, channel)) == "forbidden"
    assert bot.store.get_by_channel(channel.id) is None


def test_api_error_creating_thread(bot):
    channel = make_text_channel()
    channel.create_thread.side_effect = http_error()
    assert run(setup_event_channel(bot, channel)) == "failed"
    assert bot.store.get_by_channel(channel.id) is None


def test_event_is_stored_even_if_join_message_fails(bot):
    channel, _ = channel_with_thread()
    channel.send.side_effect = http_error()
    assert run(setup_event_channel(bot, channel)) == "ok"
    event = bot.store.get_by_channel(channel.id)
    assert event.thread_id == 77 and event.join_message_id is None


# --- listeners -------------------------------------------------------------

def test_channel_create_listener_only_acts_in_event_categories(bot):
    bot.guild_settings.add_category(GUILD_ID, 10)
    cog = AutoThreadCog(bot)
    with patch("cogs.auto_thread.setup_event_channel", new=AsyncMock()) as setup:
        run(cog.on_guild_channel_create(make_text_channel(category_id=11)))  # other category
        run(cog.on_guild_channel_create(make_text_channel(category_id=None)))  # no category
        run(cog.on_guild_channel_create(MagicMock(spec=discord.VoiceChannel, category_id=10)))  # not text
        setup.assert_not_awaited()

        channel = make_text_channel(category_id=10)
        run(cog.on_guild_channel_create(channel))
        setup.assert_awaited_once_with(bot, channel)


def test_member_join_and_raw_remove_recompute_the_counter(bot):
    thread = MagicMock(guild=MagicMock())
    bot.get_channel.return_value = thread
    cog = AutoThreadCog(bot)
    with patch("cogs.auto_thread.update_participant_count", new=AsyncMock()) as update:
        run(cog.on_thread_member_join(MagicMock(thread_id=77)))
        run(cog.on_raw_thread_member_remove(MagicMock(thread_id=77)))
    assert update.await_count == 2
    bot.get_channel.assert_called_with(77)


def test_membership_change_for_unknown_thread_is_ignored(bot):
    bot.get_channel.return_value = None
    cog = AutoThreadCog(bot)
    with patch("cogs.auto_thread.update_participant_count", new=AsyncMock()) as update:
        run(cog.on_raw_thread_member_remove(MagicMock(thread_id=77)))
    update.assert_not_awaited()
