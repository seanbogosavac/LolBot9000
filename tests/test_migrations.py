import sqlite3

import pytest

from db import PlayerRepository
from db.migrations import MIGRATIONS, _apply_one, apply_migrations
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


def version(conn) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def columns(conn) -> list[str]:
    return [row[1] for row in conn.execute("PRAGMA table_info(players)")]


@pytest.fixture
def v1_database(tmp_path):
    """A database written by the previous release, version 1 and no riot_name column."""
    path = tmp_path / "players.db"
    conn = sqlite3.connect(path)
    conn.executescript(V1_SCHEMA + "PRAGMA user_version = 1;")
    conn.commit()
    conn.close()
    return path


def test_upgrading_adds_the_column_without_losing_rows(v1_database):
    conn = sqlite3.connect(v1_database)
    conn.execute("INSERT INTO players (name, puuid, discord_id) VALUES ('Sean', ?, ?)", (PUUID_SEAN, "123456789012345678"))
    conn.commit()
    conn.close()

    with PlayerRepository(v1_database) as repo:
        assert repo.get("Sean")["riot_name"] is None
        repo.update("Sean", riot_name=RIOT_NAME_SEAN)
        assert repo.get("Sean")["riot_name"] == RIOT_NAME_SEAN

    assert version(sqlite3.connect(v1_database)) == len(MIGRATIONS)


def test_a_migration_and_its_version_bump_commit_together(v1_database):
    """A migration interrupted before it commits must leave no half-applied schema behind."""
    conn = sqlite3.connect(v1_database)
    conn.execute("INSERT INTO players (name, puuid, discord_id) VALUES ('Sean', ?, ?)", (PUUID_SEAN, "123456789012345678"))
    conn.commit()

    # The column is added, then the migration dies before it can record the new version.
    broken_script = MIGRATIONS[1] + " SELECT no_such_function(1);"
    with pytest.raises(sqlite3.Error):
        _apply_one(conn, 2, broken_script)

    assert version(conn) == 1, "the version was bumped even though the migration failed"
    assert "riot_name" not in columns(conn), "the column landed even though the migration failed"
    conn.close()


def test_a_half_applied_database_still_opens(v1_database, caplog):
    """The crash window that used to brick the bot: the column exists, the version doesn't.

    Re-running `ALTER TABLE ADD COLUMN` raises `duplicate column name`, which stopped the
    bot from starting at all. An interrupted migration now resumes instead.
    """
    conn = sqlite3.connect(v1_database)
    conn.executescript(MIGRATIONS[1])  # column added, PRAGMA user_version left at 1
    conn.close()
    assert version(sqlite3.connect(v1_database)) == 1

    with PlayerRepository(v1_database) as repo:
        assert repo.count() == 0
        assert "riot_name" in columns(sqlite3.connect(v1_database))
    assert "skipping already applied statement" in caplog.text


def test_migrations_are_a_no_op_once_applied(v1_database):
    conn = sqlite3.connect(v1_database)
    apply_migrations(conn)
    after_first = (version(conn), columns(conn))
    apply_migrations(conn)
    assert (version(conn), columns(conn)) == after_first
    conn.close()
