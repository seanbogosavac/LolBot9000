import asyncio

import pytest

import lolbot.bot.loops as loops
from lolbot import services
from lolbot.db import PlayerRepository
from lolbot.api import NoOngoingMatch, RiotAPIError
from tests.conftest import DISCORD_MAXIME, DISCORD_SEAN, PUUID_MAXIME, PUUID_SEAN, run


class FakeChannel:
    def __init__(self):
        self.sent = []

    async def send(self, content=None, **kwargs):
        self.sent.append((content, kwargs.get("embed")))


@pytest.fixture
def channel(monkeypatch):
    """A fake Discord channel in front of the loop, with the settle wait removed.

    The wait is shortened through its constant rather than by patching
    asyncio.sleep, which would affect every coroutine in the process.
    """
    fake = FakeChannel()
    monkeypatch.setattr(loops.bot, "get_channel", lambda _id: fake)
    monkeypatch.setattr(loops, "POST_MATCH_SETTLE_SECONDS", 0)
    monkeypatch.setattr(services, "get_champions", lambda: {157: "Yasuo", 412: "Leona"})
    loops.ongoing_matches.clear()
    loops.pending_recaps.clear()
    yield fake
    loops.ongoing_matches.clear()
    loops.pending_recaps.clear()


def tick():
    run(loops.check_players_in_game.coro())


def in_game(puuid):
    return {"gameId": 42, "gameType": 420, "players": [puuid, "teammate"], "champions": [157, 412]}


def test_a_fresh_game_is_announced_once_per_player(seeded_roster, channel, monkeypatch, riot_client):
    monkeypatch.setattr(riot_client, "get_current_match", lambda puuid: in_game(puuid))
    tick()
    tick()
    assert len(channel.sent) == 2
    assert "Maxime" in channel.sent[0][0]
    assert "Sean" in channel.sent[1][0] and "Yasuo" in channel.sent[1][0]


def test_only_the_announced_player_is_reported(seeded_roster, channel, monkeypatch, riot_client):
    def current(puuid):
        if puuid == PUUID_SEAN:
            return in_game(puuid)
        raise NoOngoingMatch("none")

    monkeypatch.setattr(riot_client, "get_current_match", current)
    tick()
    assert len(channel.sent) == 1 and "Maxime" not in channel.sent[0][0]


def test_the_recap_is_posted_when_a_game_ends(seeded_roster, channel, monkeypatch, riot_client):
    match = {
        "gameType": 420,
        "duration": "27:04",
        "participants": [
            {"puuid": PUUID_SEAN, "champion": "Yasuo", "kills": 12, "deaths": 2, "assists": 7,
             "win": True, "cs": 210, "gold": 15000},
            {"puuid": PUUID_MAXIME, "champion": "Leona", "kills": 1, "deaths": 9, "assists": 20,
             "win": False, "cs": 40, "gold": 9000},
        ],
    }

    def current(puuid):
        if puuid == PUUID_SEAN:
            return in_game(puuid)
        raise NoOngoingMatch("none")

    monkeypatch.setattr(riot_client, "get_current_match", current)
    monkeypatch.setattr(riot_client, "get_last_match_id", lambda puuid: "EUW_1")
    monkeypatch.setattr(riot_client, "get_match_data", lambda _id: match)

    tick()
    assert "Yasuo" in channel.sent[0][0]

    # Sean's game ends
    monkeypatch.setattr(riot_client, "get_current_match", lambda puuid: (_ for _ in ()).throw(NoOngoingMatch("none")))
    channel.sent.clear()
    tick()
    assert "Sean a retourné" in channel.sent[0][0]
    assert channel.sent[0][1].title == "Dernier match de Sean"
    assert loops.ongoing_matches == {}


def _shared_match(sean_wins=True, maxime_wins=True):
    return {
        "gameType": 420,
        "duration": "27:04",
        "participants": [
            {"puuid": PUUID_SEAN, "champion": "Yasuo", "kills": 12, "deaths": 2, "assists": 7,
             "win": sean_wins, "cs": 210, "gold": 15000},
            {"puuid": PUUID_MAXIME, "champion": "Leona", "kills": 1, "deaths": 9, "assists": 20,
             "win": maxime_wins, "cs": 40, "gold": 9000},
        ],
    }


def _end_game(monkeypatch, riot_client, match):
    monkeypatch.setattr(riot_client, "get_current_match", lambda puuid: (_ for _ in ()).throw(NoOngoingMatch("none")))
    monkeypatch.setattr(riot_client, "get_last_match_id", lambda puuid: "EUW_1")
    monkeypatch.setattr(riot_client, "get_match_data", lambda _id: match)


def test_players_in_the_same_game_get_a_single_recap(seeded_roster, channel, monkeypatch, riot_client):
    monkeypatch.setattr(riot_client, "get_current_match", lambda puuid: in_game(puuid))
    tick()
    channel.sent.clear()

    _end_game(monkeypatch, riot_client, _shared_match(sean_wins=True, maxime_wins=False))
    tick()
    assert len(channel.sent) == 1
    content, embed = channel.sent[0]
    assert "Sean a gagné" in content and "Maxime a perdu" in content
    assert embed.title == "Dernier match de Maxime, Sean" or embed.title == "Dernier match de Sean, Maxime"
    assert loops.ongoing_matches == {} and loops.pending_recaps == {}


def test_the_recap_waits_until_every_player_has_left_the_game(seeded_roster, channel, monkeypatch, riot_client):
    monkeypatch.setattr(riot_client, "get_current_match", lambda puuid: in_game(puuid))
    tick()
    channel.sent.clear()

    still_in = {PUUID_MAXIME}

    def current(puuid):
        if puuid in still_in:
            return in_game(puuid)
        raise NoOngoingMatch("none")

    _end_game(monkeypatch, riot_client, _shared_match())
    monkeypatch.setattr(riot_client, "get_current_match", current)
    tick()
    assert channel.sent == []

    still_in.clear()
    tick()
    assert len(channel.sent) == 1
    assert "Sean a gagné" in channel.sent[0][0] and "Maxime a gagné" in channel.sent[0][0]


def test_a_failed_poll_does_not_end_the_game(seeded_roster, channel, monkeypatch, riot_client):
    monkeypatch.setattr(riot_client, "get_current_match", lambda puuid: in_game(puuid))
    tick()
    channel.sent.clear()

    monkeypatch.setattr(riot_client, "get_current_match", lambda puuid: (_ for _ in ()).throw(RiotAPIError("boom")))
    tick()
    assert channel.sent == [] and len(loops.ongoing_matches) == 2


def test_a_player_added_mid_flight_is_picked_up(roster, channel, monkeypatch, riot_client):
    monkeypatch.setattr(riot_client, "get_current_match", lambda puuid: (_ for _ in ()).throw(NoOngoingMatch("none")))
    tick()
    assert channel.sent == []

    roster.add("Maxime", DISCORD_MAXIME, PUUID_MAXIME)
    monkeypatch.setattr(riot_client, "get_current_match", lambda puuid: in_game(puuid))
    tick()
    assert "Maxime" in channel.sent[0][0]


def test_an_untracked_game_type_is_announced_but_not_recapped(seeded_roster, channel, monkeypatch, riot_client):
    def current(puuid):
        if puuid == PUUID_SEAN:
            return {"gameId": 7, "gameType": 9999, "players": [puuid], "champions": [157]}
        raise NoOngoingMatch("none")

    monkeypatch.setattr(riot_client, "get_current_match", current)
    tick()
    assert "non détectée" in channel.sent[0][0]
    assert loops.ongoing_matches[PUUID_SEAN] == 0

    monkeypatch.setattr(riot_client, "get_current_match", lambda puuid: (_ for _ in ()).throw(NoOngoingMatch("none")))
    channel.sent.clear()
    tick()
    assert channel.sent == []


def test_a_riot_api_failure_for_one_player_does_not_stop_the_others(seeded_roster, channel, monkeypatch, riot_client):
    def current(puuid):
        if puuid == PUUID_SEAN:
            raise RiotAPIError("boom")
        return in_game(puuid)

    monkeypatch.setattr(riot_client, "get_current_match", current)
    tick()
    assert len(channel.sent) == 1 and "Maxime" in channel.sent[0][0]


def test_a_missing_channel_ends_the_tick_quietly(roster, monkeypatch):
    async def failing_fetch(channel_id):
        raise RiotAPIError("no channel")

    monkeypatch.setattr(loops.bot, "get_channel", lambda _id: None)
    monkeypatch.setattr(loops.bot, "fetch_channel", failing_fetch)
    tick()  # must not raise


def test_a_broken_database_skips_the_tick_instead_of_killing_the_loop(roster, channel, monkeypatch, riot_client):
    monkeypatch.setattr(riot_client, "get_current_match", lambda puuid: in_game(puuid))
    roster.close()
    tick()  # must swallow the failure
    assert channel.sent == []

    roster = PlayerRepository(str(roster.path))
    monkeypatch.setattr(services, "get_players", lambda: roster)
    roster.add("Sean", DISCORD_SEAN, PUUID_SEAN)
    tick()
    assert "Sean" in channel.sent[0][0]
    roster.close()


def test_yannis_still_gets_the_shoutout(roster, channel, monkeypatch, riot_client):
    roster.add("Yannis", DISCORD_SEAN, PUUID_SEAN)
    monkeypatch.setattr(riot_client, "get_current_match", lambda puuid: in_game(puuid))
    tick()
    assert "@everyone Yannis" in channel.sent[0][0]


def test_the_loop_does_not_block_the_event_loop_while_riot_is_slow(seeded_roster, channel, monkeypatch, riot_client):
    """Regression: a rate-limit sleep used to freeze Discord heartbeats."""
    import time

    def slow_current(puuid):
        time.sleep(0.05)  # stands in for the retry sleep in RiotClient._request
        raise NoOngoingMatch("none")

    monkeypatch.setattr(riot_client, "get_current_match", slow_current)

    async def scenario():
        ticks = []

        async def heartbeat():
            while True:
                await asyncio.sleep(0.01)
                ticks.append(1)

        hb = asyncio.create_task(heartbeat())
        await loops.check_players_in_game.coro()
        hb.cancel()
        return ticks

    ticks = run(scenario())
    # 2 players x 50ms of blocking = 100ms; a frozen loop would yield ~0
    assert len(ticks) > 5, f"event loop starved during Riot calls ({len(ticks)} ticks)"
