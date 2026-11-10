import pytest

from db import PlayerRepository
from scripts.manage_players import main
from tests.conftest import DISCORD_MAXIME, DISCORD_SEAN, DISCORD_THOMAS, PUUID_MAXIME, PUUID_SEAN, PUUID_THOMAS


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "cli.db")
    with PlayerRepository(path) as repo:
        yield path, repo


def run_cli(*argv):
    return main(list(argv))


def test_list_on_an_empty_database(capsys, db):
    path, _ = db
    assert run_cli("--db", path, "list") == 0
    assert capsys.readouterr().out.strip() == "no player registered"


def test_add_accepts_a_raw_puuid_and_prints_the_row(capsys, db):
    path, repo = db
    assert run_cli("--db", path, "add", "Sean", DISCORD_SEAN, PUUID_SEAN) == 0
    assert repo.get("sean")["puuid"] == PUUID_SEAN
    assert "added Sean" in capsys.readouterr().out


def test_add_resolves_a_riot_id_using_the_api_key(capsys, db, monkeypatch):
    path, repo = db
    monkeypatch.setenv("RIOT_API_KEY", "secret")
    monkeypatch.setattr("scripts.manage_players.RiotClient.get_puuid_by_riot_id",
                        lambda self, riot_id: PUUID_MAXIME)
    assert run_cli("--db", path, "add", "Max", f"<@{DISCORD_MAXIME}>", "Maxime#EUW") == 0
    assert repo.get("Max")["puuid"] == PUUID_MAXIME


def test_add_without_an_api_key_cannot_resolve_a_riot_id(db, monkeypatch):
    path, _ = db
    monkeypatch.delenv("RIOT_API_KEY", raising=False)
    with pytest.raises(SystemExit, match="RIOT_API_KEY"):
        run_cli("--db", path, "add", "Max", DISCORD_MAXIME, "Maxime#EUW")


def test_list_shows_every_player(capsys, db):
    path, repo = db
    repo.add("Sean", DISCORD_SEAN, PUUID_SEAN)
    assert run_cli("--db", path, "list") == 0
    out = capsys.readouterr().out
    assert "Sean" in out and DISCORD_SEAN in out and PUUID_SEAN in out


def test_update_and_remove(capsys, db):
    path, repo = db
    repo.add("Sean", DISCORD_SEAN, PUUID_SEAN)
    assert run_cli("--db", path, "update", "Sean", "--discord-id", DISCORD_THOMAS) == 0
    assert repo.get("Sean")["discord_id"] == DISCORD_THOMAS
    assert run_cli("--db", path, "remove", "Sean") == 0
    assert repo.count() == 0


def test_duplicate_registration_reports_an_error(capsys, db):
    path, repo = db
    repo.add("Sean", DISCORD_SEAN, PUUID_SEAN)
    assert run_cli("--db", path, "add", "Sean", DISCORD_THOMAS, PUUID_THOMAS) == 1
    assert "déjà enregistré" in capsys.readouterr().err


def test_removing_an_unknown_player_reports_an_error(capsys, db):
    path, _ = db
    assert run_cli("--db", path, "remove", "Ghost") == 1
    assert "Aucun joueur" in capsys.readouterr().err


def test_an_unopenable_database_reports_an_error(capsys, tmp_path):
    blocked = tmp_path / "file"
    blocked.write_text("nope")
    assert run_cli("--db", str(blocked / "players.db"), "list") == 1
    assert "error:" in capsys.readouterr().err


def test_seed_imports_the_legacy_environment(capsys, db, legacy_env, monkeypatch):
    path, repo = db
    for key, value in legacy_env.items():
        monkeypatch.setenv(key, value)
    assert run_cli("--db", path, "seed") == 0
    assert "seeded 2" in capsys.readouterr().out
    assert repo.get("Sean")["discord_id"] == DISCORD_SEAN
