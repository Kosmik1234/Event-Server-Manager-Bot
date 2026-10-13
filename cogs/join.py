"""The green "Join Event" and red "Leave Event" buttons.

The thread ID is baked into the button's custom_id ("join-event:<thread_id>"), so the
button needs no database lookup and keeps working after the bot restarts. This is what
discord.py calls a DynamicItem: on startup we register the *pattern*, and whenever
someone clicks a matching button, discord.py rebuilds the item from the custom_id."""
import logging

import discord
from discord.ext import commands

from i18n import t


async def get_participants_count(thread: discord.Thread) -> int | None:
    """Number of members in the thread, excluding the bot. None if the API call failed."""
    try:
        members = await thread.fetch_members()  # needs the privileged Server Members intent
    except discord.HTTPException:
        logging.exception("Failed to receive participant count for thread %s", thread.id)
        return None
    return max(len(members) - 1, 0)  # -1 for the bot, which is always a member of its own thread


def counter_text(count: int, lang: str) -> str:
    return t(lang, "counter", count=count)


async def update_participant_count(store, thread: discord.Thread, lang: str) -> None:
    """Recomputes thread membership and edits the pinned join message in the event channel.
    Called by the on_thread_member_join/remove listeners in auto_thread.py, which fire for
    ANY membership change - these buttons, manual add/remove in Discord's UI, etc. N excludes
    the bot itself."""
    event = store.get_by_thread(thread.id)
    if event is None or event.join_message_id is None or thread.parent is None:
        return
    count = await get_participants_count(thread)
    if count is None:
        return
    try:
        await thread.parent.get_partial_message(event.join_message_id).edit(content=counter_text(count, lang))
    except discord.HTTPException:
        logging.exception("Failed to update participant count for thread %s", thread.id)


class JoinButton(discord.ui.DynamicItem[discord.ui.Button], template=r"join-event:(?P<thread_id>[0-9]+)"):
    def __init__(self, thread_id: int, lang: str):
        super().__init__(
            discord.ui.Button(
                label=t(lang, "join_label"), style=discord.ButtonStyle.success, custom_id=f"join-event:{thread_id}"
            )
        )
        self.thread_id = thread_id

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match):
        return cls(int(match["thread_id"]), interaction.client.lang(interaction.guild))

    async def callback(self, interaction: discord.Interaction):
        lang = interaction.client.lang(interaction.guild)
        # Active threads are usually cached; fall back to an API call if not.
        thread = interaction.guild.get_thread(self.thread_id)
        try:
            if thread is None:
                thread = await interaction.guild.fetch_channel(self.thread_id)
            await thread.add_user(interaction.user)
        except discord.NotFound:
            await interaction.response.send_message(t(lang, "thread_gone"), ephemeral=True)
            return
        except discord.HTTPException:
            logging.exception("Failed to add %s to thread %s", interaction.user, self.thread_id)
            await interaction.response.send_message(t(lang, "join_failed"), ephemeral=True)
            return

        await interaction.response.send_message(t(lang, "joined", thread=thread.mention), ephemeral=True)


class LeaveButton(discord.ui.DynamicItem[discord.ui.Button], template=r"leave-event:(?P<thread_id>[0-9]+)"):
    """Red counterpart of JoinButton: removes the member from the thread."""

    def __init__(self, thread_id: int, lang: str):
        super().__init__(
            discord.ui.Button(
                label=t(lang, "leave_label"), style=discord.ButtonStyle.danger, custom_id=f"leave-event:{thread_id}"
            )
        )
        self.thread_id = thread_id

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match):
        return cls(int(match["thread_id"]), interaction.client.lang(interaction.guild))

    async def callback(self, interaction: discord.Interaction):
        lang = interaction.client.lang(interaction.guild)
        thread = interaction.guild.get_thread(self.thread_id)
        try:
            if thread is None:
                thread = await interaction.guild.fetch_channel(self.thread_id)
            await thread.remove_user(interaction.user)
        except discord.NotFound:
            await interaction.response.send_message(t(lang, "thread_gone"), ephemeral=True)
            return
        except discord.HTTPException:
            logging.exception("Failed to remove %s from thread %s", interaction.user, self.thread_id)
            await interaction.response.send_message(t(lang, "leave_failed"), ephemeral=True)
            return

        await interaction.response.send_message(t(lang, "left"), ephemeral=True)


def join_view(thread_id: int, lang: str) -> discord.ui.View:
    """A view holding the Join and Leave buttons, to attach to a message."""
    view = discord.ui.View(timeout=None)  # timeout=None: the buttons never expire
    view.add_item(JoinButton(thread_id, lang))
    view.add_item(LeaveButton(thread_id, lang))
    return view


async def setup(bot: commands.Bot):
    bot.add_dynamic_items(JoinButton, LeaveButton)
