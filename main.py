import logging
from logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

import bot.commands
from bot.bot_runner import bot
from config import DISCORD_TOKEN

logger.info("Starting LolBot9000...")
bot.run(DISCORD_TOKEN, log_handler=None)
