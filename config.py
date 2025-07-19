import os
import requests
from dotenv import load_dotenv

load_dotenv()
champions_data = requests.get("http://ddragon.leagueoflegends.com/cdn/13.14.1/data/en_US/champion.json").json()

DISCORD_CHANNEL = os.getenv("DISCORD_CHANNEL")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
API_KEY = os.getenv("RIOT_API_KEY")

PLAYERS = {
    "sean": {
        "puuid": os.getenv("RIOT_ID_SEAN"),
        "discord_id": os.getenv("DISCORD_ID_SEAN")
    },
    "maxime": {
        "puuid": os.getenv("RIOT_ID_MAXIME"),
        "discord_id": os.getenv("DISCORD_ID_MAXIME")
    },
    "thomas": {
        "puuid": os.getenv("RIOT_ID_THOMAS"),
        "discord_id": os.getenv("DISCORD_ID_THOMAS")
    },
    "yannis": {
        "puuid": os.getenv("RIOT_ID_YANNIS"),
        "discord_id": os.getenv("DISCORD_ID_YANNIS")
    }
}

CHAMPIONS = {}
for champ_name, champ_info in champions_data['data'].items():
    champ_id = int(champ_info['key'])
    tags = champ_info['tags']
    CHAMPIONS[champ_id] = {
        'name': champ_name
    }