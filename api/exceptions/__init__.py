from .RiotAPIError import RiotAPIError
from .NoOngoingMatch import NoOngoingMatch


class AuthenticationError(RiotAPIError):
    """Raised when the API key is missing, invalid, or expired (401/403)."""
    pass


class RateLimitError(RiotAPIError):
    """Raised when rate limits are exceeded and retries exhausted (429)."""
    pass


class NotFoundError(RiotAPIError):
    """Raised when a requested resource is not found (HTTP 404)."""
    pass


class RiotServerError(RiotAPIError):
    """Raised when Riot API server returns a 5xx error."""
    pass


__all__ = [
    "RiotAPIError",
    "NoOngoingMatch",
    "AuthenticationError",
    "RateLimitError",
    "NotFoundError",
    "RiotServerError",
]

