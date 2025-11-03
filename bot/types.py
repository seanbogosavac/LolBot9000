from typing import TypedDict, Optional

class PlayerInfos(TypedDict):
    name: str
    puuid: Optional[str]
    discord_id: Optional[str]
