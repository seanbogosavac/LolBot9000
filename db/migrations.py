import logging
import sqlite3

logger = logging.getLogger(__name__)

__all__ = ["SCHEMA_VERSION", "apply_migrations"]

# Each migration bumps PRAGMA user_version by one, so the list must stay append-only.
MIGRATIONS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS players (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        name       TEXT    NOT NULL UNIQUE COLLATE NOCASE,
        puuid      TEXT    NOT NULL UNIQUE,
        discord_id TEXT    NOT NULL UNIQUE,
        created_at TEXT    NOT NULL DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS players_name_idx ON players (name COLLATE NOCASE);
    """,
    """
    -- The in-game Riot name ("GameName#TAG") of each player, so the roster can be shown
    -- without printing raw puuids. NULL until we resolve it from the Account API.
    ALTER TABLE players ADD COLUMN riot_name TEXT;
    """,
]

SCHEMA_VERSION = len(MIGRATIONS)


def current_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def apply_migrations(conn: sqlite3.Connection) -> None:
    """Bring the database up to SCHEMA_VERSION, one transaction per migration."""
    version = current_version(conn)
    if version >= SCHEMA_VERSION:
        return

    for index, migration in enumerate(MIGRATIONS[version:], start=version):
        logger.info("Applying database migration %d", index + 1)
        conn.executescript(migration)
        conn.execute(f"PRAGMA user_version = {index + 1}")
        conn.commit()
