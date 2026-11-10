from typing import TypedDict

__all__ = ["PlayerInfos"]


class PlayerInfos(TypedDict):
    """A registered player: how we call them, their Riot account and their Discord account."""

    name: str
    puuid: str
    discord_id: str
