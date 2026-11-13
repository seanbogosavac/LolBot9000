import logging
import sqlite3
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

__all__ = ["SCHEMA_VERSION", "apply_migrations"]


@dataclass
class Migration:
    """The schema a database is brought to, and the version it is brought to *as*.

    `target` is the value written to `PRAGMA user_version` and must never be reused or
    renumbered: a deployed database sits at the version it was migrated to, and a migration
    whose target it already matches is skipped. That is why the baseline targets version 2
    rather than 1 — every database created by the previous release is already at 2, so a new
    migration has to come after it.

    `statements` describe the table as of this version and are idempotent
    (CREATE ... IF NOT EXISTS), so they do nothing to an existing table. `columns` are then
    added when missing, which is what upgrades an older database: SQLite has no
    "ADD COLUMN IF NOT EXISTS", and checking first lets an interrupted migration resume
    without swallowing an unrelated error.
    """

    target: int
    statements: str = ""
    columns: dict[str, str] = field(default_factory=dict)


# Append-only. Bump SCHEMA_VERSION's meaning by adding an entry whose target is the next
# number, never by editing an existing one.
MIGRATIONS: list[Migration] = [
    Migration(
        target=2,
        statements="""
        CREATE TABLE IF NOT EXISTS players (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL UNIQUE COLLATE NOCASE,
            puuid      TEXT    NOT NULL UNIQUE,
            discord_id TEXT    NOT NULL UNIQUE,
            created_at TEXT    NOT NULL DEFAULT (datetime('now')),
            riot_name  TEXT
        );

        CREATE INDEX IF NOT EXISTS players_name_idx ON players (name COLLATE NOCASE);
        """,
        # A database created before riot_name existed gets the column added here.
        columns={"riot_name": "TEXT"},
    ),
]

SCHEMA_VERSION = MIGRATIONS[-1].target


def current_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def apply_migrations(conn: sqlite3.Connection) -> None:
    """Bring the database up to the newest migration, one transaction per migration.

    Walks the list rather than comparing against SCHEMA_VERSION so a database is upgraded by
    every migration it has not been through yet, whatever order they were appended in.
    """
    version = current_version(conn)
    for migration in MIGRATIONS:
        if version >= migration.target:
            continue
        logger.info("Upgrading the player database to version %d", migration.target)
        _apply(conn, migration)
        version = migration.target


def _apply(conn: sqlite3.Connection, migration: Migration) -> None:
    """Apply one migration and record its version in the same transaction.

    `executescript` commits by itself, so schema changes would land before the version does:
    a container stopped in between leaves a half-migrated database. Running the statements one
    by one inside an explicit transaction means either everything lands or nothing does.
    """
    try:
        if not conn.in_transaction:
            conn.execute("BEGIN")
        for statement in _statements(migration.statements):
            conn.execute(statement)
        existing = _columns(conn)
        for name, definition in migration.columns.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE players ADD COLUMN {name} {definition}")
        conn.execute(f"PRAGMA user_version = {migration.target}")
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise


def _columns(conn: sqlite3.Connection) -> set[str]:
    return {row[1] for row in conn.execute("PRAGMA table_info(players)")}


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
