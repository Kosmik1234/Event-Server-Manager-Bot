"""Shared slash-command permission checks."""
import discord
from discord import app_commands

import config


def is_admin_or_mod():
    """Slash-command check: allow Administrators or members with the moderator role."""

    def predicate(interaction: discord.Interaction) -> bool:
        member = interaction.user
        if not isinstance(member, discord.Member):  # used in a DM
            return False
        if member.guild_permissions.administrator:
            return True
        # Config value may be a role name or a numeric ID.
        return any(str(r.id) == config.MODERATOR_ROLE or r.name == config.MODERATOR_ROLE for r in member.roles)

    return app_commands.check(predicate)
