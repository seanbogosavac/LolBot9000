from typing import TypedDict, List

__all__ = ["PlayerStats", "Participant", "Match", "OngoingMatch"]


class PlayerStats(TypedDict):
    rank: str
    winrate: int


class Participant(TypedDict):
    puuid: str
    champion: str
    kills: int
    deaths: int
    assists: int
    win: bool
    cs: int
    gold: int


class Match(TypedDict):
    gameType: int
    duration: str
    participants: List[Participant]


class OngoingMatch(TypedDict):
    gameId: int
    gameType: int
    players: List[str]
    champions: List[int]
