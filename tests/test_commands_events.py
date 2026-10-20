"""/create-event, /make-event, /set-date, /get-date, /set-field."""
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from cogs.events import EventsCog
from conftest import GUILD_ID, http_error, make_category, make_text_channel, not_found, reply, run, was_ephemeral
from i18n import t
from storage import Event


def saved_event(bot, **kw) -> Event:
    event = Event(channel_id=5, guild_id=GUILD_ID, title="Fest", date="15.11.2026", location="Warsaw", description="Fun", **kw)
    bot.store.save(event)
    return event


# --- /get-date -------------------------------------------------------------

def test_get_date_shows_date_and_how_it_was_read(bot, make_interaction):
    saved_event(bot)
    i = make_interaction()
    run(EventsCog(bot).get_date.callback(EventsCog(bot), i))
    assert reply(i) == "Event date: 15.11.2026 (read as 15.11.2026)"
    assert was_ephemeral(i)


def test_get_date_works_in_the_thread(bot, make_interaction):
    saved_event(bot, thread_id=77)
    i = make_interaction(channel_id=77)
    run(EventsCog(bot).get_date.callback(EventsCog(bot), i))
    assert "15.11.2026" in reply(i)


def test_get_date_warns_about_unreadable_date(bot, make_interaction):
    event = saved_event(bot)
    event.date = "soon"
    bot.store.save(event)
    i = make_interaction()
    run(EventsCog(bot).get_date.callback(EventsCog(bot), i))
    assert "soon" in reply(i) and t("en", "date_unreadable") in reply(i)


def test_get_date_without_date(bot, make_interaction):
    event = saved_event(bot)
    event.date = ""
    bot.store.save(event)
    i = make_interaction()
    run(EventsCog(bot).get_date.callback(EventsCog(bot), i))
    assert reply(i) == t("en", "date_none")


def test_get_date_outside_event(bot, make_interaction):
    i = make_interaction(channel_id=999)
    run(EventsCog(bot).get_date.callback(EventsCog(bot), i))
    assert reply(i) == t("en", "not_event_channel")


# --- /set-date -------------------------------------------------------------

def test_set_date_saves_and_refreshes_announcement(bot, make_interaction):
    saved_event(bot, message_id=7)
    i = make_interaction()
    with patch("cogs.events.refresh_announcement", new=AsyncMock()) as refresh:
        run(EventsCog(bot).set_date.callback(EventsCog(bot), i, "20.12.2026"))
    assert bot.store.get_by_channel(5).date == "20.12.2026"
    refresh.assert_awaited_once()
    assert reply(i) == "Event date set to: 20.12.2026"


def test_set_date_warns_when_unreadable(bot, make_interaction):
    saved_event(bot)
    i = make_interaction()
    with patch("cogs.events.refresh_announcement", new=AsyncMock()):
        run(EventsCog(bot).set_date.callback(EventsCog(bot), i, "next week"))
    assert t("en", "date_unreadable") in reply(i)
    assert bot.store.get_by_channel(5).date == "next week"  # still saved


def test_set_date_works_from_the_thread(bot, make_interaction):
    saved_event(bot, thread_id=77)
    i = make_interaction(channel_id=77)
    with patch("cogs.events.refresh_announcement", new=AsyncMock()):
        run(EventsCog(bot).set_date.callback(EventsCog(bot), i, "20.12.2026"))
    assert bot.store.get_by_channel(5).date == "20.12.2026"


def test_set_date_outside_event(bot, make_interaction):
    i = make_interaction(channel_id=999)
    run(EventsCog(bot).set_date.callback(EventsCog(bot), i, "20.12.2026"))
    assert reply(i) == t("en", "not_event_channel")


# --- /set-field ------------------------------------------------------------

def test_set_field_sets_and_clears(bot, make_interaction):
    saved_event(bot)
    cog = EventsCog(bot)
    with patch("cogs.events.refresh_announcement", new=AsyncMock()) as refresh:
        i = make_interaction()
        run(cog.set_field.callback(cog, i, "Tickets", "http://x"))  # key is normalized
        assert bot.store.get_by_channel(5).extra == {"tickets": "http://x"}
        assert reply(i) == "Field `tickets` set to: http://x"

        i = make_interaction()
        run(cog.set_field.callback(cog, i, "tickets", None))
        assert bot.store.get_by_channel(5).extra == {}
        assert reply(i) == "Field `tickets` cleared."
    assert refresh.await_count == 2


def test_set_field_rejects_reserved_and_invalid_keys(bot, make_interaction):
    saved_event(bot)
    cog = EventsCog(bot)
    for key in ("title", "date", "location", "description", "bad key", "1abc", "a-b", ""):
        i = make_interaction()
        run(cog.set_field.callback(cog, i, key, "x"))
        assert "isn't a valid custom field name" in reply(i), key
    assert bot.store.get_by_channel(5).extra == {}


def test_set_field_outside_event(bot, make_interaction):
    i = make_interaction(channel_id=999)
    run(EventsCog(bot).set_field.callback(EventsCog(bot), i, "tickets", "x"))
    assert reply(i) == t("en", "not_event_channel")


# --- /make-event -----------------------------------------------------------

def make_event_in(bot, make_interaction, *, category_id=10, **kw):
    channel = make_text_channel(category_id=category_id)
    i = make_interaction(channel=channel)
    return channel, i


def test_make_event_outside_event_category(bot, make_interaction):
    bot.guild_settings.add_category(GUILD_ID, 10)
    channel, i = make_event_in(bot, make_interaction, category_id=11)
    run(EventsCog(bot).make_event.callback(EventsCog(bot), i))
    assert reply(i) == t("en", "not_in_event_category")


def test_make_event_creates_event(bot, make_interaction):
    bot.guild_settings.add_category(GUILD_ID, 10)
    channel, i = make_event_in(bot, make_interaction)
    with patch("cogs.events.setup_event_channel", new=AsyncMock(return_value="ok")) as setup:
        run(EventsCog(bot).make_event.callback(EventsCog(bot), i))
    setup.assert_awaited_once_with(bot, channel)
    assert reply(i) == t("en", "event_made")


def test_make_event_already_an_event(bot, make_interaction):
    bot.guild_settings.add_category(GUILD_ID, 10)
    saved_event(bot, thread_id=77)
    channel, i = make_event_in(bot, make_interaction)
    i.guild.fetch_channel = AsyncMock(return_value=MagicMock())  # the thread still exists
    with patch("cogs.events.setup_event_channel", new=AsyncMock()) as setup:
        run(EventsCog(bot).make_event.callback(EventsCog(bot), i))
    setup.assert_not_awaited()
    assert reply(i) == t("en", "already_event")


def test_make_event_rebuilds_deleted_thread(bot, make_interaction):
    bot.guild_settings.add_category(GUILD_ID, 10)
    saved_event(bot, thread_id=77)
    channel, i = make_event_in(bot, make_interaction)
    i.guild.fetch_channel = AsyncMock(side_effect=not_found())
    with patch("cogs.events.setup_event_channel", new=AsyncMock(return_value="ok")) as setup:
        run(EventsCog(bot).make_event.callback(EventsCog(bot), i))
    setup.assert_awaited_once()
    assert reply(i) == t("en", "event_made")


def test_make_event_maps_setup_results_to_messages(bot, make_interaction):
    bot.guild_settings.add_category(GUILD_ID, 10)
    for result, key in (("forbidden", "no_permission"), ("failed", "create_failed")):
        channel, i = make_event_in(bot, make_interaction)
        with patch("cogs.events.setup_event_channel", new=AsyncMock(return_value=result)):
            run(EventsCog(bot).make_event.callback(EventsCog(bot), i))
        assert reply(i) == t("en", key)


# --- /create-event ---------------------------------------------------------

def guild_creating(channel, category=None):
    guild = MagicMock(spec=discord.Guild)
    guild.id = GUILD_ID
    guild.categories = [category] if category else []
    guild.default_role = MagicMock()
    guild.me = MagicMock()
    guild.create_text_channel = AsyncMock(return_value=channel)
    return guild


def test_create_event_without_configured_categories(bot, make_interaction):
    i = make_interaction()
    run(EventsCog(bot).create_event.callback(EventsCog(bot), i, "Fest", "15.11.2026", "Warsaw", "Fun"))
    assert reply(i) == t("en", "no_categories")


def test_create_event_when_configured_categories_are_gone(bot, make_interaction):
    bot.guild_settings.add_category(GUILD_ID, 10)
    i = make_interaction()
    i.guild = guild_creating(make_text_channel(), category=None)
    run(EventsCog(bot).create_event.callback(EventsCog(bot), i, "Fest", "15.11.2026", "Warsaw", "Fun"))
    assert reply(i) == t("en", "categories_missing")


def test_create_event_saves_record_before_posting_embed(bot, make_interaction):
    """The channel-create listener runs as soon as the channel exists and looks the record up."""
    bot.guild_settings.add_category(GUILD_ID, 10)
    channel = make_text_channel()
    seen = {}

    async def send(**kwargs):
        seen["record_existed"] = bot.store.get_by_channel(channel.id) is not None
        seen["embed"] = kwargs["embed"]
        return MagicMock(id=700)

    channel.send = AsyncMock(side_effect=send)
    i = make_interaction()
    i.guild = guild_creating(channel, make_category(10))
    run(EventsCog(bot).create_event.callback(EventsCog(bot), i, "Fest", "15.11.2026", "Warsaw", "Fun"))

    assert seen["record_existed"] is True
    assert "Fest" in seen["embed"].description
    event = bot.store.get_by_channel(channel.id)
    assert (event.title, event.date, event.location, event.description) == ("Fest", "15.11.2026", "Warsaw", "Fun")
    assert event.message_id == 700 and event.creator_id == 42
    assert reply(i) == t("en", "event_created", channel=channel.mention)


def test_create_event_keeps_thread_added_by_listener(bot, make_interaction):
    bot.guild_settings.add_category(GUILD_ID, 10)
    channel = make_text_channel()

    async def send(**kwargs):  # the listener fills these in while the embed is being posted
        event = bot.store.get_by_channel(channel.id)
        event.thread_id, event.join_message_id = 77, 88
        bot.store.save(event)
        return MagicMock(id=700)

    channel.send = AsyncMock(side_effect=send)
    i = make_interaction()
    i.guild = guild_creating(channel, make_category(10))
    run(EventsCog(bot).create_event.callback(EventsCog(bot), i, "Fest", "15.11.2026", "Warsaw", "Fun"))
    event = bot.store.get_by_channel(channel.id)
    assert (event.thread_id, event.join_message_id, event.message_id) == (77, 88, 700)


def test_create_event_channel_name_is_sanitized(bot, make_interaction):
    bot.guild_settings.add_category(GUILD_ID, 10)
    for title, name in (("Wędrówka", "w-dr-wka"), ("Big  Party!!", "big-party"), ("!!!", "event"), ("x" * 200, "x" * 90)):
        channel = make_text_channel()
        channel.send = AsyncMock(return_value=MagicMock(id=1))
        i = make_interaction()
        i.guild = guild_creating(channel, make_category(10))
        run(EventsCog(bot).create_event.callback(EventsCog(bot), i, title, "15.11.2026", "W", "D"))
        assert i.guild.create_text_channel.await_args.args[0] == name


def test_create_event_warns_about_unreadable_date(bot, make_interaction):
    bot.guild_settings.add_category(GUILD_ID, 10)
    channel = make_text_channel()
    channel.send = AsyncMock(return_value=MagicMock(id=1))
    i = make_interaction()
    i.guild = guild_creating(channel, make_category(10))
    run(EventsCog(bot).create_event.callback(EventsCog(bot), i, "Fest", "someday", "W", "D"))
    assert t("en", "date_unreadable") in reply(i)


def test_create_event_reports_missing_permissions_and_api_errors(bot, make_interaction):
    bot.guild_settings.add_category(GUILD_ID, 10)
    for error, key in ((discord.Forbidden(MagicMock(status=403, reason="no"), "no"), "no_permission"), (http_error(), "create_failed")):
        i = make_interaction()
        i.guild = guild_creating(make_text_channel(), make_category(10))
        i.guild.create_text_channel = AsyncMock(side_effect=error)
        run(EventsCog(bot).create_event.callback(EventsCog(bot), i, "Fest", "15.11.2026", "W", "D"))
        assert reply(i) == t("en", key)
