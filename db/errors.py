__all__ = [
    "DatabaseError",
    "PlayerNotFound",
    "InvalidPlayerName",
    "InvalidDiscordId",
    "InvalidPuuid",
    "NameAlreadyExists",
    "DiscordIdAlreadyExists",
    "PuuidAlreadyExists",
]


class DatabaseError(Exception):
    """Raised when the player database cannot be opened or written."""


class PlayerNotFound(DatabaseError):
    """Raised when the requested player is not registered in the database."""


class InvalidPlayerName(DatabaseError):
    """Raised when a player name is empty or contains illegal characters."""


class InvalidDiscordId(DatabaseError):
    """Raised when a Discord snowflake is not a valid identifier."""


class InvalidPuuid(DatabaseError):
    """Raised when a Riot puuid doesn't look like a puuid at all."""


class NameAlreadyExists(DatabaseError):
    """Raised when a player name is already taken."""


class DiscordIdAlreadyExists(DatabaseError):
    """Raised when a Discord account is already linked to another player."""


class PuuidAlreadyExists(DatabaseError):
    """Raised when a Riot account is already linked to another player."""
