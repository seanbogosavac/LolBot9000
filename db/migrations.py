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
        _apply_one(conn, index + 1, migration)


def _apply_one(conn: sqlite3.Connection, number: int, script: str) -> None:
    """Apply a single migration and bump the version in the same transaction.

    `executescript` commits by itself, so the schema changes would land before the version
    does: a container stopped in between leaves a database that no longer opens, because the
    retry hits `duplicate column name`. Statements are run one by one inside an explicit
    transaction instead, and a statement that is already applied is skipped, so an
    interrupted or half-hand-edited database still comes up.
    """
    try:
        if not conn.in_transaction:
            conn.execute("BEGIN")
        for statement in _statements(script):
            try:
                conn.execute(statement)
            except sqlite3.OperationalError as e:
                if not _already_applied(str(e)):
                    raise
                logger.warning("Migration %d: skipping already applied statement (%s)", number, e)
        conn.execute(f"PRAGMA user_version = {number}")
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise


# SQLite has no "ADD COLUMN IF NOT EXISTS", so a resumed migration re-runs statements that
# already landed. These are the only failures that mean "nothing to do".
ALREADY_APPLIED = ("duplicate column name", "already exists")


def _already_applied(message: str) -> bool:
    return any(needle in message for needle in ALREADY_APPLIED)


def _statements(script: str):
    """Split a migration script into the individual statements sqlite3 can execute."""
    buffer = ""
    for line in script.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            yield buffer
            buffer = ""
    if sqlite3.complete_statement(buffer):
        yield buffer
