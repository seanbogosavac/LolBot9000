import pytest

from db import PlayerRepository, legacy_players_from_environment, seed_from_environment
from tests.conftest import DISCORD_MAXIME, DISCORD_SEAN, PUUID_MAXIME, PUUID_SEAN


def test_legacy_layout_is_discovered(legacy_env):
    assert legacy_players_from_environment(legacy_env) == {
        "Sean": {"puuid": PUUID_SEAN, "discord_id": DISCORD_SEAN},
        "Maxime": {"puuid": PUUID_MAXIME, "discord_id": DISCORD_MAXIME},
    }


def test_seeding_an_empty_database_imports_every_legacy_player(legacy_env, repo):
    assert seed_from_environment(repo, legacy_env) == 2
    assert repo.get("sean")["puuid"] == PUUID_SEAN
    assert repo.get("maxime")["discord_id"] == DISCORD_MAXIME


def test_seeding_is_skipped_once_the_database_has_players(legacy_env, seeded):
    assert seed_from_environment(seeded, legacy_env) == 0
    assert seeded.count() == 2


def test_seeding_is_skipped_without_legacy_variables(repo):
    assert seed_from_environment(repo, {}) == 0


def test_incomplete_legacy_entries_are_skipped_not_fatal(repo, caplog):
    assert seed_from_environment(repo, {"RIOT_ID_GUY": PUUID_SEAN}) == 0
    assert repo.count() == 0
    assert "Guy" in caplog.text


def test_seeding_falls_back_to_the_process_environment(legacy_env, monkeypatch, repo):
    for key, value in legacy_env.items():
        monkeypatch.setenv(key, value)
    assert seed_from_environment(repo) == 2
    assert repo.get("sean")["discord_id"] == DISCORD_SEAN
