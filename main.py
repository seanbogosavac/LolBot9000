import logging
from logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

import bot.commands  # noqa: F401  (registers the discord commands on the bot)
from bot.bot_runner import bot
from config import DISCORD_TOKEN, players

logger.info("Starting LolBot9000...")
try:
    bot.run(DISCORD_TOKEN, log_handler=None)
finally:
    players.close()
