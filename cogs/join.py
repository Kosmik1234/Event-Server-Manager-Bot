"""The green "Join Event" and red "Leave Event" buttons.

The thread ID is baked into the button's custom_id ("join-event:<thread_id>"), so the
button needs no database lookup and keeps working after the bot restarts. This is what
discord.py calls a DynamicItem: on startup we register the *pattern*, and whenever
someone clicks a matching button, discord.py rebuilds the item from the custom_id."""
import logging

import discord
from discord.ext import commands


async def update_participant_count(thread: discord.Thread) -> None:
    """Recomputes thread membership and edits the pinned "Participants: N" message.
    Called by the on_thread_member_join/remove listeners in auto_thread.py, which fire for
    ANY membership change — this button, manual add/remove in Discord's UI, etc. N excludes
    the bot itself."""
    try:
        members = await thread.fetch_members()
        count = max(len(members) - 1, 0)  # -1 for the bot, which is always a member of its own thread
        pins = await thread.pins()
        if pins:
            await pins[0].edit(content=f"Participants: {count}")
    except discord.HTTPException:
        logging.exception("Failed to update participant count for thread %s", thread.id)


class JoinButton(discord.ui.DynamicItem[discord.ui.Button], template=r"join-event:(?P<thread_id>[0-9]+)"):
    def __init__(self, thread_id: int):
        super().__init__(
            discord.ui.Button(label="Join Event", style=discord.ButtonStyle.success, custom_id=f"join-event:{thread_id}")
        )
        self.thread_id = thread_id

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match):
        return cls(int(match["thread_id"]))

    async def callback(self, interaction: discord.Interaction):
        # Active threads are usually cached; fall back to an API call if not.
        thread = interaction.guild.get_thread(self.thread_id)
        try:
            if thread is None:
                thread = await interaction.guild.fetch_channel(self.thread_id)
            await thread.add_user(interaction.user)
        except discord.NotFound:
            await interaction.response.send_message("This event's thread no longer exists.", ephemeral=True)
            return
        except discord.HTTPException:
            logging.exception("Failed to add %s to thread %s", interaction.user, self.thread_id)
            await interaction.response.send_message("Couldn't add you to the event thread. Try again later.", ephemeral=True)
            return

        await interaction.response.send_message(f"You've joined the event! See {thread.mention}", ephemeral=True)


class LeaveButton(discord.ui.DynamicItem[discord.ui.Button], template=r"leave-event:(?P<thread_id>[0-9]+)"):
    """Red counterpart of JoinButton: removes the member from the thread."""

    def __init__(self, thread_id: int):
        super().__init__(
            discord.ui.Button(label="Leave Event", style=discord.ButtonStyle.danger, custom_id=f"leave-event:{thread_id}")
        )
        self.thread_id = thread_id

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match):
        return cls(int(match["thread_id"]))

    async def callback(self, interaction: discord.Interaction):
        thread = interaction.guild.get_thread(self.thread_id)
        try:
            if thread is None:
                thread = await interaction.guild.fetch_channel(self.thread_id)
            await thread.remove_user(interaction.user)
        except discord.NotFound:
            await interaction.response.send_message("This event's thread no longer exists.", ephemeral=True)
            return
        except discord.HTTPException:
            logging.exception("Failed to remove %s from thread %s", interaction.user, self.thread_id)
            await interaction.response.send_message("Couldn't remove you from the event thread. Try again later.", ephemeral=True)
            return

        await interaction.response.send_message("You've left the event.", ephemeral=True)


def join_view(thread_id: int) -> discord.ui.View:
    """A view holding the Join and Leave buttons, to attach to a message."""
    view = discord.ui.View(timeout=None)  # timeout=None: the buttons never expire
    view.add_item(JoinButton(thread_id))
    view.add_item(LeaveButton(thread_id))
    return view


async def setup(bot: commands.Bot):
    bot.add_dynamic_items(JoinButton, LeaveButton)
