class NoPlayerMentioned(Exception):
    """Raised when a command is invoked without specifying a target player."""


class UnknownPlayer(Exception):
    """Raised when the specified player is not in the known players list."""

