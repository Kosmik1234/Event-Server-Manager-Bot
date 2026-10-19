"""The /create-event command."""
import logging
import re

import discord
from discord import app_commands
from discord.ext import commands

from checks import is_admin_or_mod
from cogs.auto_thread import setup_event_channel
from dates import parse_event_date
from i18n import t
from storage import Event


def find_category(guild: discord.Guild, allowed_category_ids: list[int]) -> discord.CategoryChannel | None:
    """Pick the first configured category (by ID) that still exists."""
    for cat in guild.categories:
        if cat.id in allowed_category_ids:
            return cat
    return None


def build_embed(event: Event, lang: str) -> discord.Embed:
    embed = discord.Embed(title=event.title, description=event.description, color=discord.Color.blurple())
    embed.add_field(name=t(lang, "field_when"), value=event.date, inline=True)
    embed.add_field(name=t(lang, "field_where"), value=event.location, inline=True)
    return embed


class EventsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="create-event", description="Create a new event channel (admins/mods only)")
    @app_commands.describe(title="Event name", date="When it happens", location="Where it happens", description="Details")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)  # hides it from the picker for regular members by default
    @is_admin_or_mod()  # the actual enforcement; Discord's default_permissions is just UI-level and admin-overridable
    async def create_event(
        self, interaction: discord.Interaction, title: str, date: str, location: str, description: str
    ):
        guild = interaction.guild
        lang = self.bot.lang(guild)
        # Creating channels can take a moment; defer so Discord doesn't time out (3s limit).
        await interaction.response.defer(ephemeral=True)

        allowed_category_ids = self.bot.guild_settings.get_categories(guild.id)
        if not allowed_category_ids:
            await interaction.followup.send(t(lang, "no_categories"))
            return

        category = find_category(guild, allowed_category_ids)
        if category is None:
            await interaction.followup.send(t(lang, "categories_missing"))
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
                send_messages=True, manage_threads=True, create_private_threads=True,
                send_messages_in_threads=True, manage_messages=True,  # manage_messages: needed to pin the participant counter
            ),
        }
        try:
            channel = await guild.create_text_channel(
                name, category=category, overwrites=overwrites, reason=f"Event created by {interaction.user}"
            )

            event = Event(
                channel_id=channel.id, guild_id=guild.id, title=title, date=date,
                location=location, description=description, creator_id=interaction.user.id,
            )
            # Save BEFORE posting the message: the auto-thread listener fires as soon as the
            # channel exists and looks this event up to link the thread to it.
            self.bot.store.save(event)
            message = await channel.send(embed=build_embed(event, lang))  # Join button is added in the next step
            # Re-read: the listener may have added thread_id / join_message_id in the meantime.
            event = self.bot.store.get_by_channel(channel.id) or event
            event.message_id = message.id
            self.bot.store.save(event)
        except discord.Forbidden:
            await interaction.followup.send(t(lang, "no_permission"))
            return
        except discord.HTTPException:
            logging.exception("Failed to create event channel")
            await interaction.followup.send(t(lang, "create_failed"))
            return

        reply = t(lang, "event_created", channel=channel.mention)
        if parse_event_date(date) is None:
            reply += "\n" + t(lang, "date_unreadable")
        await interaction.followup.send(reply)

    @app_commands.command(name="make-event", description="Turn this channel into an event (admins/mods only)")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @is_admin_or_mod()
    async def make_event(self, interaction: discord.Interaction):
        """Repair command for channels the bot never registered (created before it joined, or
        moved into an event category)."""
        lang = self.bot.lang(interaction.guild)
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel) or channel.category_id not in self.bot.guild_settings.get_categories(
            interaction.guild_id
        ):
            await interaction.response.send_message(t(lang, "not_in_event_category"), ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        existing = self.bot.store.get_by_channel(channel.id)
        if existing is not None and existing.thread_id is not None:
            try:
                await interaction.guild.fetch_channel(existing.thread_id)
            except discord.NotFound:
                pass  # the thread was deleted: rebuild it
            except discord.HTTPException:
                logging.exception("Failed to check thread %s", existing.thread_id)
                await interaction.followup.send(t(lang, "create_failed"))
                return
            else:
                await interaction.followup.send(t(lang, "already_event"))
                return

        result = await setup_event_channel(self.bot, channel)
        key = {"ok": "event_made", "forbidden": "no_permission"}.get(result, "create_failed")
        await interaction.followup.send(t(lang, key))

    @make_event.error
    async def make_event_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(t(self.bot.lang(interaction.guild), "only_admins_change"), ephemeral=True)
        else:
            raise error

    @app_commands.command(name="set-date", description="Set the date of this event (admins/mods only)")
    @app_commands.describe(date="When it happens, e.g. 15.11.2026")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @is_admin_or_mod()
    async def set_date(self, interaction: discord.Interaction, date: str):
        """Works in the event channel or in its updates thread."""
        lang = self.bot.lang(interaction.guild)
        store = self.bot.store
        event = store.get_by_channel(interaction.channel_id) or store.get_by_thread(interaction.channel_id)
        if event is None:
            await interaction.response.send_message(t(lang, "not_event_channel"), ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        event.date = date
        store.save(event)

        # Keep the announcement embed in sync (recovery reads the date back from it).
        # Channels made by hand have no embed.
        if event.message_id is not None:
            channel = interaction.guild.get_channel(event.channel_id)
            if channel is not None:
                try:
                    await channel.get_partial_message(event.message_id).edit(embed=build_embed(event, lang))
                except discord.HTTPException:
                    logging.exception("Failed to update the announcement embed in %s", event.channel_id)

        reply = t(lang, "date_set", date=date)
        if parse_event_date(date) is None:
            reply += "\n" + t(lang, "date_unreadable")
        await interaction.followup.send(reply)

    @app_commands.command(name="get-date", description="Show the date of this event")
    @app_commands.guild_only()
    async def get_date(self, interaction: discord.Interaction):
        """Works in the event channel or in its updates thread. Also shows how the date was
        parsed, since that is what the archive sweep uses."""
        lang = self.bot.lang(interaction.guild)
        store = self.bot.store
        event = store.get_by_channel(interaction.channel_id) or store.get_by_thread(interaction.channel_id)
        if event is None:
            await interaction.response.send_message(t(lang, "not_event_channel"), ephemeral=True)
            return

        if not event.date:
            reply = t(lang, "date_none")
        else:
            parsed = parse_event_date(event.date)
            if parsed is None:
                reply = t(lang, "date_get", date=event.date) + "\n" + t(lang, "date_unreadable")
            else:
                reply = t(lang, "date_get_parsed", date=event.date, parsed=parsed.strftime("%d.%m.%Y"))
        await interaction.response.send_message(reply, ephemeral=True)

    @create_event.error
    async def create_event_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(t(self.bot.lang(interaction.guild), "only_admins_create"), ephemeral=True)
        else:
            raise error

    @set_date.error
    async def set_date_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(t(self.bot.lang(interaction.guild), "only_admins_change"), ephemeral=True)
        else:
            raise error


async def setup(bot: commands.Bot):
    await bot.add_cog(EventsCog(bot))
