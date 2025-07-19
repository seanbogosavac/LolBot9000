from discord.ext import tasks
from riot_api.client import get_current_match
from config import PLAYERS, API_KEY, DISCORD_CHANNEL
from .bot_instance import bot

players_in_game = set()


@tasks.loop(seconds=60)
async def check_players_in_game():
    # Get the channel
    channel = bot.get_channel(DISCORD_CHANNEL)
    if channel is None:
        try:
            channel = await bot.fetch_channel(DISCORD_CHANNEL)
        except Exception as e:
            print(f"Failed to fetch channel: {e}")
            return

    for player_name, data in PLAYERS.items():
        puuid = data['puuid']

        try:
            current_match = get_current_match(puuid, API_KEY)
            
            if current_match:
                if puuid not in players_in_game:
                    players_in_game.add(puuid)

                    mention = f"<@{int(data['discord_id'])}>"
                    await channel.send(f"{mention} est en train de jouer une partie ! Glhf :video_game:")

            else:
                if puuid in players_in_game:
                    players_in_game.remove(puuid)

        except Exception as e:
            print(f"Error checking current match for {player_name}: {e}")
