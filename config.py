import os
from dotenv import load_dotenv

load_dotenv()

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
