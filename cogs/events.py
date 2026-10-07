"""The /create-event command."""
import re

import discord
from discord import app_commands
from discord.ext import commands

from checks import is_admin_or_mod
from storage import Event


def find_category(guild: discord.Guild, allowed_category_ids: list[int]) -> discord.CategoryChannel | None:
    """Pick the first configured category (by ID) that still exists."""
    for cat in guild.categories:
        if cat.id in allowed_category_ids:
            return cat
    return None


def build_embed(event: Event) -> discord.Embed:
    embed = discord.Embed(title=event.title, description=event.description, color=discord.Color.blurple())
    embed.add_field(name="📅 When", value=event.date, inline=True)
    embed.add_field(name="📍 Where", value=event.location, inline=True)
    return embed


class EventsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="create-event", description="Create a new event channel (admins/mods only)")
    @app_commands.describe(title="Event name", date="When it happens", location="Where it happens", description="Details")
    @app_commands.guild_only()
    @is_admin_or_mod()
    async def create_event(
        self, interaction: discord.Interaction, title: str, date: str, location: str, description: str
    ):
        guild = interaction.guild
        # Creating channels can take a moment; defer so Discord doesn't time out (3s limit).
        await interaction.response.defer(ephemeral=True)

        allowed_category_ids = self.bot.guild_settings.get_categories(guild.id)
        if not allowed_category_ids:
            await interaction.followup.send("No event categories configured yet. Ask an admin to run `/event-category add`.")
            return

        category = find_category(guild, allowed_category_ids)
        if category is None:
            await interaction.followup.send("None of the configured event categories exist anymore. Fix with `/event-category`.")
            return

        # Channel name: lowercase, letters/digits/dashes only.
        name = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:90] or "event"

        # Members can see the channel but not type in it; only the bot (and admins/mods
        # via their own permissions) can post. Joining happens via the button, not chat.
        # The updates thread itself is created separately by the auto-thread listener,
        # the same way it is for every other channel in this category.
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                send_messages=False, create_public_threads=False, create_private_threads=False
            ),
            guild.me: discord.PermissionOverwrite(
                send_messages=True, manage_threads=True, create_private_threads=True, send_messages_in_threads=True
            ),
        }
        channel = await guild.create_text_channel(
            name, category=category, overwrites=overwrites, reason=f"Event created by {interaction.user}"
        )

        event = Event(
            channel_id=channel.id, guild_id=guild.id, title=title, date=date,
            location=location, description=description, creator_id=interaction.user.id,
        )
        message = await channel.send(embed=build_embed(event))  # Join button is added in the next step
        event.message_id = message.id
        self.bot.store.save(event)

        await interaction.followup.send(f"Event created: {channel.mention}")

    @create_event.error
    async def create_event_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("Only admins or moderators can create events.", ephemeral=True)
        else:
            raise error


async def setup(bot: commands.Bot):
    await bot.add_cog(EventsCog(bot))
