"""Moves event channels into their archive category once the event date has passed.

Each event category can have an archive (see /archive-category). Every hour, and once at
startup after the event records are restored, we compare each event's date with today's
date (in config.TIMEZONE) and move the channel of any past event. Events whose date can't
be read (see dates.py), and channels made by hand without details, are never moved."""
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands, tasks

import config
from dates import parse_event_date


class ArchiveSweepCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def cog_unload(self):
        self.sweep.cancel()

    @commands.Cog.listener()
    async def on_events_recovered(self):
        if not self.sweep.is_running():  # dispatched once per run, but be safe
            self.sweep.start()

    @tasks.loop(hours=1)
    async def sweep(self):
        today = datetime.now(ZoneInfo(config.TIMEZONE)).date()
        for event in self.bot.store.all():
            event_date = parse_event_date(event.date)
            if event_date is None or event_date >= today:
                continue
            guild = self.bot.get_guild(event.guild_id)
            channel = guild.get_channel(event.channel_id) if guild else None
            if channel is None or channel.category_id is None:
                continue
            archive_id = self.bot.guild_settings.get_archives(guild.id).get(channel.category_id)
            archive = guild.get_channel(archive_id) if archive_id else None
            if not isinstance(archive, discord.CategoryChannel):
                continue  # no archive for this category (or it was deleted)
            try:
                await channel.edit(category=archive, reason=f"Event date {event_date} has passed")
                logging.info("Archived #%s into %s", channel.name, archive.name)
            except discord.HTTPException:
                # Missing Manage Channels on the archive, or the category is full (50 channels).
                logging.exception("Failed to archive #%s into %s", channel.name, archive.name)

    @sweep.error
    async def on_sweep_error(self, error: Exception):
        logging.error("Archive sweep crashed", exc_info=error)


async def setup(bot: commands.Bot):
    await bot.add_cog(ArchiveSweepCog(bot))
