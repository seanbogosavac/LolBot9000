import logging
import time
from typing import Optional, Dict, Union, Any, List
import requests

from api.exceptions import (
    RiotAPIError,
    NoOngoingMatch,
    AuthenticationError,
    RateLimitError,
    NotFoundError,
    RiotServerError,
)
from api.types import PlayerStats, Participant, Match, OngoingMatch

logger = logging.getLogger(__name__)


class RiotClient:
    """Client for interacting with the Riot Games API.

    Handles connection pooling, authentication via X-Riot-Token header,
    automatic retries on rate limits (429) and transient server errors (5xx),
    and exponential backoff.
    """

    def __init__(
        self,
        api_key: str,
        region: str = "euw1",
        routing: str = "europe",
        session: Optional[requests.Session] = None,
        timeout: tuple[float, float] = (3.05, 10.0),
        retries: int = 3,
        backoff_factor: float = 1.0,
    ) -> None:
        self.api_key = api_key
        self.region = region.lower()
        self.routing = routing.lower()
        self.timeout = timeout
        self.retries = retries
        self.backoff_factor = backoff_factor

        self._external_session = session is not None
        self.session = session or requests.Session()
        self.session.headers.update({
            "X-Riot-Token": self.api_key,
            "Accept": "application/json",
        })

    def close(self) -> None:
        """Close the underlying session if managed internally."""
        if not self._external_session:
            self.session.close()

    def __enter__(self) -> "RiotClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def _get_base_url(self, is_regional: bool) -> str:
        domain = self.routing if is_regional else self.region
        return f"https://{domain}.api.riotgames.com"

    def _request(
        self,
        method: str,
        endpoint: str,
        is_regional: bool = False,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        url = f"{self._get_base_url(is_regional)}{endpoint}"

        for attempt in range(self.retries):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    timeout=self.timeout,
                )
            except requests.RequestException as e:
                logger.warning(
                    "Request error on attempt %d/%d for %s: %s",
                    attempt + 1, self.retries, endpoint, e
                )
                if attempt == self.retries - 1:
                    raise RiotAPIError(f"Connection error to Riot API for {endpoint}: {e}") from e
                time.sleep(self.backoff_factor * (2 ** attempt))
                continue

            if response.status_code == 200:
                try:
                    return response.json()
                except Exception as e:
                    raise RiotAPIError(f"Failed to decode JSON from {endpoint}: {e}") from e

            elif response.status_code == 404:
                raise NotFoundError(f"Resource not found at {endpoint} (HTTP 404)")

            elif response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 1))
                logger.warning(
                    "Rate limited (429) on %s. Retrying after %d seconds (attempt %d/%d)...",
                    endpoint, retry_after, attempt + 1, self.retries
                )
                if attempt == self.retries - 1:
                    raise RateLimitError(f"Rate limit exceeded on {endpoint} after {self.retries} attempts.")
                time.sleep(retry_after)
                continue

            elif response.status_code in {401, 403}:
                raise AuthenticationError(
                    f"Riot API authentication failed with HTTP {response.status_code}. "
                    "Ensure your API key is valid and not expired."
                )

            elif response.status_code in {500, 502, 503, 504}:
                logger.warning(
                    "Riot server error (%d) on %s (attempt %d/%d).",
                    response.status_code, endpoint, attempt + 1, self.retries
                )
                if attempt == self.retries - 1:
                    raise RiotServerError(
                        f"Riot server error ({response.status_code}) on {endpoint} after {self.retries} attempts."
                    )
                time.sleep(self.backoff_factor * (2 ** attempt))
                continue

            else:
                raise RiotAPIError(
                    f"Request to {endpoint} failed with HTTP status code {response.status_code}"
                )

        raise RiotAPIError(f"All {self.retries} attempts failed for {endpoint}")

    def get_player_info(self, puuid: str) -> PlayerStats:
        """Gather the League of Legends ranked stats of the selected player."""
        endpoint = f"/lol/league/v4/entries/by-puuid/{puuid}"
        try:
            data = self._request("GET", endpoint, is_regional=False)
        except NotFoundError:
            return {"rank": "Unranked", "winrate": 0}

        if not data or not isinstance(data, list) or len(data) == 0:
            return {"rank": "Unranked", "winrate": 0}

        player_info = next(
            (entry for entry in data if entry.get("queueType") == "RANKED_SOLO_5x5"),
            data[0]
        )
        tier = player_info.get("tier", "Unranked")
        rank = player_info.get("rank", "")
        lp = player_info.get("leaguePoints", 0)
        wins = player_info.get("wins", 0)
        losses = player_info.get("losses", 0)
        total_games = wins + losses
        winrate = round((wins / total_games) * 100) if total_games > 0 else 0

        formatted_rank = f"{tier} {rank} {lp} LP".strip() if tier != "Unranked" else "Unranked"
        return {
            "rank": formatted_rank,
            "winrate": winrate,
        }

    def get_current_match(self, puuid: str) -> OngoingMatch:
        """Retrieve the current active match played by the selected player."""
        endpoint = f"/lol/spectator/v5/active-games/by-summoner/{puuid}"
        try:
            data = self._request("GET", endpoint, is_regional=False)
        except NotFoundError:
            raise NoOngoingMatch("No ongoing match for this player.")

        if not data or not isinstance(data, dict):
            raise NoOngoingMatch("No ongoing match for this player.")

        participants = data.get("participants", [])
        return {
            "gameId": data.get("gameId", 0),
            "gameType": data.get("gameQueueConfigId", 0),
            "players": [p.get("puuid", "") for p in participants],
            "champions": [p.get("championId", 0) for p in participants],
        }

    def get_last_match_id(self, puuid: str, start: int = 0, count: int = 1) -> str:
        """Retrieve the most recent match ID for the selected player."""
        endpoint = f"/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params = {"start": start, "count": count}
        data = self._request("GET", endpoint, is_regional=True, params=params)
        if not data or not isinstance(data, list) or len(data) == 0:
            raise RiotAPIError("No match history found for this player.")
        return str(data[0])

    def get_match_data(self, match_id: Union[str, int]) -> Match:
        """Retrieve detailed data for a specific match."""
        endpoint = f"/lol/match/v5/matches/{match_id}"
        data = self._request("GET", endpoint, is_regional=True)
        if not data or not isinstance(data, dict) or "info" not in data:
            raise RiotAPIError(f"Failed to retrieve match data for match {match_id}.")

        info = data["info"]
        duration_seconds = info.get("gameDuration", 0)
        minutes, seconds = divmod(int(duration_seconds), 60)

        participants: List[Participant] = []
        for p in info.get("participants", []):
            cs = p.get("totalMinionsKilled", 0) + p.get("neutralMinionsKilled", 0)
            participants.append({
                "puuid": p.get("puuid", "Unknown"),
                "champion": p.get("championName", "Unknown"),
                "kills": p.get("kills", 0),
                "deaths": p.get("deaths", 0),
                "assists": p.get("assists", 0),
                "win": p.get("win", False),
                "cs": cs,
                "gold": p.get("goldEarned", 0),
            })

        return {
            "gameType": info.get("queueId", 0),
            "duration": f"{minutes}:{seconds:02d}",
            "participants": participants,
        }


# ============================================================================
# Backward-compatibility layer & module-level convenience functions
# ============================================================================

_cached_clients: Dict[tuple[str, str, str], RiotClient] = {}


def _get_shared_client(api_key: str, region: str = "euw1", routing: str = "europe") -> RiotClient:
    key = (api_key, region, routing)
    if key not in _cached_clients:
        _cached_clients[key] = RiotClient(api_key=api_key, region=region, routing=routing)
    return _cached_clients[key]


def get_player_info(puuid: str, api_key: str, region: str = "euw1") -> PlayerStats:
    """Gather the LOL info of the selected player (convenience wrapper)."""
    client = _get_shared_client(api_key, region=region)
    return client.get_player_info(puuid)


def get_current_match(puuid: str, api_key: str, region: str = "euw1") -> OngoingMatch:
    """Retrieve the current match played by the selected player (convenience wrapper)."""
    client = _get_shared_client(api_key, region=region)
    return client.get_current_match(puuid)


def get_last_match_id(puuid: str, api_key: str, routing: str = "europe") -> str:
    """Retrieve the most recent match played by the selected player (convenience wrapper)."""
    client = _get_shared_client(api_key, routing=routing)
    return client.get_last_match_id(puuid)


def get_match_data(match_id: Union[str, int], api_key: str, routing: str = "europe") -> Match:
    """Retrieve all data about the selected match (convenience wrapper)."""
    client = _get_shared_client(api_key, routing=routing)
    return client.get_match_data(match_id)
