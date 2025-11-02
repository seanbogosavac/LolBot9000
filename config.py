import os
import requests
from typing import Dict

from bot.types import PlayerInfos

CHAMPIONS_DATA = requests.get("https://ddragon.leagueoflegends.com/cdn/13.14.1/data/en_US/champion.json").json()

DISCORD_CHANNEL = os.getenv("DISCORD_CHANNEL")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
API_KEY = os.getenv("RIOT_API_KEY")

PLAYERS: Dict[PlayerInfos] = {
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

QUEUE_NAMES = {
    400: "Normal Draft",
    420: "Ranked Solo/Duo",
    440: "Ranked Flex",
    450: "ARAM",
    430: "Normal Blind Pick",
}

CHAMPIONS = {}
for champ_name, champ_info in CHAMPIONS_DATA['data'].items():
    champ_id = int(champ_info['key'])
    tags = champ_info['tags']
    CHAMPIONS[champ_id] = {
        'name': champ_name
    }
