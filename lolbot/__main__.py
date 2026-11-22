"""Start the bot: `python -m lolbot`."""
import argparse
import logging

from lolbot import services, settings
from lolbot.bot import commands  # noqa: F401  (registers the discord commands on the bot)
from lolbot.bot.bot_runner import bot
from lolbot.logging_config import setup_logging
from lolbot.version import version_string

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="lolbot", description="Discord bot that announces League of Legends games")
    parser.add_argument("--version", action="version", version=f"%(prog)s {version_string()}")
    parser.parse_args(argv)

    setup_logging()

    if settings.DISCORD_CHANNEL is None:
        logger.error("DISCORD_CHANNEL is missing or is not a numeric channel id")

    players = services.get_players()  # fail fast if the database cannot be opened
    services.get_champions()

    logger.info("Starting LolBot9000 %s...", version_string())
    try:
        bot.run(settings.DISCORD_TOKEN, log_handler=None)
    finally:
        players.close()


if __name__ == "__main__":
    main()
