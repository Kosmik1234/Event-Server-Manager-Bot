"""/event-template commands: choose the format of event announcements per server
(admins/mods only)."""
import discord
from discord import app_commands
from discord.ext import commands

from checks import is_admin_or_mod
from cogs.events import build_embed, refresh_announcement
from i18n import t
from storage import Event
from templates import TEMPLATE_LIMIT, default_template, sample_values, validate_template


class TemplateModal(discord.ui.Modal):
    """Multi-line editor. Slash command options are single-line, so a modal is the only way
    to type a template with line breaks."""

    def __init__(self, bot: commands.Bot, lang: str, current: str):
        super().__init__(title=t(lang, "template_modal_title"))
        self.bot = bot
        self.lang = lang
        self.template = discord.ui.TextInput(
            label=t(lang, "template_modal_label"), style=discord.TextStyle.paragraph,
            default=current, max_length=TEMPLATE_LIMIT, required=True,
            placeholder="{title} {date} {location} {description} {custom_field}",  # label is capped at 45 chars, placeholder at 100
        )
        self.add_item(self.template)

    async def on_submit(self, interaction: discord.Interaction):
        error = validate_template(self.template.value)
        if error:
            await interaction.response.send_message(t(self.lang, error), ephemeral=True)
            return
        self.bot.guild_settings.set_template(interaction.guild_id, self.template.value)
        await interaction.response.send_message(t(self.lang, "template_saved"), ephemeral=True)


class EventTemplateCog(
    commands.GroupCog,
    group_name="event-template",
    group_description="Choose how event announcements look on this server",
):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _current(self, guild: discord.Guild) -> str:
        return self.bot.guild_settings.get_template(guild.id) or default_template(self.bot.lang(guild))

    @app_commands.command(name="edit", description="Edit the announcement template (admins/mods only)")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @is_admin_or_mod()
    async def edit(self, interaction: discord.Interaction):
        lang = self.bot.lang(interaction.guild)
        await interaction.response.send_modal(TemplateModal(self.bot, lang, self._current(interaction.guild)))

    @app_commands.command(name="show", description="Show the current announcement template (admins/mods only)")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @is_admin_or_mod()
    async def show(self, interaction: discord.Interaction):
        lang = self.bot.lang(interaction.guild)
        custom = self.bot.guild_settings.get_template(interaction.guild_id) is not None
        text = self._current(interaction.guild).replace("```", "`​``")  # keep the code block intact
        embed = discord.Embed(description=f"```\n{text}\n```")
        await interaction.response.send_message(
            t(lang, "template_custom" if custom else "template_default"), embed=embed, ephemeral=True
        )

    @app_commands.command(name="preview", description="Preview the announcement with sample data (admins/mods only)")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @is_admin_or_mod()
    async def preview(self, interaction: discord.Interaction):
        lang = self.bot.lang(interaction.guild)
        template = self._current(interaction.guild)
        values = sample_values(template)
        sample = Event(
            channel_id=0, guild_id=interaction.guild_id, title=values["title"], date=values["date"],
            location=values["location"], description=values["description"], extra=values,
        )
        await interaction.response.send_message(
            t(lang, "template_preview"), embed=build_embed(sample, lang, template), ephemeral=True
        )

    @app_commands.command(name="reset", description="Go back to the default announcement format (admins/mods only)")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @is_admin_or_mod()
    async def reset(self, interaction: discord.Interaction):
        lang = self.bot.lang(interaction.guild)
        reset = self.bot.guild_settings.reset_template(interaction.guild_id)
        await interaction.response.send_message(t(lang, "template_reset" if reset else "template_already_default"), ephemeral=True)

    @app_commands.command(name="apply", description="Re-render existing announcements with the current template (admins/mods only)")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @is_admin_or_mod()
    async def apply(self, interaction: discord.Interaction):
        """Announcements are rendered once when posted; this updates the ones already out there."""
        lang = self.bot.lang(interaction.guild)
        await interaction.response.defer(ephemeral=True)
        events = [e for e in self.bot.store.all() if e.guild_id == interaction.guild_id and e.message_id is not None]
        for event in events:
            await refresh_announcement(self.bot, event, interaction.guild)
        await interaction.followup.send(t(lang, "template_applied", count=len(events)))

    @edit.error
    @show.error
    @preview.error
    @reset.error
    @apply.error
    async def on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(t(self.bot.lang(interaction.guild), "only_admins_change"), ephemeral=True)
        else:
            raise error


async def setup(bot: commands.Bot):
    await bot.add_cog(EventTemplateCog(bot))
