import os
from dotenv import load_dotenv
from src.riot_api import get_player_info

load_dotenv()
API_KEY = os.getenv("RIOT_API_KEY")
REGION = os.getenv("REGION")
PUUID = {"sean": os.getenv("ID_SEAN"),
         "maxime": os.getenv("ID_MAXIME"),
         "thomas": os.getenv("ID_THOMAS"),
         "yannis": os.getenv("ID_YANNIS")}

info_maxime = get_player_info(PUUID["maxime"], API_KEY)
print(info_maxime)
