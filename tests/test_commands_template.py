"""/event-template and its edit modal."""
from unittest.mock import AsyncMock, MagicMock, patch

from cogs.event_template import EventTemplateCog, TemplateModal
from conftest import GUILD_ID, reply, run, was_ephemeral
from i18n import t
from storage import Event
from templates import default_template


def submit(bot, make_interaction, text):
    async def go():
        modal = TemplateModal(bot, "en", "current")
        modal.template._value = text  # what the user typed
        i = make_interaction()
        await modal.on_submit(i)
        return i

    return run(go())


def test_modal_saves_template(bot, make_interaction):
    i = submit(bot, make_interaction, "# {title}\n🎟 {tickets}")
    assert bot.guild_settings.get_template(GUILD_ID) == "# {title}\n🎟 {tickets}"
    assert reply(i) == t("en", "template_saved") and was_ephemeral(i)


def test_modal_rejects_blank_template(bot, make_interaction):
    i = submit(bot, make_interaction, "   \n ")
    assert bot.guild_settings.get_template(GUILD_ID) is None
    assert reply(i) == t("en", "template_empty")


def test_edit_opens_modal_prefilled_with_current_template(bot, make_interaction):
    cog = EventTemplateCog(bot)

    async def go(i):
        await cog.edit.callback(cog, i)

    i = make_interaction()
    run(go(i))
    modal = i.response.send_modal.await_args.args[0]
    assert modal.template.default == default_template("en")  # nothing custom saved yet

    bot.guild_settings.set_template(GUILD_ID, "mine {title}")
    i = make_interaction()
    run(go(i))
    assert i.response.send_modal.await_args.args[0].template.default == "mine {title}"


def test_show_marks_default_vs_custom(bot, make_interaction):
    cog = EventTemplateCog(bot)
    i = make_interaction()
    run(cog.show.callback(cog, i))
    assert reply(i) == t("en", "template_default")
    assert default_template("en") in i.response.send_message.await_args.kwargs["embed"].description

    bot.guild_settings.set_template(GUILD_ID, "mine ``` {title}")
    i = make_interaction()
    run(cog.show.callback(cog, i))
    assert reply(i) == t("en", "template_custom")
    description = i.response.send_message.await_args.kwargs["embed"].description
    assert description.count("```") == 2  # the user's backticks can't close our code block


def test_preview_renders_sample_data_including_custom_keys(bot, make_interaction):
    bot.guild_settings.set_template(GUILD_ID, "{title} | {tickets}")
    cog = EventTemplateCog(bot)
    i = make_interaction()
    run(cog.preview.callback(cog, i))
    assert i.response.send_message.await_args.kwargs["embed"].description == "Sample event | <tickets>"
    assert was_ephemeral(i)


def test_reset(bot, make_interaction):
    cog = EventTemplateCog(bot)
    i = make_interaction()
    run(cog.reset.callback(cog, i))
    assert reply(i) == t("en", "template_already_default")

    bot.guild_settings.set_template(GUILD_ID, "x {title}")
    i = make_interaction()
    run(cog.reset.callback(cog, i))
    assert reply(i) == t("en", "template_reset")
    assert bot.guild_settings.get_template(GUILD_ID) is None


def test_apply_refreshes_only_this_guilds_events_that_have_an_announcement(bot, make_interaction):
    bot.store.save(Event(channel_id=1, guild_id=GUILD_ID, message_id=11))
    bot.store.save(Event(channel_id=2, guild_id=GUILD_ID))  # made by hand: no announcement
    bot.store.save(Event(channel_id=3, guild_id=999, message_id=33))  # other server
    cog = EventTemplateCog(bot)
    i = make_interaction()
    with patch("cogs.event_template.refresh_announcement", new=AsyncMock()) as refresh:
        run(cog.apply.callback(cog, i))
    assert [call.args[1].channel_id for call in refresh.await_args_list] == [1]
    assert reply(i) == t("en", "template_applied", count=1)
