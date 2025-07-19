import os
from dotenv import load_dotenv
from src.riot_api import get_player_info, get_current_match, get_last_match

load_dotenv()
API_KEY = os.getenv("RIOT_API_KEY")
PUUID = {"sean": os.getenv("ID_SEAN"),
         "maxime": os.getenv("ID_MAXIME"),
         "thomas": os.getenv("ID_THOMAS"),
         "yannis": os.getenv("ID_YANNIS")}

info_maxime = get_current_match(PUUID["sean"], API_KEY)
print(info_maxime)
info_maxime = get_last_match(PUUID["sean"], API_KEY)
print(info_maxime)
