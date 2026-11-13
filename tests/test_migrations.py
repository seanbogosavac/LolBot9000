import sqlite3

import pytest

from db import PlayerRepository
from db.migrations import MIGRATIONS, Migration, _apply, apply_migrations
from tests.conftest import PUUID_SEAN, RIOT_NAME_SEAN

V1_SCHEMA = """
CREATE TABLE players (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    puuid      TEXT    NOT NULL UNIQUE,
    discord_id TEXT    NOT NULL UNIQUE,
    created_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

V2_SCHEMA = V1_SCHEMA + "\nALTER TABLE players ADD COLUMN riot_name TEXT;\n"


def version(conn) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def columns(conn) -> list[str]:
    return [row[1] for row in conn.execute("PRAGMA table_info(players)")]


@pytest.fixture
def database_at(tmp_path):
    """Build a database on an old schema, at a given version, holding one Sean row."""
    counter = {"n": 0}

    def build(script: str, at: int):
        counter["n"] += 1
        path = tmp_path / f"players-{counter['n']}.db"
        conn = sqlite3.connect(path)
        conn.executescript(script)
        conn.execute("INSERT INTO players (name, puuid, discord_id) VALUES ('Sean', ?, ?)", (PUUID_SEAN, "123456789012345678"))
        conn.execute(f"PRAGMA user_version = {at}")
        conn.commit()
        conn.close()
        return path

    return build


def test_a_fresh_database_is_created_with_the_full_schema(tmp_path):
    path = tmp_path / "players.db"
    with PlayerRepository(path) as repo:
        assert repo.add("Sean", "123456789012345678", PUUID_SEAN, RIOT_NAME_SEAN)["riot_name"] == RIOT_NAME_SEAN

    conn = sqlite3.connect(path)
    assert version(conn) == 2
    assert "riot_name" in columns(conn)
    conn.close()


def test_upgrading_an_old_database_adds_the_column_without_losing_rows(database_at):
    path = database_at(V1_SCHEMA, 1)
    with PlayerRepository(path) as repo:
        assert repo.count() == 1
        assert repo.get("Sean")["riot_name"] is None

        repo.update("Sean", riot_name=RIOT_NAME_SEAN)
        assert repo.get("Sean")["riot_name"] == RIOT_NAME_SEAN

    assert version(sqlite3.connect(path)) == 2


def test_a_database_already_at_the_current_version_is_left_alone(database_at):
    path = database_at(V2_SCHEMA, 2)
    with PlayerRepository(path) as repo:
        assert repo.get("Sean")["riot_name"] is None
    assert version(sqlite3.connect(path)) == 2


def test_a_half_applied_database_still_opens(database_at):
    """The crash window that used to brick the bot: the column exists, the version doesn't.

    Re-running `ALTER TABLE ADD COLUMN` raises `duplicate column name`, which stopped the bot
    from starting at all. The column is checked before it is added, so the migration resumes.
    """
    path = database_at(V2_SCHEMA, 1)
    assert version(sqlite3.connect(path)) == 1

    with PlayerRepository(path) as repo:
        assert repo.count() == 1
    assert version(sqlite3.connect(path)) == 2


def test_a_migration_and_its_version_bump_commit_together(database_at):
    """A migration interrupted before it commits must leave no half-applied schema behind."""
    conn = sqlite3.connect(database_at(V1_SCHEMA, 1))
    interrupted = Migration(target=2, columns={"riot_name": "TEXT", "broken": "SELECT no_such_function(1)"})

    with pytest.raises(sqlite3.Error):
        _apply(conn, interrupted)

    assert version(conn) == 1, "the version was bumped even though the migration failed"
    assert "riot_name" not in columns(conn), "the column landed even though the migration failed"
    conn.close()


def test_migrations_are_a_no_op_once_applied(database_at):
    conn = sqlite3.connect(database_at(V1_SCHEMA, 1))
    apply_migrations(conn)
    after_first = (version(conn), columns(conn))
    apply_migrations(conn)
    assert (version(conn), columns(conn)) == after_first
    conn.close()


def test_a_future_migration_still_reaches_deployed_databases(database_at):
    """Deployed databases sit at version 2, so the next migration must target a higher number.

    Squashing the schema into a baseline that restarted the count at 1 would leave fresh
    installs at 1 and deployed ones at 2, and the next migration would be skipped everywhere
    the upgrade actually mattered.
    """
    path = database_at(V2_SCHEMA, 2)
    conn = sqlite3.connect(path)
    apply_migrations(conn)
    assert "role" not in columns(conn)

    original = list(MIGRATIONS)
    try:
        MIGRATIONS.append(Migration(target=3, columns={"role": "TEXT"}))
        apply_migrations(conn)
        assert "role" in columns(conn)
        assert version(conn) == 3
    finally:
        MIGRATIONS[:] = original
        conn.close()
