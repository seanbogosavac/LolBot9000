import sqlite3

import pytest

from db import (
    SCHEMA_VERSION,
    DatabaseError,
    DiscordIdAlreadyExists,
    InvalidDiscordId,
    InvalidPlayerName,
    InvalidPuuid,
    InvalidRiotName,
    NameAlreadyExists,
    PlayerNotFound,
    PlayerRepository,
    PuuidAlreadyExists,
)
from tests.conftest import (
    DISCORD_MAXIME,
    DISCORD_SEAN,
    DISCORD_THOMAS,
    PUUID_MAXIME,
    PUUID_SEAN,
    PUUID_THOMAS,
    RIOT_NAME_SEAN,
)


def test_creates_parent_directory_and_starts_empty(repo, tmp_path):
    assert (tmp_path / "data" / "players.db").exists()
    assert repo.count() == 0
    assert repo.all() == []


def test_schema_is_versioned_and_wal(repo, tmp_path):
    conn = sqlite3.connect(tmp_path / "data" / "players.db")
    try:
        assert int(conn.execute("PRAGMA user_version").fetchone()[0]) == SCHEMA_VERSION
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    finally:
        conn.close()


def test_an_old_database_is_upgraded_in_place(tmp_path):
    """A database created before the riot_name column keeps its rows and gains the column."""
    path = tmp_path / "players.db"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE players (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL UNIQUE COLLATE NOCASE,
            puuid      TEXT    NOT NULL UNIQUE,
            discord_id TEXT    NOT NULL UNIQUE,
            created_at TEXT    NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX players_name_idx ON players (name COLLATE NOCASE);
        INSERT INTO players (name, puuid, discord_id) VALUES ('Sean', 'AbCdEf1234567890_-abcdef1234567890', '123456789012345678');
        PRAGMA user_version = 1;
        """
    )
    conn.commit()
    conn.close()

    with PlayerRepository(path) as repo:
        assert repo.count() == 1
        assert repo.get("Sean")["riot_name"] is None

        repo.update("Sean", riot_name=RIOT_NAME_SEAN)
        assert repo.get("Sean")["riot_name"] == RIOT_NAME_SEAN


def test_add_returns_the_normalized_player(repo):
    player = repo.add("  sean   the  goat ", DISCORD_SEAN, PUUID_SEAN)
    assert player == {"name": "sean the goat", "puuid": PUUID_SEAN, "discord_id": DISCORD_SEAN, "riot_name": None}


def test_add_keeps_the_in_game_riot_name(repo):
    player = repo.add("Sean", DISCORD_SEAN, PUUID_SEAN, "SeanTheGoat#EUW")
    assert player["riot_name"] == "SeanTheGoat#EUW"
    assert repo.get("Sean")["riot_name"] == "SeanTheGoat#EUW"
    assert repo.all()[0]["riot_name"] == "SeanTheGoat#EUW"


def test_riot_name_is_optional_and_stays_null_when_unknown(repo):
    assert repo.add("Sean", DISCORD_SEAN, PUUID_SEAN)["riot_name"] is None


@pytest.mark.parametrize("riot_name", ["@Leading@At#EUW", "a" * 40, "bad;char"])
def test_invalid_riot_names_are_rejected(repo, riot_name):
    with pytest.raises(InvalidRiotName):
        repo.add("Sean", DISCORD_SEAN, PUUID_SEAN, riot_name)
    assert repo.count() == 0


def test_an_empty_riot_name_is_stored_as_unknown(repo):
    assert repo.add("Sean", DISCORD_SEAN, PUUID_SEAN, "   ")["riot_name"] is None


@pytest.mark.parametrize("by,value", [
    ("name", "SEAN"),
    ("puuid", PUUID_SEAN),
    ("discord_id", DISCORD_SEAN),
    ("discord_id", f"<@{DISCORD_SEAN}>"),
    ("discord_id", f"<@!{DISCORD_SEAN}>"),
])
def test_lookups_are_case_insensitive_on_name_and_tolerate_mentions(seeded, by, value):
    assert seeded.get(value, by=by)["name"] == "Sean"


def test_unknown_lookup_raises_and_find_returns_none(seeded):
    with pytest.raises(PlayerNotFound):
        seeded.get("ghost")
    assert seeded.find("ghost") is None


def test_lookup_by_unknown_column_is_rejected(seeded):
    with pytest.raises(ValueError):
        seeded.get("whatever", by="email")


def test_uniqueness_is_enforced_on_every_column(seeded):
    with pytest.raises(NameAlreadyExists):
        seeded.add("sean", DISCORD_THOMAS, PUUID_THOMAS)
    with pytest.raises(PuuidAlreadyExists):
        seeded.add("Other", DISCORD_THOMAS, PUUID_SEAN)
    with pytest.raises(DiscordIdAlreadyExists):
        seeded.add("Other", DISCORD_SEAN, PUUID_THOMAS)


@pytest.mark.parametrize("name", ["", "   ", "a" * 33, "bad/name", "semi;colon", "quote\"d"])
def test_invalid_names_are_rejected(repo, name):
    with pytest.raises(InvalidPlayerName):
        repo.add(name, DISCORD_SEAN, PUUID_SEAN)


@pytest.mark.parametrize("name", ["Max'O", "Le Goff", "Jean-Paul", "Très_Bien"])
def test_names_keep_the_characters_players_actually_use(repo, name):
    assert repo.add(name, DISCORD_SEAN, PUUID_SEAN)["name"] == name


@pytest.mark.parametrize("discord_id", ["", "123", "not-a-snowflake", "1" * 21])
def test_invalid_discord_ids_are_rejected(repo, discord_id):
    with pytest.raises(InvalidDiscordId):
        repo.add("Guy", discord_id, PUUID_SEAN)


@pytest.mark.parametrize("puuid", ["", "short", "has space", "x" * 129])
def test_invalid_puuids_are_rejected(repo, puuid):
    with pytest.raises(InvalidPuuid):
        repo.add("Guy", DISCORD_SEAN, puuid)


def test_failed_insert_leaves_no_partial_row(repo):
    with pytest.raises(InvalidPuuid):
        repo.add("Guy", DISCORD_SEAN, "nope")
    assert repo.count() == 0


def test_update_changes_only_what_is_given(seeded):
    updated = seeded.update("sean", puuid=PUUID_THOMAS)
    assert updated["puuid"] == PUUID_THOMAS
    assert updated["discord_id"] == DISCORD_SEAN
    assert updated["riot_name"] == RIOT_NAME_SEAN

    unchanged = seeded.update("Sean")
    assert unchanged == updated


def test_update_can_rename_the_in_game_riot_name(seeded):
    assert seeded.update("Sean", riot_name="NewName#EUW")["riot_name"] == "NewName#EUW"


def test_update_rejects_taken_ids(seeded):
    with pytest.raises(DiscordIdAlreadyExists):
        seeded.update("Sean", discord_id=DISCORD_MAXIME)
    with pytest.raises(PuuidAlreadyExists):
        seeded.update("Sean", puuid=PUUID_MAXIME)
    assert seeded.get("Sean")["discord_id"] == DISCORD_SEAN


def test_update_of_unknown_player_raises(seeded):
    with pytest.raises(PlayerNotFound):
        seeded.update("ghost", puuid=PUUID_THOMAS)


def test_remove_returns_the_deleted_player(seeded):
    removed = seeded.remove("MAXIME")
    assert removed["name"] == "Maxime"
    assert seeded.count() == 1
    with pytest.raises(PlayerNotFound):
        seeded.remove("Maxime")


def test_upsert_adds_then_replaces(repo):
    repo.upsert("Guy", DISCORD_SEAN, PUUID_SEAN)
    assert repo.count() == 1

    repo.upsert("Guy", DISCORD_SEAN, PUUID_THOMAS)
    assert repo.count() == 1
    assert repo.get("Guy")["puuid"] == PUUID_THOMAS


def test_all_is_ordered_case_insensitively_by_name(seeded):
    seeded.add("adam", DISCORD_THOMAS, PUUID_THOMAS)
    assert seeded.names() == ["adam", "Maxime", "Sean"]


def test_data_survives_reopening(tmp_path):
    path = tmp_path / "players.db"
    with PlayerRepository(path) as repo:
        repo.add("Sean", DISCORD_SEAN, PUUID_SEAN)

    with PlayerRepository(path) as reopened:
        assert reopened.get("sean")["puuid"] == PUUID_SEAN


def test_closed_repository_refuses_to_work(tmp_path):
    repo = PlayerRepository(tmp_path / "players.db")
    repo.close()
    with pytest.raises(DatabaseError):
        repo.all()
    with pytest.raises(DatabaseError):
        repo.add("Sean", DISCORD_SEAN, PUUID_SEAN)


def test_unreachable_database_path_raises(tmp_path):
    blocked = tmp_path / "occupied"
    blocked.write_text("not a directory")
    with pytest.raises(DatabaseError):
        PlayerRepository(blocked / "players.db")
