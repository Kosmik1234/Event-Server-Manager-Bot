"""Central place for settings. Everything comes from environment variables so the
same code runs locally (.env file) and on Railway (Variables tab)."""
import os

from dotenv import load_dotenv

# Reads a local .env file if present. On Railway there is no .env; the real
# environment variables are used and this call quietly does nothing.
load_dotenv()

TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
EVENT_CATEGORY = os.environ.get("EVENT_CATEGORY", "Events")
MODERATOR_ROLE = os.environ.get("MODERATOR_ROLE", "Moderator")
DEV_GUILD_ID = int(os.environ["DEV_GUILD_ID"]) if os.environ.get("DEV_GUILD_ID") else None
EVENTS_FILE = os.environ.get("EVENTS_FILE", "data/events.json")
