import pytest

import config
from api import RiotAPIError
from bot.roster import (
    PlayerActionError,
    add_player,
    ensure_riot_names,
    find_player,
    get_player,
    get_player_by_discord_id,
    list_players,
    puuid_to_riot_name,
    remove_player,
    riot_id_to_puuid,
    update_player,
)
from db import PlayerNotFound
from tests.conftest import (
    DISCORD_MAXIME,
    DISCORD_SEAN,
    DISCORD_THOMAS,
    PUUID_MAXIME,
    PUUID_SEAN,
    PUUID_THOMAS,
    RIOT_NAME_SEAN,
)


def test_riot_id_to_puuid_passes_a_raw_puuid_through(fake_riot):
    assert riot_id_to_puuid(f"  {PUUID_SEAN} ") == PUUID_SEAN


def test_riot_id_to_puuid_resolves_a_named_account(fake_riot):
    assert riot_id_to_puuid("@Maxime#EUW") == PUUID_MAXIME


def test_puuid_to_riot_name_resolves_an_in_game_name(fake_riot):
    assert puuid_to_riot_name(PUUID_SEAN) == RIOT_NAME_SEAN


def test_add_player_resolves_a_riot_id_and_stores_it(roster, fake_riot):
    player = add_player("Max", DISCORD_MAXIME, "Maxime#EUW")
    assert player == {"name": "Max", "discord_id": DISCORD_MAXIME, "puuid": PUUID_MAXIME, "riot_name": "Maxime#EUW"}
    assert roster.get("max") == player


def test_add_player_accepts_a_raw_puuid(roster, fake_riot):
    assert add_player("Thomas", DISCORD_THOMAS, PUUID_THOMAS)["puuid"] == PUUID_THOMAS


def test_add_player_stores_no_name_for_a_raw_puuid(roster, fake_riot):
    """The name of a bare puuid isn't guessed at registration; !players resolves it later."""
    assert add_player("Sean", DISCORD_SEAN, PUUID_SEAN)["riot_name"] is None


def test_add_player_reports_an_unresolvable_riot_id_without_writing(roster, fake_riot):
    with pytest.raises(PlayerActionError, match="Pseudo#TAG"):
        add_player("Ghost", DISCORD_THOMAS, "Ghost#NOPE")
    assert roster.count() == 0


def test_add_player_reports_a_taken_name_or_account(seeded_roster, fake_riot):
    with pytest.raises(PlayerActionError, match="déjà enregistré"):
        add_player("sean", DISCORD_THOMAS, "Thomas#EUW")
    with pytest.raises(PlayerActionError, match="déjà enregistré"):
        add_player("Other", DISCORD_SEAN, "Thomas#EUW")
    assert seeded_roster.count() == 2


@pytest.mark.parametrize("name,discord_id", [("  ", DISCORD_SEAN), ("bad/name", DISCORD_SEAN), ("Guy", "12", )])
def test_add_player_reports_invalid_input(seeded_roster, name, discord_id):
    with pytest.raises(PlayerActionError):
        add_player(name, discord_id, PUUID_THOMAS)


def test_update_player_relinks_accounts(seeded_roster, fake_riot):
    player = update_player("Sean", discord_id=DISCORD_THOMAS)
    assert player["discord_id"] == DISCORD_THOMAS
    assert player["puuid"] == PUUID_SEAN
    assert player["riot_name"] == RIOT_NAME_SEAN

    player = update_player("Sean", riot_identifier="Thomas#EUW")
    assert player["puuid"] == PUUID_THOMAS
    assert player["riot_name"] == "Thomas#EUW"


def test_update_player_reports_unknown_player(seeded_roster):
    with pytest.raises(PlayerActionError, match="pas dans la liste"):
        update_player("Ghost", discord_id=DISCORD_THOMAS)


def test_update_player_reports_a_riot_id_it_cannot_resolve(seeded_roster, fake_riot):
    with pytest.raises(PlayerActionError, match="Pseudo#TAG"):
        update_player("Sean", riot_identifier="Ghost#NOPE")
    assert seeded_roster.get("Sean")["puuid"] == PUUID_SEAN


def test_remove_player_returns_the_removed_row(seeded_roster):
    assert remove_player("MAXIME")["name"] == "Maxime"
    assert seeded_roster.count() == 1
    with pytest.raises(PlayerActionError, match="pas dans la liste"):
        remove_player("Maxime")


def test_reads_go_through_the_service(seeded_roster):
    assert [p["name"] for p in list_players()] == ["Maxime", "Sean"]
    assert get_player("sean")["discord_id"] == DISCORD_SEAN
    assert get_player_by_discord_id(f"<@{DISCORD_SEAN}>")["name"] == "Sean"
    assert get_player_by_discord_id(DISCORD_THOMAS) is None
    assert find_player("nope") is None
    with pytest.raises(PlayerActionError, match="C'est qui"):
        get_player("nope")


def test_service_raises_when_the_database_is_gone(roster, fake_riot):
    roster.close()
    with pytest.raises(PlayerActionError):
        add_player("Guy", DISCORD_THOMAS, PUUID_THOMAS)
    with pytest.raises(PlayerActionError):
        list_players()


def test_service_keeps_typed_errors_available_for_callers(roster):
    with pytest.raises(PlayerNotFound):
        roster.get("nobody")


###
# IN-GAME NAME BACKFILL
###


def test_ensure_riot_names_fills_the_rows_imported_without_a_name(roster, fake_riot):
    roster.add("Sean", DISCORD_SEAN, PUUID_SEAN)  # e.g. a row that predates riot_name
    assert roster.get("Sean")["riot_name"] is None

    players = ensure_riot_names()
    assert players[0]["riot_name"] == RIOT_NAME_SEAN
    assert roster.get("Sean")["riot_name"] == RIOT_NAME_SEAN


def test_ensure_riot_names_leaves_known_names_alone(roster, fake_riot, monkeypatch):
    roster.add("Sean", DISCORD_SEAN, PUUID_SEAN, RIOT_NAME_SEAN)

    def no_call(puuid):
        raise AssertionError("must not re-resolve a player that already has a name")

    monkeypatch.setattr(config.riot_client, "get_riot_id_by_puuid", no_call)
    assert ensure_riot_names()[0]["riot_name"] == RIOT_NAME_SEAN


def test_ensure_riot_names_keeps_going_when_riot_cannot_be_reached(roster, fake_riot, monkeypatch):
    roster.add("Sean", DISCORD_SEAN, PUUID_SEAN)
    roster.add("Maxime", DISCORD_MAXIME, PUUID_MAXIME)

    def only_sean(puuid):
        if puuid == PUUID_MAXIME:
            raise RiotAPIError("unreachable")
        return RIOT_NAME_SEAN

    monkeypatch.setattr(config.riot_client, "get_riot_id_by_puuid", only_sean)
    players = {p["name"]: p["riot_name"] for p in ensure_riot_names()}
    assert players == {"Sean": RIOT_NAME_SEAN, "Maxime": None}
