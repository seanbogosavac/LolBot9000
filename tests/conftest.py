import asyncio

import pytest

from lolbot import services
from lolbot.db import PlayerRepository

PUUID_SEAN = "AbCdEf1234567890_-abcdef1234567890"
PUUID_MAXIME = "zzzz12345678901234567890abcdefABCD"
PUUID_THOMAS = "thomas9999999999999999999999999"
DISCORD_SEAN = "123456789012345678"
DISCORD_MAXIME = "987654321098765432"
DISCORD_THOMAS = "555555555555555555"

# The in-game Riot IDs behind those puuids, and the Riot IDs resolving to them.
RIOT_NAME_SEAN = "SeanTheGoat#EUW"
RIOT_NAME_MAXIME = "Maxime#EUW"
RIOT_NAME_THOMAS = "Thomas#EUW"
PUUID_TO_RIOT_NAME = {
    PUUID_SEAN: RIOT_NAME_SEAN,
    PUUID_MAXIME: RIOT_NAME_MAXIME,
    PUUID_THOMAS: RIOT_NAME_THOMAS,
}


def run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Fail loudly instead of calling the real Riot API from a test."""
    import requests

    def blocked(*args, **kwargs):
        raise AssertionError("tests must not perform HTTP requests")

    monkeypatch.setattr(requests.Session, "request", blocked)


@pytest.fixture
def repo(tmp_path):
    with PlayerRepository(tmp_path / "data" / "players.db") as repository:
        yield repository


@pytest.fixture
def seeded(repo):
    repo.add("Sean", DISCORD_SEAN, PUUID_SEAN, RIOT_NAME_SEAN)
    repo.add("Maxime", DISCORD_MAXIME, PUUID_MAXIME, RIOT_NAME_MAXIME)
    return repo


@pytest.fixture
def roster(tmp_path, monkeypatch):
    """A clean database behind the `services.get_players()` the bot reads from."""
    repository = PlayerRepository(tmp_path / "bot-players.db")
    monkeypatch.setattr(services, "get_players", lambda: repository)
    yield repository
    repository.close()


@pytest.fixture
def riot_client():
    """The Riot client the bot shares, for tests to stub methods on."""
    return services.get_riot_client()


@pytest.fixture
def fake_riot(monkeypatch, riot_client):
    """Stub the Riot client the bot shares: Riot ID both ways + ranked stats."""
    riot_ids = {"Maxime#EUW": PUUID_MAXIME, "Thomas#EUW": PUUID_THOMAS}
    stats = {
        PUUID_SEAN: {"rank": "GOLD II 45 LP", "winrate": 55, "streak": 3},
        PUUID_MAXIME: {"rank": "DIAMOND IV 30 LP", "winrate": 51, "streak": -2},
        PUUID_THOMAS: {"rank": "Unranked", "winrate": 0, "streak": 0},
    }

    def resolve(riot_id):
        if riot_id not in riot_ids:
            from lolbot.api import RiotAPIError

            raise RiotAPIError(f"Riot account {riot_id!r} not found.")
        return riot_ids[riot_id]

    def reverse(puuid):
        from lolbot.api import RiotAPIError

        if puuid not in PUUID_TO_RIOT_NAME:
            raise RiotAPIError(f"Riot account for puuid {puuid!r} not found.")
        return PUUID_TO_RIOT_NAME[puuid]

    monkeypatch.setattr(riot_client, "get_puuid_by_riot_id", resolve)
    monkeypatch.setattr(riot_client, "get_riot_id_by_puuid", reverse)
    monkeypatch.setattr(riot_client, "get_player_info", lambda puuid: stats[puuid])
    return riot_ids


class FakeUser:
    def __init__(self, user_id):
        self.id = user_id
        self.name = "Author"


def _as_ids(mentions):
    """Accept a single id, an iterable of ids, or nothing at all."""
    if mentions is None:
        return ()
    if isinstance(mentions, (int, str)):
        return (mentions,)
    return tuple(mentions)


class FakeContext:
    """The sliver of a discord.py Context the commands actually touch."""

    def __init__(self, mentions=None):
        self.message = type("M", (), {"mentions": [FakeUser(m) for m in _as_ids(mentions)]})()
        self.author = FakeUser(DISCORD_THOMAS)
        self.sent = []

    async def send(self, content=None, **kwargs):
        self.sent.append(content)
        return content


@pytest.fixture
def ctx():
    """Build a context, optionally with the mentioned accounts: ctx(DISCORD_SEAN)."""
    return FakeContext


@pytest.fixture
def seeded_roster(roster):
    roster.add("Sean", DISCORD_SEAN, PUUID_SEAN, RIOT_NAME_SEAN)
    roster.add("Maxime", DISCORD_MAXIME, PUUID_MAXIME, RIOT_NAME_MAXIME)
    return roster
