"""/event-category, /archive-category, /language."""
from unittest.mock import MagicMock

import discord

from cogs.settings import ArchiveCog, LanguageCog, SettingsCog
from conftest import GUILD_ID, make_category, reply, run, was_ephemeral
from i18n import t


# --- /event-category -------------------------------------------------------

def test_event_category_add_remove_list(bot, make_interaction):
    cog, cat = SettingsCog(bot), make_category(10)

    i = make_interaction()
    run(cog.add.callback(cog, i, cat))
    assert reply(i) == t("en", "category_added", category=cat.mention)
    assert bot.guild_settings.get_categories(GUILD_ID) == [10]

    i = make_interaction()
    run(cog.add.callback(cog, i, cat))
    assert reply(i) == t("en", "category_exists", category=cat.mention)

    i = make_interaction()
    i.guild.get_channel.return_value = cat
    run(cog.list_categories.callback(cog, i))
    assert cat.mention in reply(i) and was_ephemeral(i)

    i = make_interaction()
    run(cog.remove.callback(cog, i, cat))
    assert reply(i) == t("en", "category_removed", category=cat.mention)

    i = make_interaction()
    run(cog.remove.callback(cog, i, cat))
    assert reply(i) == t("en", "category_not_in_list", category=cat.mention)


def test_event_category_list_empty_and_deleted_category(bot, make_interaction):
    cog = SettingsCog(bot)
    i = make_interaction()
    run(cog.list_categories.callback(cog, i))
    assert reply(i) == t("en", "category_none")

    bot.guild_settings.add_category(GUILD_ID, 10)
    i = make_interaction()  # get_channel returns None: the category was deleted
    run(cog.list_categories.callback(cog, i))
    assert t("en", "category_gone", id=10) in reply(i)


def test_archive_cannot_become_event_category(bot, make_interaction):
    bot.guild_settings.add_category(GUILD_ID, 10)
    bot.guild_settings.set_archive(GUILD_ID, 10, 99)
    cog, archive = SettingsCog(bot), make_category(99)
    i = make_interaction()
    run(cog.add.callback(cog, i, archive))
    assert reply(i) == t("en", "category_is_archive", category=archive.mention)
    assert bot.guild_settings.get_categories(GUILD_ID) == [10]


# --- /archive-category -----------------------------------------------------

def test_archive_add_validations(bot, make_interaction):
    cog = ArchiveCog(bot)
    events, archive = make_category(10), make_category(99)

    i = make_interaction()  # source isn't an event category yet
    run(cog.add.callback(cog, i, events, archive))
    assert reply(i) == t("en", "archive_source_not_event", category=events.mention)

    bot.guild_settings.add_category(GUILD_ID, 10)
    bot.guild_settings.add_category(GUILD_ID, 11)
    i = make_interaction()  # the target is itself an event category
    run(cog.add.callback(cog, i, events, make_category(11)))
    assert reply(i) == t("en", "archive_target_is_event", category=make_category(11).mention)

    i = make_interaction()
    run(cog.add.callback(cog, i, events, archive))
    assert reply(i) == t("en", "archive_added", source=events.mention, archive=archive.mention)
    assert bot.guild_settings.get_archives(GUILD_ID) == {10: 99}


def test_archive_add_refuses_second_archive_for_same_category(bot, make_interaction):
    bot.guild_settings.add_category(GUILD_ID, 10)
    bot.guild_settings.set_archive(GUILD_ID, 10, 99)
    cog = ArchiveCog(bot)
    i = make_interaction()
    i.guild.get_channel.return_value = make_category(99)
    run(cog.add.callback(cog, i, make_category(10), make_category(98)))
    assert "already has an archive" in reply(i)
    assert bot.guild_settings.get_archives(GUILD_ID) == {10: 99}


def test_archive_remove_and_list(bot, make_interaction):
    bot.guild_settings.add_category(GUILD_ID, 10)
    bot.guild_settings.set_archive(GUILD_ID, 10, 99)
    cog = ArchiveCog(bot)

    i = make_interaction()
    i.guild.get_channel.side_effect = lambda cid: make_category(cid)
    run(cog.list_archives.callback(cog, i))
    assert "<#10> → <#99>" in reply(i)

    i = make_interaction()
    run(cog.remove.callback(cog, i, make_category(10)))
    assert reply(i) == t("en", "archive_removed", source="<#10>")
    i = make_interaction()
    run(cog.remove.callback(cog, i, make_category(10)))
    assert reply(i) == t("en", "archive_not_set", source="<#10>")
    i = make_interaction()
    run(cog.list_archives.callback(cog, i))
    assert reply(i) == t("en", "archive_none")


# --- /language -------------------------------------------------------------

def test_language_is_saved_and_confirmed_in_the_new_language(bot, make_interaction):
    from discord import app_commands
    cog = LanguageCog(bot)
    i = make_interaction()
    run(cog.language.callback(cog, i, app_commands.Choice(name="Polski", value="pl")))
    assert bot.guild_settings.get_language(GUILD_ID) == "pl"
    assert reply(i) == t("pl", "language_set", language="Polski")
