from typing import TypedDict

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
    participants: list[Participant]


class OngoingMatch(TypedDict):
    gameId: int
    gameType: int
    players: list[str]
    champions: list[int]
