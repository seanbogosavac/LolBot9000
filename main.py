from riot_api.client import get_match_data
from config import API_KEY

info_maxime = get_match_data('EUW1_7465491302', API_KEY)
print(info_maxime)
