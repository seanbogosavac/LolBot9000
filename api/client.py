import logging
from typing import Optional, Dict, Union, Any
import requests
from time import sleep

from api.exceptions.RiotAPIError import RiotAPIError
from api.exceptions.NoOngoingMatch import NoOngoingMatch
from api.types import *

logger = logging.getLogger(__name__)

session = requests.Session()  # Reuse TCP connection for multiple requests


def riot_get(url: str, retries: int = 3, backoff: float = 1.0) -> Optional[Union[Dict[str, Any], List[Any]]]:
    """Generic GET request handler with retries and error handling."""
    for attempt in range(retries):
        try:
            response = session.get(url, timeout=5)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
            elif response.status_code == 429:  # rate limited
                retry_after = int(response.headers.get("Retry-After", 1))
                logger.warning("Rate limited (429) on %s. Retrying after %d seconds...", url, retry_after)
                sleep(retry_after)
            else:
                raise RiotAPIError(f"Request failed with status code {response.status_code}: {url}")
        except requests.RequestException as e:
            logger.error("Request error on attempt %d/%d for %s: %s", attempt + 1, retries, url, e)
        sleep(backoff)
    logger.error("All %d retries failed for URL: %s", retries, url)
    return None


def get_player_info(puuid: str, api_key: str) -> PlayerStats:
    """Gather the LOL info of the selected player."""
    url = f"https://euw1.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}?api_key={api_key}"
    data = riot_get(url)
    
    # If the request completely failed (e.g. 404 or connection error)
    if data is None:
        raise RiotAPIError("Failed to retrieve player info from Riot API.")

    # If the player has no ranked entries (unranked)
    if len(data) == 0:
        return {
            "rank": "Unranked",
            "winrate": 0
        }

    # Find Solo/Duo entry if present, otherwise default to first entry
    player_info = next((entry for entry in data if entry.get("queueType") == "RANKED_SOLO_5x5"), data[0])
    total_games = player_info['wins'] + player_info['losses']
    winrate = int(player_info['wins'] / total_games * 100) if total_games > 0 else 0

    return {
        "rank": f"{player_info['tier']} {player_info['rank']} {player_info['leaguePoints']} LP",
        "winrate": winrate
    }


def get_current_match(puuid: str, api_key: str) -> OngoingMatch:
    """Retrieve the current match played by the selected player."""
    url = f"https://euw1.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}?api_key={api_key}"
    data = riot_get(url)
    if data is None:
        raise NoOngoingMatch("No ongoing match for this player.")

    return {
        "gameId": data['gameId'],
        "gameType": data['gameQueueConfigId'],
        "players": [p['puuid'] for p in data['participants']],
        "champions": [p['championId'] for p in data['participants']]
    }


def get_last_match_id(puuid: str, api_key: str) -> int:
    """Retrieve the most recent match played by the selected player."""
    url = f"https://europe.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=1&api_key={api_key}"
    data = riot_get(url)
    if not data:
        raise RiotAPIError("No match history found for this player.")
    return data[0]


def get_match_data(match_id: int, api_key: str) -> Match:
    """Retrieve all data about the selected match."""
    url = f"https://europe.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={api_key}"
    data = riot_get(url)
    if not data:
        raise RiotAPIError("Failed to retrieve match data.")

    info = data['info']
    duration_seconds = info['gameDuration']
    minutes, seconds = divmod(duration_seconds, 60)

    participants: List[Participant] = []
    for p in info['participants']:
        participants.append({
            "puuid": p.get('puuid', 'Unknown'),
            "champion": p.get('championName', 'Unknown'),
            "kills": p.get('kills', 0),
            "deaths": p.get('deaths', 0),
            "assists": p.get('assists', 0),
            "win": p.get('win', False),
            "cs": p.get('totalMinionsKilled', 0),
            "gold": p.get('goldEarned', 0)
        })

    return {
        "gameType": info['queueId'],
        "duration": f"{minutes}:{seconds:02d}",
        "participants": participants
    }
