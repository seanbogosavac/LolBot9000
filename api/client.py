import logging
import time
from typing import Any
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

    Handles authentication via X-Riot-Token header, automatic retries on
    rate limits (429) and transient server errors (5xx), and exponential backoff.
    """

    def __init__(
        self,
        api_key: str,
        region: str = "euw1",
        routing: str = "europe",
        session: requests.Session | None = None,
        timeout: tuple[float, float] = (3.05, 10.0),
        retries: int = 3,
        backoff_factor: float = 1.0,
    ) -> None:
        self.region = region.lower()
        self.routing = routing.lower()
        self.timeout = timeout
        self.retries = retries
        self.backoff_factor = backoff_factor

        self._external_session = session is not None
        self.session = session or requests.Session()
        self.session.headers.update({"X-Riot-Token": api_key, "Accept": "application/json"})

    def close(self) -> None:
        """Close the underlying session if managed internally."""
        if not self._external_session:
            self.session.close()

    def __enter__(self) -> "RiotClient":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def _base_url(self, regional: bool) -> str:
        domain = self.routing if regional else self.region
        return f"https://{domain}.api.riotgames.com"

    def _request(self, method: str, endpoint: str, regional: bool = False, params: dict | None = None) -> Any:
        url = f"{self._base_url(regional)}{endpoint}"

        for attempt in range(self.retries):
            try:
                response = self.session.request(method, url, params=params, timeout=self.timeout)
            except requests.RequestException as e:
                logger.warning("Request error on attempt %d/%d for %s: %s", attempt + 1, self.retries, endpoint, e)
                if attempt < self.retries - 1:
                    time.sleep(self.backoff_factor * (2 ** attempt))
                    continue
                raise RiotAPIError(f"Connection error to Riot API for {endpoint}: {e}") from e

            # Response Handler
            match response.status_code:
                case 200:
                    try:
                        return response.json()
                    except Exception as e:
                        raise RiotAPIError(f"Failed to decode JSON from {endpoint}: {e}") from e
                case 404:
                    raise NotFoundError(f"Resource not found at {endpoint}")
                case 401 | 403:
                    raise AuthenticationError(f"Authentication failed (HTTP {response.status_code}). Check your API key.")
                case 429:
                    retry_after = int(response.headers.get("Retry-After", 1))
                    logger.warning("Rate limited on %s. Retrying in %ds (attempt %d/%d).", endpoint, retry_after, attempt + 1, self.retries)
                    if attempt < self.retries - 1:
                        time.sleep(retry_after)
                        continue
                    raise RateLimitError(f"Rate limit exceeded on {endpoint} after {self.retries} attempts.")
                case 500 | 502 | 503 | 504:
                    logger.warning("Server error (%d) on %s (attempt %d/%d).", response.status_code, endpoint, attempt + 1, self.retries)
                    if attempt < self.retries - 1:
                        time.sleep(self.backoff_factor * (2 ** attempt))
                        continue
                    raise RiotServerError(f"Riot server error ({response.status_code}) on {endpoint}.")
                case _:
                    raise RiotAPIError(f"Unexpected HTTP {response.status_code} for {endpoint}.")

        raise RiotAPIError(f"All {self.retries} attempts failed for {endpoint}.")

    ###
    # PUBLIC METHODS
    ###

    def get_player_info(self, puuid: str) -> PlayerStats:
        """Return the ranked stats (rank + winrate) for a player."""
        endpoint = f"/lol/league/v4/entries/by-puuid/{puuid}"
        try:
            data = self._request("GET", endpoint)
        except NotFoundError:
            return {"rank": "Unranked", "winrate": 0}

        if not data:
            return {"rank": "Unranked", "winrate": 0}

        entry = next((e for e in data if e.get("queueType") == "RANKED_SOLO_5x5"), data[0])
        tier = entry.get("tier", "Unranked")
        wins, losses = entry.get("wins", 0), entry.get("losses", 0)
        total = wins + losses
        return {
            "rank": f"{tier} {entry.get('rank', '')} {entry.get('leaguePoints', 0)} LP".strip() if tier != "Unranked" else "Unranked",
            "winrate": round(wins / total * 100) if total else 0,
        }

    def get_current_match(self, puuid: str) -> OngoingMatch:
        """Return the active match for a player, or raise NoOngoingMatch."""
        endpoint = f"/lol/spectator/v5/active-games/by-summoner/{puuid}"
        try:
            data = self._request("GET", endpoint)
        except NotFoundError:
            raise NoOngoingMatch("No ongoing match for this player.")

        if not isinstance(data, dict):
            raise NoOngoingMatch("No ongoing match for this player.")

        participants = data.get("participants", [])
        return {
            "gameId": data.get("gameId", 0),
            "gameType": data.get("gameQueueConfigId", 0),
            "players": [p.get("puuid", "") for p in participants],
            "champions": [p.get("championId", 0) for p in participants],
        }

    def get_last_match_id(self, puuid: str, start: int = 0, count: int = 1) -> str:
        """Return the most recent match ID for a player."""
        data = self._request("GET", f"/lol/match/v5/matches/by-puuid/{puuid}/ids", regional=True, params={"start": start, "count": count})
        if not data:
            raise RiotAPIError("No match history found for this player.")
        return str(data[0])

    def get_match_data(self, match_id: str | int) -> Match:
        """Return detailed data for a specific match."""
        data = self._request("GET", f"/lol/match/v5/matches/{match_id}", regional=True)
        if not isinstance(data, dict) or "info" not in data:
            raise RiotAPIError(f"Failed to retrieve match data for match {match_id}.")

        info = data["info"]
        minutes, seconds = divmod(int(info.get("gameDuration", 0)), 60)

        participants: list[Participant] = [
            {
                "puuid": p.get("puuid", "Unknown"),
                "champion": p.get("championName", "Unknown"),
                "kills": p.get("kills", 0),
                "deaths": p.get("deaths", 0),
                "assists": p.get("assists", 0),
                "win": p.get("win", False),
                "cs": p.get("totalMinionsKilled", 0) + p.get("neutralMinionsKilled", 0),
                "gold": p.get("goldEarned", 0),
            }
            for p in info.get("participants", [])
        ]

        return {
            "gameType": info.get("queueId", 0),
            "duration": f"{minutes}:{seconds:02d}",
            "participants": participants,
        }
