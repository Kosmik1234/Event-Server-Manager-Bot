"""The bot's core behavior: as soon as a text channel is created inside a
configured event category, start an updates thread in it automatically.
Works for channels created by /create-event, by mods manually, or by anyone else
with permission to create channels there — no command needed.

The thread is private: regular members can't see it. Only members explicitly
added to it, or anyone with the Manage Threads permission (admins, and any other
bot whose role is granted that permission), can see and post in it."""
import discord
from discord.ext import commands


class AutoThreadCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        if not isinstance(channel, discord.TextChannel) or channel.category_id is None:
            return
        if channel.category_id not in self.bot.guild_settings.get_categories(channel.guild.id):
            return

        thread = await channel.create_thread(
            name=f"{channel.name}-updates", type=discord.ChannelType.private_thread, invitable=False
        )

        # If this channel belongs to an event created via /create-event, link the thread to it.
        event = self.bot.store.get_by_channel(channel.id)
        if event is not None:
            event.thread_id = thread.id
            self.bot.store.save(event)


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoThreadCog(bot))
