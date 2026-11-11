"""SQLite-backed player registry.

The bot used to read a fixed set of Riot/Discord ids from the environment; they now
live in a database so players can be added, edited and removed at runtime.
"""

from .errors import (
    DatabaseError,
    DiscordIdAlreadyExists,
    InvalidDiscordId,
    InvalidPlayerName,
    InvalidPuuid,
    InvalidRiotName,
    NameAlreadyExists,
    PlayerNotFound,
    PuuidAlreadyExists,
)
from .migrations import SCHEMA_VERSION
from .repository import PlayerRepository
from .seed import legacy_players_from_environment, seed_from_environment
from .types import PlayerInfos

__all__ = [
    "PlayerRepository",
    "PlayerInfos",
    "DatabaseError",
    "PlayerNotFound",
    "InvalidPlayerName",
    "InvalidDiscordId",
    "InvalidPuuid",
    "InvalidRiotName",
    "NameAlreadyExists",
    "DiscordIdAlreadyExists",
    "PuuidAlreadyExists",
    "SCHEMA_VERSION",
    "seed_from_environment",
    "legacy_players_from_environment",
]
