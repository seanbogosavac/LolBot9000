"""Champion list from Riot's Data Dragon static data."""
import logging

import requests

logger = logging.getLogger(__name__)

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


def champions_by_id() -> dict[int, str]:
    """Map champion ids to their names, as published for the latest patch."""
    return {int(info["key"]): name for name, info in fetch_champions_data()["data"].items()}
