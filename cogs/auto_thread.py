"""The bot's core behavior: as soon as a text channel is created inside a
configured event category, start an updates thread in it automatically.
Works for channels created by /create-event, by mods manually, or by anyone else
with permission to create channels there — no command needed.

The thread is private: regular members can't see it. Only members explicitly
added to it, or anyone with the Manage Threads permission (admins, and any other
bot whose role is granted that permission), can see and post in it."""
import logging

import discord
from discord.ext import commands

from cogs.join import counter_text, join_view, update_participant_count
from i18n import t
from storage import Event


async def setup_event_channel(bot: commands.Bot, channel: discord.TextChannel) -> str:
    """Turns a channel into an event: updates thread, stored record, pinned Join/Leave message.
    Shared by the channel-create listener and /make-event. Nobody is added to the thread:
    membership happens only through the Join/Leave buttons. Returns "ok", "forbidden" or "failed"."""
    lang = bot.lang(channel.guild)
    logging.info("Creating update thread in #%s (%s)", channel.name, channel.id)
    try:
        thread = await channel.create_thread(
            name=f"{channel.name}-{t(lang, 'thread_suffix')}", type=discord.ChannelType.private_thread, invitable=False,
            slowmode_delay=300,  # 5 minutes between messages per user
        )
    except discord.Forbidden:
        logging.error(
            "Missing permissions to create a thread in #%s (%s). The bot's role needs "
            "Create Private Threads and Manage Threads here.", channel.name, channel.id,
        )
        return "forbidden"
    except discord.HTTPException:
        logging.exception("Failed to create update thread in #%s", channel.name)
        return "failed"

    logging.info("Created thread #%s (%s) in #%s", thread.name, thread.id, channel.name)

    # Every channel with a thread gets a stored record. /create-event already saved one
    # (with details); for channels made by hand we create a bare one.
    event = bot.store.get_by_channel(channel.id) or Event(
        channel_id=channel.id, guild_id=channel.guild.id, title=channel.name
    )
    event.thread_id = thread.id

    # Pinned message in the channel: the Join/Leave buttons plus the participant count,
    # which on_thread_member_join/remove keep up to date.
    try:
        join_message = await channel.send(counter_text(0, lang), view=join_view(thread.id, lang))
        event.join_message_id = join_message.id
        await join_message.pin()
    except discord.HTTPException:
        logging.exception("Failed to post or pin the join message in #%s", channel.name)

    bot.store.save(event)
    logging.info("Stored event for #%s (thread %s)", channel.name, thread.id)

    return "ok"


class AutoThreadCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        logging.info("on_guild_channel_create fired for #%s (%s), type=%s", channel.name, channel.id, channel.type)

        if not isinstance(channel, discord.TextChannel) or channel.category_id is None:
            logging.info("Skipping #%s: not a text channel, or not inside any category", channel.name)
            return
        if channel.category_id not in self.bot.guild_settings.get_categories(channel.guild.id):
            logging.info("Skipping #%s: category %s is not in the configured list", channel.name, channel.category_id)
            return
        await setup_event_channel(self.bot, channel)

    async def _handle_membership_change(self, thread_id: int):
        """Common path for on_thread_member_join/remove: recompute the participant counter.
        These events fire for ANY membership change — our buttons, a manual "Leave Thread" in
        Discord's UI, a mod manually adding someone — so this is the single source of truth,
        not the buttons themselves."""
        thread = self.bot.get_channel(thread_id)
        if thread is None:
            return
        await update_participant_count(self.bot.store, thread, self.bot.lang(thread.guild))  # ignores threads we don't track

    @commands.Cog.listener()
    async def on_thread_member_join(self, member: discord.ThreadMember):
        await self._handle_membership_change(member.thread_id)

    @commands.Cog.listener()
    async def on_raw_thread_member_remove(self, payload: discord.RawThreadMembersUpdate):
        # Raw variant: the non-raw on_thread_member_remove only fires if the member was cached.
        await self._handle_membership_change(payload.thread_id)


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoThreadCog(bot))
