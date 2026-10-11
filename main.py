"""Entry point: `python main.py`."""
import logging

import discord
from discord.ext import commands

import config
from guild_settings import GuildSettingsStore
from storage import JsonEventStore


class EventBot(commands.Bot):
    def __init__(self):
        # Intents say which Discord events we want. Default intents are enough:
        # slash commands and buttons don't need privileged intents.
        super().__init__(command_prefix=commands.when_mentioned, intents=discord.Intents.default())
        self.store = JsonEventStore(config.EVENTS_FILE)  # swap for another EventStore later
        self.guild_settings = GuildSettingsStore(config.GUILD_SETTINGS_FILE)

    async def setup_hook(self):
        # Runs once before connecting: load our command modules ("cogs") and sync slash commands.
        await self.load_extension("cogs.events")
        await self.load_extension("cogs.settings")
        await self.load_extension("cogs.join")
        await self.load_extension("cogs.auto_thread")
        if config.DEV_GUILD_ID:
            guild = discord.Object(id=config.DEV_GUILD_ID)
            self.tree.copy_global_to(guild=guild)  # instant updates in your test server
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()  # global; can take up to an hour to appear

    async def on_ready(self):
        logging.info("Logged in as %s", self.user)


def main():
    if not config.TOKEN:
        raise SystemExit("DISCORD_BOT_TOKEN is not set. Put it in .env (local) or Railway Variables.")
    logging.basicConfig(level=logging.INFO)
    EventBot().run(config.TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
