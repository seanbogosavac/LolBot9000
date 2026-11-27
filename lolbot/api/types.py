from typing import NotRequired, TypedDict

__all__ = ["PlayerStats", "Participant", "Match", "OngoingMatch"]


class PlayerStats(TypedDict):
    rank: str
    winrate: int
    streak: int  # positive = win streak length, negative = lose streak length


class Participant(TypedDict):
    puuid: str
    champion: str  # Riot's internal name (e.g. "XinZhao")
    championId: NotRequired[int]  # used to look up the display name ("Xin Zhao") from Data Dragon
    kills: int
    deaths: int
    assists: int
    win: bool
    cs: int
    gold: int


class Match(TypedDict):
    gameType: int
    duration: str
    participants: list[Participant]


class OngoingMatch(TypedDict):
    gameId: int
    gameType: int
    players: list[str]
    champions: list[int]
