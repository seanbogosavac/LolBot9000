from riot_api.client import get_player_info, get_current_match, get_last_match
from config import API_KEY, PLAYERS

info_maxime = get_current_match(PLAYERS["sean"]['puuid'], API_KEY)
print(info_maxime)
info_maxime = get_last_match(PLAYERS["sean"]['puuid'], API_KEY)
print(info_maxime)
