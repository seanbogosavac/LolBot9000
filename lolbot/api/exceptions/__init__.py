class RiotAPIError(Exception):
    """Base exception for all Riot API errors."""


class AuthenticationError(RiotAPIError):
    """Raised when the API key is missing, invalid, or expired (401/403)."""


class RateLimitError(RiotAPIError):
    """Raised when rate limits are exceeded and retries exhausted (429)."""


class NotFoundError(RiotAPIError):
    """Raised when a requested resource is not found (HTTP 404)."""


class RiotServerError(RiotAPIError):
    """Raised when Riot API server returns a 5xx error."""


class NoOngoingMatch(RiotAPIError):
    """Raised when a player has no active match."""


__all__ = [
    "RiotAPIError",
    "AuthenticationError",
    "RateLimitError",
    "NotFoundError",
    "RiotServerError",
    "NoOngoingMatch",
]
