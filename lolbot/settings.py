"""Static configuration: environment variables, paths and constants.

Importing this module has no side effects beyond reading the environment. The objects that
need I/O (database, Riot client, champion list) are built in `lolbot.services`.
"""
import os
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent


def _channel_id() -> int | None:
    # discord.py caches channels by integer id: a string id never hits the cache, so the
    # polling loop would call the REST API on every tick.
    raw = os.getenv("DISCORD_CHANNEL", "").strip()
    return int(raw) if raw.isdigit() else None


DISCORD_TOKEN: str | None = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL: int | None = _channel_id()
RIOT_API_KEY: str | None = os.getenv("RIOT_API_KEY")

# Players live in SQLite, so the roster can change without redeploying the bot.
# Set PLAYERS_DB to move the file (docker-compose mounts a volume for it).
PLAYERS_DB_PATH: Path = Path(os.getenv("PLAYERS_DB", PROJECT_ROOT / "data" / "players.db"))

QUEUE_NAMES: dict[int, str] = {
    400: "Normal Draft",
    420: "Ranked Solo/Duo",
    440: "Ranked Flex",
    450: "ARAM",
    430: "Normal Blind Pick",
}
