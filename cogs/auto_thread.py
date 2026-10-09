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

from cogs.join import join_view, update_participant_count


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

        logging.info("Creating update thread in #%s (%s)", channel.name, channel.id)
        try:
            thread = await channel.create_thread(
                name=f"{channel.name}-updates", type=discord.ChannelType.private_thread, invitable=False
            )
        except discord.Forbidden:
            logging.error(
                "Missing permissions to create a thread in #%s (%s). The bot's role needs "
                "Create Private Threads and Manage Threads here.", channel.name, channel.id,
            )
            return
        except discord.HTTPException:
            logging.exception("Failed to create update thread in #%s", channel.name)
            return

        logging.info("Created thread #%s (%s) in #%s", thread.name, thread.id, channel.name)

        # Pinned "Participants: N" message in the thread, kept up to date by the join/leave buttons.
        try:
            count_message = await thread.send("Participants: 0")
            await count_message.pin()
        except discord.HTTPException:
            logging.exception("Failed to post the participant counter in thread %s", thread.id)

        # Post the green Join Event button in the channel; clicking it adds the member to the thread.
        try:
            await channel.send("Click the button to join this event and get its updates.", view=join_view(thread.id))
        except discord.HTTPException:
            logging.exception("Failed to post the join button in #%s", channel.name)

        # If this channel belongs to an event created via /create-event, link the thread to it.
        event = self.bot.store.get_by_channel(channel.id)
        if event is not None:
            event.thread_id = thread.id
            self.bot.store.save(event)
            logging.info("Linked thread %s to the event in #%s", thread.id, channel.name)
            # A private thread is invisible to everyone not in it, so add the creator;
            # otherwise a mod without Manage Threads would never see it.
            creator = channel.guild.get_member(event.creator_id)
            if creator is not None:
                try:
                    await thread.add_user(creator)
                    await update_participant_count(thread)
                except discord.HTTPException:
                    logging.exception("Could not add creator %s to thread %s", event.creator_id, thread.id)


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoThreadCog(bot))
