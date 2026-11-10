import logging
import os
import re
from collections.abc import Mapping

from .errors import DatabaseError
from .repository import PlayerRepository

logger = logging.getLogger(__name__)

__all__ = ["seed_from_environment", "legacy_players_from_environment"]

RIOT_ID_KEY = re.compile(r"^RIOT_ID_(.+)$")
DISCORD_ID_PREFIX = "DISCORD_ID_"

# The player table is only seeded when it is empty, so these names are never
# hardcoded in the bot anymore — they are just the first rows we import.


def legacy_players_from_environment(env: Mapping[str, str] | None = None) -> dict[str, dict[str, str]]:
    """Read the pre-database `.env` layout (RIOT_ID_SEAN / DISCORD_ID_SEAN, ...)."""
    source = os.environ if env is None else env
    players: dict[str, dict[str, str]] = {}

    for key, puuid in source.items():
        match = RIOT_ID_KEY.match(key)
        if not match or not puuid:
            continue

        handle = match.group(1)
        discord_id = source.get(f"{DISCORD_ID_PREFIX}{handle}", "")
        players[handle.capitalize()] = {"puuid": puuid, "discord_id": discord_id}

    return players


def seed_from_environment(repo: PlayerRepository, env: Mapping[str, str] | None = None) -> int:
    """Import the legacy `.env` players into an empty database.

    Returns the number of players added; a database that already has players is
    left untouched.
    """
    if repo.count() > 0:
        return 0

    added = 0
    for name, ids in legacy_players_from_environment(env).items():
        try:
            repo.add(name, ids["discord_id"], ids["puuid"])
            added += 1
        except DatabaseError as e:
            logger.warning("Skipped legacy player %s during seed: %s", name, e)

    if added:
        logger.info("Seeded %d player(s) from the environment into %s", added, repo.path)
    return added
