from typing import TypedDict

__all__ = ["PlayerInfos"]


class PlayerInfos(TypedDict):
    """A registered player: how we call them, their Riot account and their Discord account.

    `riot_name` is the in-game Riot ID ("GameName#TAG"); it is None for players registered
    before the column existed and for accounts Riot could not be reached for.
    """

    name: str
    puuid: str
    discord_id: str
    riot_name: str | None
