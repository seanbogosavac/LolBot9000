from .bot_instance import bot
from .loops import check_players_in_game


@bot.event
async def on_ready():
    check_players_in_game.start()
    print("LolBot9000 up and running")
