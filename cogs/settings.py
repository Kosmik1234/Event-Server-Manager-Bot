"""/event-category commands: configure per-server which categories event
channels may be created in (admins/mods only)."""
import discord
from discord import app_commands
from discord.ext import commands

from checks import is_admin_or_mod
from i18n import LANGUAGES, t


class SettingsCog(
    commands.GroupCog,
    group_name="event-category",
    group_description="Manage which categories event channels can be created in",
):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="add", description="Allow event channels to be created in this category (admins/mods only)")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)  # hides it from the picker for regular members by default
    @is_admin_or_mod()  # the actual enforcement; Discord's default_permissions is just UI-level and admin-overridable
    async def add(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        lang = self.bot.lang(interaction.guild)
        if category.id in self.bot.guild_settings.get_archives(interaction.guild_id).values():
            await interaction.response.send_message(t(lang, "category_is_archive", category=category.mention), ephemeral=True)
            return
        added = self.bot.guild_settings.add_category(interaction.guild_id, category.id)
        if added:
            await interaction.response.send_message(t(lang, "category_added", category=category.mention), ephemeral=True)
        else:
            await interaction.response.send_message(t(lang, "category_exists", category=category.mention), ephemeral=True)

    @app_commands.command(name="remove", description="Stop allowing event channels in this category (admins/mods only)")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)  # hides it from the picker for regular members by default
    @is_admin_or_mod()  # the actual enforcement; Discord's default_permissions is just UI-level and admin-overridable
    async def remove(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        lang = self.bot.lang(interaction.guild)
        removed = self.bot.guild_settings.remove_category(interaction.guild_id, category.id)
        if removed:
            await interaction.response.send_message(t(lang, "category_removed", category=category.mention), ephemeral=True)
        else:
            await interaction.response.send_message(t(lang, "category_not_in_list", category=category.mention), ephemeral=True)

    @app_commands.command(name="list", description="List categories where event channels can be created")
    @app_commands.guild_only()
    async def list_categories(self, interaction: discord.Interaction):
        lang = self.bot.lang(interaction.guild)
        ids = self.bot.guild_settings.get_categories(interaction.guild_id)
        if not ids:
            await interaction.response.send_message(t(lang, "category_none"), ephemeral=True)
            return
        lines = []
        for cat_id in ids:
            cat = interaction.guild.get_channel(cat_id)
            lines.append(cat.mention if cat else t(lang, "category_gone", id=cat_id))
        await interaction.response.send_message(t(lang, "category_list_header") + "\n" + "\n".join(lines), ephemeral=True)

    @add.error
    @remove.error
    @list_categories.error
    async def on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(t(self.bot.lang(interaction.guild), "only_admins_change"), ephemeral=True)
        else:
            raise error


class ArchiveCog(
    commands.GroupCog,
    group_name="archive-category",
    group_description="Choose where event channels are moved after the event date passes",
):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="add", description="Move past events from an event category into an archive category (admins/mods only)")
    @app_commands.describe(event_category="A category added with /event-category", archive_category="Any other category")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @is_admin_or_mod()
    async def add(
        self, interaction: discord.Interaction,
        event_category: discord.CategoryChannel, archive_category: discord.CategoryChannel,
    ):
        lang = self.bot.lang(interaction.guild)
        settings = self.bot.guild_settings
        guild_id = interaction.guild_id
        event_ids = settings.get_categories(guild_id)
        if event_category.id not in event_ids:
            message = t(lang, "archive_source_not_event", category=event_category.mention)
        elif archive_category.id in event_ids:
            message = t(lang, "archive_target_is_event", category=archive_category.mention)
        elif not settings.set_archive(guild_id, event_category.id, archive_category.id):
            current = interaction.guild.get_channel(settings.get_archives(guild_id)[event_category.id])
            message = t(
                lang, "archive_already", source=event_category.mention,
                archive=current.mention if current else "?",
            )
        else:
            message = t(lang, "archive_added", source=event_category.mention, archive=archive_category.mention)
        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="remove", description="Stop archiving past events from an event category (admins/mods only)")
    @app_commands.describe(event_category="The event category whose archive link to remove")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @is_admin_or_mod()
    async def remove(self, interaction: discord.Interaction, event_category: discord.CategoryChannel):
        lang = self.bot.lang(interaction.guild)
        removed = self.bot.guild_settings.remove_archive(interaction.guild_id, event_category.id)
        key = "archive_removed" if removed else "archive_not_set"
        await interaction.response.send_message(t(lang, key, source=event_category.mention), ephemeral=True)

    @app_commands.command(name="list", description="List event categories and the archives they feed")
    @app_commands.guild_only()
    async def list_archives(self, interaction: discord.Interaction):
        lang = self.bot.lang(interaction.guild)
        archives = self.bot.guild_settings.get_archives(interaction.guild_id)
        if not archives:
            await interaction.response.send_message(t(lang, "archive_none"), ephemeral=True)
            return

        def name(category_id: int) -> str:
            channel = interaction.guild.get_channel(category_id)
            return channel.mention if channel else t(lang, "category_gone", id=category_id)

        lines = [f"{name(source)} → {name(target)}" for source, target in archives.items()]
        await interaction.response.send_message(t(lang, "archive_list_header") + "\n" + "\n".join(lines), ephemeral=True)

    @add.error
    @remove.error
    @list_archives.error
    async def on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(t(self.bot.lang(interaction.guild), "only_admins_change"), ephemeral=True)
        else:
            raise error


class LanguageCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="language", description="Set the bot's language for this server (admins/mods only)")
    @app_commands.describe(language="Language used in the bot's messages")
    @app_commands.choices(language=[app_commands.Choice(name=name, value=code) for code, name in LANGUAGES.items()])
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @is_admin_or_mod()
    async def language(self, interaction: discord.Interaction, language: app_commands.Choice[str]):
        self.bot.guild_settings.set_language(interaction.guild_id, language.value)
        await interaction.response.send_message(
            t(language.value, "language_set", language=language.name), ephemeral=True
        )

    @language.error
    async def on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(t(self.bot.lang(interaction.guild), "only_admins_change"), ephemeral=True)
        else:
            raise error


async def setup(bot: commands.Bot):
    await bot.add_cog(SettingsCog(bot))
    await bot.add_cog(ArchiveCog(bot))
    await bot.add_cog(LanguageCog(bot))
