"""Join/Leave buttons and the participant counter."""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from cogs.join import JoinButton, LeaveButton, counter_text, get_participants_count, join_view, update_participant_count
from conftest import http_error, not_found, reply, run, was_ephemeral
from i18n import t
from storage import Event


def make_thread(thread_id=77, members=3):
    thread = MagicMock(spec=discord.Thread)
    thread.id = thread_id
    thread.mention = f"<#{thread_id}>"
    thread.add_user = AsyncMock()
    thread.remove_user = AsyncMock()
    thread.fetch_members = AsyncMock(return_value=[MagicMock()] * members)
    thread.parent = MagicMock()
    return thread


# --- buttons ---------------------------------------------------------------

@pytest.mark.parametrize("button, action, ok_key", [
    (JoinButton, "add_user", "joined"), (LeaveButton, "remove_user", "left"),
])
def test_click_uses_cached_thread(button, action, ok_key, make_interaction):
    thread = make_thread()
    i = make_interaction()
    i.client.lang.return_value = "en"
    i.guild.get_thread.return_value = thread
    run(button(77, "en").callback(i))
    getattr(thread, action).assert_awaited_once_with(i.user)
    assert reply(i) == t("en", ok_key, thread=thread.mention)
    assert was_ephemeral(i)


@pytest.mark.parametrize("button, action", [(JoinButton, "add_user"), (LeaveButton, "remove_user")])
def test_click_fetches_thread_when_not_cached(button, action, make_interaction):
    thread = make_thread()
    i = make_interaction()
    i.client.lang.return_value = "en"
    i.guild.get_thread.return_value = None
    i.guild.fetch_channel = AsyncMock(return_value=thread)
    run(button(77, "en").callback(i))
    i.guild.fetch_channel.assert_awaited_once_with(77)
    getattr(thread, action).assert_awaited_once()


@pytest.mark.parametrize("button, gone_after", [(JoinButton, "add_user"), (LeaveButton, "remove_user")])
def test_click_when_thread_was_deleted(button, gone_after, make_interaction):
    thread = make_thread()
    getattr(thread, gone_after).side_effect = not_found()
    i = make_interaction()
    i.client.lang.return_value = "en"
    i.guild.get_thread.return_value = thread
    run(button(77, "en").callback(i))
    assert reply(i) == t("en", "thread_gone")


@pytest.mark.parametrize("button, action, key", [
    (JoinButton, "add_user", "join_failed"), (LeaveButton, "remove_user", "leave_failed"),
])
def test_click_when_discord_fails(button, action, key, make_interaction):
    thread = make_thread()
    getattr(thread, action).side_effect = http_error()
    i = make_interaction()
    i.client.lang.return_value = "en"
    i.guild.get_thread.return_value = thread
    run(button(77, "en").callback(i))
    assert reply(i) == t("en", key)


def test_button_labels_follow_language():
    assert JoinButton(1, "pl").item.label == t("pl", "join_label")
    assert LeaveButton(1, "en").item.label == t("en", "leave_label")


def test_custom_id_format_is_stable():
    """Old messages keep their buttons across restarts only if this format never changes."""
    assert JoinButton(123, "en").item.custom_id == "join-event:123"
    assert LeaveButton(123, "en").item.custom_id == "leave-event:123"
    match = JoinButton.__discord_ui_compiled_template__.fullmatch("join-event:123")
    assert match["thread_id"] == "123"
    assert LeaveButton.__discord_ui_compiled_template__.fullmatch("leave-event:123")
    assert not JoinButton.__discord_ui_compiled_template__.fullmatch("leave-event:123")


def test_from_custom_id_rebuilds_the_button(make_interaction):
    i = make_interaction()
    i.client.lang.return_value = "pl"
    match = LeaveButton.__discord_ui_compiled_template__.fullmatch("leave-event:123")
    button = run(LeaveButton.from_custom_id(i, MagicMock(), match))
    assert button.thread_id == 123 and button.item.label == t("pl", "leave_label")


def test_join_view_has_both_buttons_that_never_expire():
    async def go():
        return join_view(77, "en")

    view = run(go())
    assert view.timeout is None
    assert [c.custom_id for c in view.children] == ["join-event:77", "leave-event:77"]


# --- participant counter ---------------------------------------------------

def test_count_excludes_the_bot():
    assert run(get_participants_count(make_thread(members=4))) == 3
    assert run(get_participants_count(make_thread(members=1))) == 0
    assert run(get_participants_count(make_thread(members=0))) == 0  # never negative


def test_count_is_none_when_discord_fails():
    thread = make_thread()
    thread.fetch_members.side_effect = http_error()
    assert run(get_participants_count(thread)) is None


def test_update_edits_the_pinned_message(bot):
    bot.store.save(Event(channel_id=5, guild_id=1, thread_id=77, join_message_id=88))
    thread = make_thread(members=4)
    partial = MagicMock(edit=AsyncMock())
    thread.parent.get_partial_message.return_value = partial
    run(update_participant_count(bot.store, thread, "en"))
    thread.parent.get_partial_message.assert_called_once_with(88)
    partial.edit.assert_awaited_once_with(content=counter_text(3, "en"))


def test_update_ignores_untracked_threads_and_events_without_join_message(bot):
    thread = make_thread()
    run(update_participant_count(bot.store, thread, "en"))
    bot.store.save(Event(channel_id=5, guild_id=1, thread_id=77))  # no join_message_id
    run(update_participant_count(bot.store, thread, "en"))
    thread.fetch_members.assert_not_awaited()


def test_update_survives_discord_errors(bot):
    bot.store.save(Event(channel_id=5, guild_id=1, thread_id=77, join_message_id=88))
    thread = make_thread()
    thread.parent.get_partial_message.return_value = MagicMock(edit=AsyncMock(side_effect=http_error()))
    run(update_participant_count(bot.store, thread, "en"))  # must not raise
