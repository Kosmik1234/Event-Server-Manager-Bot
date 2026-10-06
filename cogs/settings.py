"""/event-category commands: configure per-server which categories event
channels may be created in (admins/mods only)."""
import discord
from discord import app_commands
from discord.ext import commands

from checks import is_admin_or_mod


class SettingsCog(
    commands.GroupCog,
    group_name="event-category",
    group_description="Manage which categories event channels can be created in",
):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="add", description="Allow event channels to be created in this category")
    @app_commands.guild_only()
    @is_admin_or_mod()
    async def add(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        added = self.bot.guild_settings.add_category(interaction.guild_id, category.id)
        if added:
            await interaction.response.send_message(f"Added {category.mention} to allowed event categories.", ephemeral=True)
        else:
            await interaction.response.send_message(f"{category.mention} is already allowed.", ephemeral=True)

    @app_commands.command(name="remove", description="Stop allowing event channels in this category")
    @app_commands.guild_only()
    @is_admin_or_mod()
    async def remove(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        removed = self.bot.guild_settings.remove_category(interaction.guild_id, category.id)
        if removed:
            await interaction.response.send_message(f"Removed {category.mention} from allowed event categories.", ephemeral=True)
        else:
            await interaction.response.send_message(f"{category.mention} wasn't in the list.", ephemeral=True)

    @app_commands.command(name="list", description="List categories where event channels can be created")
    @app_commands.guild_only()
    @is_admin_or_mod()
    async def list_categories(self, interaction: discord.Interaction):
        ids = self.bot.guild_settings.get_categories(interaction.guild_id)
        if not ids:
            await interaction.response.send_message(
                "No event categories configured yet. Add one with `/event-category add`.",
                ephemeral=True,
            )
            return
        lines = []
        for cat_id in ids:
            cat = interaction.guild.get_channel(cat_id)
            lines.append(cat.mention if cat else f"`{cat_id}` (category no longer exists)")
        await interaction.response.send_message("Allowed event categories:\n" + "\n".join(lines), ephemeral=True)

    @add.error
    @remove.error
    @list_categories.error
    async def on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("Only admins or moderators can change this.", ephemeral=True)
        else:
            raise error


async def setup(bot: commands.Bot):
    await bot.add_cog(SettingsCog(bot))
