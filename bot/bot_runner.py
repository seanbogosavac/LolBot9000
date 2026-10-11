import logging

from .bot_instance import bot
from .loops import check_players_in_game

logger = logging.getLogger(__name__)


@bot.event
async def on_ready():
    check_players_in_game.start()
    logger.info("LolBot9000 up and running (logged in as %s)", bot.user)
