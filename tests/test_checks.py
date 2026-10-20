from unittest.mock import MagicMock

import discord

import config
from checks import is_admin_or_mod


def predicate():
    def command(): ...
    is_admin_or_mod()(command)
    return command.__discord_app_commands_checks__[0]


def _role(role_id, name):
    role = MagicMock(id=role_id)
    role.name = name  # MagicMock(name=...) would set the mock's repr name, not the attribute
    return role


def interaction(*, admin=False, roles=()):
    member = MagicMock(spec=discord.Member)
    member.guild_permissions = MagicMock(administrator=admin)
    member.roles = [_role(rid, name) for rid, name in roles]
    return MagicMock(user=member)


def test_admin_allowed():
    assert predicate()(interaction(admin=True)) is True


def test_moderator_role_by_name(monkeypatch):
    monkeypatch.setattr(config, "MODERATOR_ROLE", "Moderator")
    assert predicate()(interaction(roles=[(1, "Moderator")])) is True


def test_moderator_role_by_id(monkeypatch):
    monkeypatch.setattr(config, "MODERATOR_ROLE", "12345")
    assert predicate()(interaction(roles=[(12345, "Whatever")])) is True


def test_regular_member_denied(monkeypatch):
    monkeypatch.setattr(config, "MODERATOR_ROLE", "Moderator")
    assert predicate()(interaction(roles=[(1, "Member")])) is False


def test_dm_user_denied():
    assert predicate()(MagicMock(user=MagicMock(spec=discord.User))) is False
