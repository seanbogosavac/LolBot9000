import logging
import re
import sqlite3
import threading
from pathlib import Path

from .errors import (
    DatabaseError,
    DiscordIdAlreadyExists,
    InvalidDiscordId,
    InvalidPlayerName,
    InvalidPuuid,
    NameAlreadyExists,
    PlayerNotFound,
    PuuidAlreadyExists,
)
from .migrations import apply_migrations
from .types import PlayerInfos

logger = logging.getLogger(__name__)

__all__ = ["PlayerRepository", "column"]

NAME_PATTERN = re.compile(r"^[\w .'\-]{1,32}$", re.UNICODE)
DISCORD_ID_PATTERN = re.compile(r"^\d{17,20}$")
PUUID_PATTERN = re.compile(r"^[0-9A-Za-z_\-]{16,128}$")

# Column names accepted by `column`, mapped to their (case-insensitive) lookup expression.
LOOKUP_COLUMNS = {
    "name": "name COLLATE NOCASE",
    "puuid": "puuid",
    "discord_id": "discord_id",
}


def column(name: str) -> str:
    """Return the SQL expression used to look a player up by the given column."""
    try:
        return LOOKUP_COLUMNS[name]
    except KeyError:
        raise ValueError(f"Unknown player lookup column: {name!r}") from None


def _row_to_player(row: sqlite3.Row) -> PlayerInfos:
    return {"name": row["name"], "puuid": row["puuid"], "discord_id": row["discord_id"]}


class PlayerRepository:
    """SQLite-backed registry of the players the bot knows about.

    A single connection is shared across threads (the bot runs its polling loop
    from the event loop thread), guarded by a lock, with WAL enabled so reads
    stay fast and the file survives a container restart.
    """

    def __init__(self, path: str | Path, timeout: float = 5.0) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()
        self._conn: sqlite3.Connection | None = None

        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self.path), timeout=timeout, check_same_thread=False)
        except (sqlite3.Error, OSError) as e:
            raise DatabaseError(f"Could not open the player database at {self.path}: {e}") from e

        conn.row_factory = sqlite3.Row
        with self._lock:
            try:
                conn.execute("PRAGMA journal_mode = WAL")
                conn.execute("PRAGMA foreign_keys = ON")
                apply_migrations(conn)
            except sqlite3.Error as e:
                conn.close()
                raise DatabaseError(f"Could not initialise the player database at {self.path}: {e}") from e

        self._conn = conn
        logger.info("Player database ready at %s", self.path)

    ###
    # LIFECYCLE
    ###

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    def __enter__(self) -> "PlayerRepository":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    @property
    def _db(self) -> sqlite3.Connection:
        if self._conn is None:
            raise DatabaseError("The player database is closed.")
        return self._conn

    def _query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            try:
                return self._db.execute(sql, params).fetchall()
            except sqlite3.Error as e:
                raise DatabaseError(f"Query failed on {self.path}: {e}") from e

    def _execute(self, sql: str, params: tuple = ()) -> int:
        with self._lock:
            try:
                cur = self._db.execute(sql, params)
                self._db.commit()
                return cur.rowcount
            except sqlite3.IntegrityError as e:
                self._db.rollback()
                raise self._integrity_error(str(e).lower()) from e
            except sqlite3.Error as e:
                self._db.rollback()
                raise DatabaseError(f"Write failed on {self.path}: {e}") from e

    def _integrity_error(self, message: str) -> DatabaseError:
        if "players.name" in message:
            return NameAlreadyExists("Un pseudo est déjà pris.")
        if "players.puuid" in message:
            return PuuidAlreadyExists("Un compte Riot est déjà enregistré.")
        if "players.discord_id" in message:
            return DiscordIdAlreadyExists("Un compte Discord est déjà enregistré.")
        return DatabaseError(f"Contrainte d'unicité violée : {message}")

    ###
    # VALIDATION
    ###

    @staticmethod
    def normalize_name(name: str) -> str:
        cleaned = " ".join((name or "").split())
        if not NAME_PATTERN.match(cleaned):
            raise InvalidPlayerName(
                "Un pseudo doit faire entre 1 et 32 caractères, sans caractères spéciaux."
            )
        return cleaned

    @staticmethod
    def normalize_discord_id(discord_id: str) -> str:
        cleaned = str(discord_id or "").strip().strip("<@!>").strip()
        if not DISCORD_ID_PATTERN.match(cleaned):
            raise InvalidDiscordId("Un ID Discord doit être un snowflake numérique de 17 à 20 chiffres.")
        return cleaned

    @staticmethod
    def normalize_puuid(puuid: str) -> str:
        cleaned = str(puuid or "").strip()
        if not PUUID_PATTERN.match(cleaned):
            raise InvalidPuuid("Un puuid Riot doit être une chaîne alphanumérique de 16 à 128 caractères.")
        return cleaned

    ###
    # READS
    ###

    def get(self, value: str, by: str = "name") -> PlayerInfos:
        """Return the player registered under `value`, looked up `by` name, puuid or discord_id."""
        expression = column(by)
        lookup = self.normalize_discord_id(value) if by == "discord_id" else str(value).strip()
        rows = self._query(f"SELECT name, puuid, discord_id FROM players WHERE {expression} = ?", (lookup,))
        if not rows:
            raise PlayerNotFound(f"Aucun joueur trouvé pour {by}={value!r}.")
        return _row_to_player(rows[0])

    def find(self, value: str, by: str = "name") -> PlayerInfos | None:
        """Like `get`, but returns None instead of raising."""
        try:
            return self.get(value, by=by)
        except PlayerNotFound:
            return None

    def all(self) -> list[PlayerInfos]:
        rows = self._query("SELECT name, puuid, discord_id FROM players ORDER BY name COLLATE NOCASE")
        return [_row_to_player(row) for row in rows]

    def names(self) -> list[str]:
        return [player["name"] for player in self.all()]

    def count(self) -> int:
        rows = self._query("SELECT COUNT(*) AS total FROM players")
        return int(rows[0]["total"])

    def exists(self, value: str, by: str = "name") -> bool:
        return self.find(value, by=by) is not None

    ###
    # WRITES
    ###

    def add(self, name: str, discord_id: str, puuid: str) -> PlayerInfos:
        """Register a new player.

        Raises the matching DatabaseError subclass if the name, the Riot account or
        the Discord account is already taken.
        """
        player: PlayerInfos = {
            "name": self.normalize_name(name),
            "discord_id": self.normalize_discord_id(discord_id),
            "puuid": self.normalize_puuid(puuid),
        }

        existing = self.find(player["name"], by="name")
        if existing:
            raise NameAlreadyExists(f"{player['name']} est déjà enregistré.")

        self._execute(
            "INSERT INTO players (name, puuid, discord_id) VALUES (?, ?, ?)",
            (player["name"], player["puuid"], player["discord_id"]),
        )
        logger.info("Registered player %s (discord_id=%s)", player["name"], player["discord_id"])
        return player

    def update(self, name: str, *, discord_id: str | None = None, puuid: str | None = None) -> PlayerInfos:
        """Change the Riot or Discord id of an existing player."""
        current = self.get(name)
        changes: dict[str, str] = {}
        if discord_id is not None:
            changes["discord_id"] = self.normalize_discord_id(discord_id)
        if puuid is not None:
            changes["puuid"] = self.normalize_puuid(puuid)
        if not changes:
            return current

        assignments = ", ".join(f"{key} = ?" for key in changes)
        self._execute(
            f"UPDATE players SET {assignments} WHERE name = ?",
            (*changes.values(), current["name"]),
        )
        logger.info("Updated player %s: %s", current["name"], ", ".join(changes))
        return self.get(current["name"])

    def remove(self, name: str) -> PlayerInfos:
        """Unregister a player and return the row that was removed."""
        player = self.get(name)
        self._execute("DELETE FROM players WHERE name = ?", (player["name"],))
        logger.info("Removed player %s", player["name"])
        return player

    def upsert(self, name: str, discord_id: str, puuid: str) -> PlayerInfos:
        """Add a player, replacing their ids if the name is already registered."""
        if self.exists(name):
            return self.update(name, discord_id=discord_id, puuid=puuid)
        return self.add(name, discord_id, puuid)
