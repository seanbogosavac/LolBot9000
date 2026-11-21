import logging
import os
from pathlib import Path
from typing import Dict, Optional
import requests

from api import RiotClient
from db import PlayerRepository
from logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE: Optional[str] = os.getenv("LOG_FILE")

DDRAGON_URL = "https://ddragon.leagueoflegends.com"
DDRAGON_TIMEOUT = (3.05, 10.0)


def fetch_champions_data() -> dict:
    """Fetch the champion list for the latest Data Dragon patch (empty on failure)."""
    try:
        versions = requests.get(f"{DDRAGON_URL}/api/versions.json", timeout=DDRAGON_TIMEOUT)
        versions.raise_for_status()
        version = versions.json()[0]
        response = requests.get(f"{DDRAGON_URL}/cdn/{version}/data/en_US/champion.json", timeout=DDRAGON_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error("Failed to fetch champion data from Data Dragon: %s", e)
        return {"data": {}}


CHAMPIONS_DATA = fetch_champions_data()

# discord.py caches channels by integer id: a string id never hits the cache, so the polling
# loop would call the REST API on every tick.
_channel_env = os.getenv("DISCORD_CHANNEL", "").strip()
DISCORD_CHANNEL: Optional[int] = int(_channel_env) if _channel_env.isdigit() else None
if DISCORD_CHANNEL is None:
    logger.error("DISCORD_CHANNEL is missing or is not a numeric channel id")

DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN")
API_KEY: str = os.getenv("RIOT_API_KEY")

# Players live in SQLite now, so the roster can change without redeploying the bot.
# Set PLAYERS_DB to move the file (docker-compose mounts a volume for it).
BASE_DIR: Path = Path(__file__).resolve().parent
PLAYERS_DB_PATH: Path = Path(os.getenv("PLAYERS_DB", BASE_DIR / "data" / "players.db"))

try:
    players = PlayerRepository(PLAYERS_DB_PATH)
except Exception as e:
    logger.critical("Could not open the players database at %s: %s", PLAYERS_DB_PATH, e)
    raise

riot_client = RiotClient(api_key=API_KEY)

QUEUE_NAMES: Dict[int, str] = {
    400: "Normal Draft",
    420: "Ranked Solo/Duo",
    440: "Ranked Flex",
    450: "ARAM",
    430: "Normal Blind Pick",
}

CHAMPIONS: Dict[int, str] = {}
for champ_name, champ_info in CHAMPIONS_DATA['data'].items():
    champ_id = int(champ_info['key'])
    CHAMPIONS[champ_id] = champ_name
