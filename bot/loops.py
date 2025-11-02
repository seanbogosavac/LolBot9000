from discord.ext import tasks
from config import PLAYERS, API_KEY, DISCORD_CHANNEL
from .bot_instance import bot
from .functions.generate_in_game_message import generate_in_game_message
from .functions.generate_match_info_response import generate_match_info_response
from api.client import get_current_match, get_match_data

ongoing_matches = {}


@tasks.loop(seconds=15)
async def check_players_in_game():
    # Get the channel
    channel = bot.get_channel(DISCORD_CHANNEL)
    if channel is None:
        try:
            channel = await bot.fetch_channel(DISCORD_CHANNEL)
        except Exception as e:
            print(f"Failed to fetch channel: {e}")
            return

    for player_name, player_info in PLAYERS.items():
        puuid = player_info['puuid']

        try:
            current_match = get_current_match(puuid, API_KEY)
            
            if current_match:
                if puuid not in ongoing_matches:
                    ongoing_matches[puuid] = current_match['gameId']

                    message = generate_in_game_message(player_info, current_match)
                    await channel.send(message)

            else:
                if puuid in ongoing_matches:
                    # Remove ended match from the list and fetch its data
                    ended_game_id = ongoing_matches.pop(puuid)
                    last_match_data = get_match_data(ended_game_id, API_KEY)
                    
                    # Generates response
                    message, embed = generate_match_info_response(player_info, last_match_data)
                    await channel.send(
                        content=message,
                        embed=embed
                    )
        except Exception as e:
            print(f"Error checking current match for {player_name}: {e}")
