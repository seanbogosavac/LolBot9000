from typing import Dict, Optional
from discord.ext import tasks
from discord import TextChannel, Embed

from .types import PlayerStats
from .bot_instance import bot
from .functions.generate_match_info_response import generate_match_info_response
from api.types import Match, OngoingMatch
from config import PLAYERS, API_KEY, DISCORD_CHANNEL, CHAMPIONS
from api.client import get_current_match, get_match_data, NoOngoingMatch

# Map ongoing matches (player puuid to ongoing gameId)
ongoing_matches: Dict[str, str] = {}


def generate_in_game_message(player_info: PlayerStats, match_data: OngoingMatch) -> str:
    mention: str = ""
    champion: str = "un champion inconnu"
    puuid: Optional[str] = None

    if 'players' in match_data and 'champions' in match_data:
        mention = f"<@{int(player_info['discord_id'])}>"
        if puuid in match_data['players']:
            champ_id = match_data['champions'][match_data['players'].index(puuid)]
            champion = CHAMPIONS.get(champ_id, "un champion inconnu")

    game_type = match_data.get("gameType", "")
    if game_type == '400':
        return f"{mention} remet les crampons pour une nouvelle game avec **{champion}**"
    elif game_type == '420':
        return f"Omg {mention} part en ranked sur avec **{champion}** ! Tout pour les e-points"
    elif game_type == '430':
        return f"{mention} a lancé une normale classique vanille #aucuneDraftAucunFun. Je vais même pas dire sur quel champ t'es pour la peine..."
    elif game_type == '450':
        return f"{mention} veut chill et part en ARAM avec **{champion}**"
    elif game_type == '900':
        return f"{mention} joue au mode clash... (Qui fait ça?)"
    else:
        return f"{mention} a lancé une game non détectée par le système (blip-bloup le robot à un problème"


@tasks.loop(seconds=15)
async def check_players_in_game() -> None:
    """Check if players are currently in a game and notify Discord channel."""
    channel: Optional[TextChannel] = bot.get_channel(DISCORD_CHANNEL)
    if channel is None:
        try:
            channel = await bot.fetch_channel(DISCORD_CHANNEL)
        except Exception as e:
            print(f"Failed to fetch channel: {e}")
            return

    for player_name, player_info in PLAYERS.items():
        puuid: str = player_info['puuid']

        try:
            current_match: OngoingMatch = get_current_match(puuid, API_KEY)

            if current_match:
                if puuid not in ongoing_matches:
                    ongoing_matches[puuid] = current_match['gameId']  # type: ignore

                    message: str = generate_in_game_message(player_info, current_match)
                    await channel.send(message)

            else:
                if puuid in ongoing_matches:
                    # Remove ended match from the list and fetch its data
                    ended_game_id: str = ongoing_matches.pop(puuid)
                    last_match_data: Match = get_match_data(ended_game_id, API_KEY)

                    # Generates response
                    message, embed = generate_match_info_response(player_info, last_match_data)
                    # Type hints for embed
                    embed: Optional[Embed]
                    await channel.send(
                        content=message,
                        embed=embed
                    )
        except NoOngoingMatch:
            print(f"No ongoing match for {player_info['name']}")
        except Exception as e:
            print(f"Error checking current match for {player_name}: {e}")
