"""Shared runtime objects, created on first use.

They are not built at import time so that importing the package stays free of I/O (network,
database). The entry points call these getters once at startup to fail fast; everything
else goes through the same functions, which tests can patch.
"""
import logging
from functools import lru_cache

from lolbot import settings
from lolbot.api import RiotClient
from lolbot.api.ddragon import champions_by_id
from lolbot.db import PlayerRepository

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_players() -> PlayerRepository:
    """The SQLite player roster."""
    try:
        return PlayerRepository(settings.PLAYERS_DB_PATH)
    except Exception as e:
        logger.critical("Could not open the players database at %s: %s", settings.PLAYERS_DB_PATH, e)
        raise


@lru_cache(maxsize=1)
def get_riot_client() -> RiotClient:
    """The Riot API client shared by the bot."""
    return RiotClient(api_key=settings.RIOT_API_KEY)


@lru_cache(maxsize=1)
def get_champions() -> dict[int, str]:
    """Champion id → name, fetched once from Data Dragon."""
    return champions_by_id()
