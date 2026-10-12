from typing import TypedDict


class PlayerInfos(TypedDict):
    name: str
    puuid: str | None
    discord_id: str | None
