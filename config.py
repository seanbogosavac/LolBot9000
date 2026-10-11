import logging
import os
from typing import Dict, Optional
import requests

from bot.types import PlayerInfos
from logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE: Optional[str] = os.getenv("LOG_FILE")

try:
    CHAMPIONS_DATA = requests.get("https://ddragon.leagueoflegends.com/cdn/13.14.1/data/en_US/champion.json").json()
except Exception as e:
    logger.error("Failed to fetch champion data from Data Dragon: %s", e)
    CHAMPIONS_DATA = {"data": {}}

DISCORD_CHANNEL: str = os.getenv("DISCORD_CHANNEL")
DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN")
API_KEY: str = os.getenv("RIOT_API_KEY")

PLAYERS: Dict[str, PlayerInfos] = {
    "sean": {
        "name": "Sean",
        "puuid": os.getenv("RIOT_ID_SEAN"),
        "discord_id": os.getenv("DISCORD_ID_SEAN")
    },
    "maxime": {
        "name": "Maxime",
        "puuid": os.getenv("RIOT_ID_MAXIME"),
        "discord_id": os.getenv("DISCORD_ID_MAXIME")
    },
    "thomas": {
        "name": "Thomas",
        "puuid": os.getenv("RIOT_ID_THOMAS"),
        "discord_id": os.getenv("DISCORD_ID_THOMAS")
    },
    "yannis": {
        "name": "Yannis",
        "puuid": os.getenv("RIOT_ID_YANNIS"),
        "discord_id": os.getenv("DISCORD_ID_YANNIS")
    }
}

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
