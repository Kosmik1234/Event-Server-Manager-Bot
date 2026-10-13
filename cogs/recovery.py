"""Rebuilds missing event records on startup.

If the events file is lost (e.g. it wasn't on a persistent volume), the bot no longer
knows which channels are events. Discord still has everything, so for every channel in a
configured event category that has no record we find its updates thread and its bot
messages, recreate the record and resync the participant counter. Fields that only existed
in the record (creator) can't be recovered; title/date/location/description are read back
from the announcement embed when there is one."""
import logging

import discord
from discord.ext import commands

from cogs.join import update_participant_count
from storage import Event


def _custom_ids(message: discord.Message):
    for row in message.components:
        for child in getattr(row, "children", []):
            custom_id = getattr(child, "custom_id", None)
            if custom_id:
                yield custom_id


class RecoveryCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._done = False  # on_ready fires again after reconnects; recover only once per run

    @commands.Cog.listener()
    async def on_ready(self):
        if self._done:
            return
        self._done = True
        for guild in self.bot.guilds:
            for category_id in self.bot.guild_settings.get_categories(guild.id):
                category = guild.get_channel(category_id)
                if not isinstance(category, discord.CategoryChannel):
                    continue
                for channel in category.text_channels:
                    if self.bot.store.get_by_channel(channel.id) is None:
                        try:
                            await self._restore(channel)
                        except discord.HTTPException:
                            logging.exception("Failed to restore event record for #%s", channel.name)

    async def _find_thread(self, channel: discord.TextChannel) -> discord.Thread | None:
        """The private updates thread the bot created in this channel."""
        for thread in channel.threads:
            if thread.owner_id == self.bot.user.id:
                return thread
        # Inactive threads are archived and not in the cache.
        async for thread in channel.archived_threads(private=True, limit=None):
            if thread.owner_id == self.bot.user.id:
                return thread
        return None

    async def _restore(self, channel: discord.TextChannel) -> None:
        thread = await self._find_thread(channel)
        if thread is None:
            return  # not an event channel (or its thread is gone)

        event = Event(channel_id=channel.id, guild_id=channel.guild.id, title=channel.name, thread_id=thread.id)
        join_marker = f"join-event:{thread.id}"
        async for message in channel.history(limit=100, oldest_first=True):
            if message.author.id != self.bot.user.id:
                continue
            if event.join_message_id is None and join_marker in _custom_ids(message):
                event.join_message_id = message.id
            elif event.message_id is None and message.embeds:
                embed = message.embeds[0]
                event.message_id = message.id
                event.title = embed.title or event.title
                event.description = embed.description or ""
                if len(embed.fields) >= 2:  # /create-event posts "when" then "where"
                    event.date, event.location = embed.fields[0].value, embed.fields[1].value

        self.bot.store.save(event)
        logging.info("Restored event record for #%s (thread %s)", channel.name, thread.id)
        await update_participant_count(self.bot.store, thread, self.bot.lang(channel.guild))


async def setup(bot: commands.Bot):
    await bot.add_cog(RecoveryCog(bot))
