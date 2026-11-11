import logging

import config
from api import RiotAPIError
from db import (
    DatabaseError,
    DiscordIdAlreadyExists,
    InvalidDiscordId,
    InvalidPuuid,
    InvalidPlayerName,
    InvalidRiotName,
    NameAlreadyExists,
    PlayerInfos,
    PlayerNotFound,
    PuuidAlreadyExists,
)

logger = logging.getLogger(__name__)

DB_UNAVAILABLE = "La base de données des joueurs est indisponible."

# Errors whose message is already phrased for the channel.
USER_FACING_ERRORS = (
    NameAlreadyExists,
    PuuidAlreadyExists,
    DiscordIdAlreadyExists,
    InvalidPlayerName,
    InvalidDiscordId,
    InvalidPuuid,
    InvalidRiotName,
)

__all__ = [
    "PlayerActionError",
    "add_player",
    "remove_player",
    "update_player",
    "list_players",
    "get_player",
    "find_player",
    "get_player_by_discord_id",
    "riot_id_to_puuid",
    "puuid_to_riot_name",
    "ensure_riot_names",
]


class PlayerActionError(Exception):
    """Raised with a Discord-ready message when a player management action fails."""


def riot_id_to_puuid(riot_identifier: str) -> str:
    """Accept either a raw puuid or a "GameName#Tag" Riot ID and return the puuid."""
    identifier = riot_identifier.strip().lstrip("@")
    if "#" not in identifier:
        return identifier  # already a puuid
    return config.riot_client.get_puuid_by_riot_id(identifier)


def puuid_to_riot_name(puuid: str) -> str:
    """Return the in-game Riot ID ("GameName#Tag") of a puuid."""
    return config.riot_client.get_riot_id_by_puuid(puuid)


def riot_name_of(riot_identifier: str) -> str | None:
    """Return the in-game name carried by the identifier the user handed us.

    A `Pseudo#TAG` Riot ID already *is* the in-game name. A raw puuid isn't, and we don't
    spend an extra Riot request on it at registration time: the row is stored without a
    name and `ensure_riot_names` resolves it the next time the roster is displayed.
    """
    identifier = riot_identifier.strip().lstrip("@")
    return identifier if "#" in identifier else None


def add_player(name: str, discord_id: str, riot_identifier: str) -> PlayerInfos:
    """Register a player under `name` with their Discord id and Riot id (or puuid).

    The in-game Riot name is stored too, so `!players` can show it instead of a raw puuid.
    """
    try:
        puuid = riot_id_to_puuid(riot_identifier)
    except RiotAPIError as e:
        logger.error("Could not resolve Riot identifier %r: %s", riot_identifier, e)
        raise PlayerActionError(f"J'arrive pas à trouver le compte Riot **{riot_identifier}**. Vérifie le format `Pseudo#TAG`.") from e

    riot_name = riot_name_of(riot_identifier)

    try:
        return config.players.add(name, discord_id, puuid, riot_name)
    except USER_FACING_ERRORS as e:
        raise PlayerActionError(str(e)) from e
    except DatabaseError as e:
        logger.error("Database error while adding player %s: %s", name, e, exc_info=True)
        raise PlayerActionError(DB_UNAVAILABLE) from e


def update_player(name: str, *, discord_id: str | None = None, riot_identifier: str | None = None) -> PlayerInfos:
    """Re-link an existing player to a new Discord and/or Riot account."""
    puuid: str | None = None
    riot_name: str | None = None
    if riot_identifier:
        try:
            puuid = riot_id_to_puuid(riot_identifier)
        except RiotAPIError as e:
            logger.error("Could not resolve Riot identifier %r: %s", riot_identifier, e)
            raise PlayerActionError(f"J'arrive pas à trouver le compte Riot **{riot_identifier}**. Vérifie le format `Pseudo#TAG`.") from e
        # "" clears the old name when the new account was given as a bare puuid, so the
        # name of the previous account can't linger on the row.
        riot_name = riot_name_of(riot_identifier) or ""

    try:
        return config.players.update(name, discord_id=discord_id, puuid=puuid, riot_name=riot_name)
    except PlayerNotFound as e:
        raise PlayerActionError(f"**{name}** n'est pas dans la liste des joueurs.") from e
    except USER_FACING_ERRORS as e:
        raise PlayerActionError(str(e)) from e
    except DatabaseError as e:
        logger.error("Database error while updating player %s: %s", name, e, exc_info=True)
        raise PlayerActionError(DB_UNAVAILABLE) from e


def remove_player(name: str) -> PlayerInfos:
    """Unregister a player."""
    try:
        return config.players.remove(name)
    except PlayerNotFound as e:
        raise PlayerActionError(f"**{name}** n'est pas dans la liste des joueurs.") from e
    except DatabaseError as e:
        logger.error("Database error while removing player %s: %s", name, e, exc_info=True)
        raise PlayerActionError(DB_UNAVAILABLE) from e


def list_players() -> list[PlayerInfos]:
    """Return every registered player, ordered by name."""
    return _read(config.players.all)


def ensure_riot_names(roster: list[PlayerInfos] | None = None) -> list[PlayerInfos]:
    """Fill in the in-game Riot name of the players that don't have one yet.

    Rows imported from the old `.env` layout (and anything registered while Riot was
    unreachable) only carry a puuid, so we resolve the missing names once and store them.
    A player Riot cannot be reached for is left without a name — the caller falls back to
    showing something — rather than failing the whole roster.
    """
    players = list_players() if roster is None else list(roster)
    missing = [player for player in players if not player.get("riot_name")]
    if not missing:
        return players

    for player in missing:
        try:
            riot_name = puuid_to_riot_name(player["puuid"])
        except RiotAPIError as e:
            logger.warning("Could not resolve the in-game name of %s: %s", player["name"], e)
            continue

        try:
            config.players.update(player["name"], riot_name=riot_name)
        except (PlayerNotFound, DatabaseError) as e:
            logger.warning("Could not store the in-game name of %s: %s", player["name"], e)
            continue

        player["riot_name"] = riot_name

    return players


def get_player(name: str) -> PlayerInfos:
    """Return the player registered under `name`, or raise a channel-ready error."""
    player = _read(lambda: config.players.find(name))
    if player is None:
        raise PlayerActionError(f"C'est qui **{name}** ?")
    return player


def get_player_by_discord_id(discord_id: str) -> PlayerInfos | None:
    """Return the player linked to a Discord account, if any."""
    return _read(lambda: config.players.find(discord_id, by="discord_id"))


def find_player(name: str) -> PlayerInfos | None:
    """Return the player registered under `name`, or None if unknown."""
    return _read(lambda: config.players.find(name))


def _read(operation):
    """Run a read query, turning a broken database into a channel-ready error."""
    try:
        return operation()
    except DatabaseError as e:
        logger.error("Player database unavailable: %s", e, exc_info=True)
        raise PlayerActionError(DB_UNAVAILABLE) from e
