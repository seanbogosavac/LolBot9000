from typing import Dict, Optional
from discord.ext import tasks
from discord import TextChannel, Embed

from .types import PlayerInfos
from .bot_instance import bot
from .functions.generate_match_info_response import generate_match_info_response
from api.types import Match, OngoingMatch
from config import PLAYERS, API_KEY, DISCORD_CHANNEL, CHAMPIONS
from api.client import get_current_match, get_match_data, NoOngoingMatch

# Map ongoing matches (player puuid to ongoing gameId)
ongoing_matches: Dict[str, int] = {}


def get_role(match_position: int) -> str:
    if match_position % 5 == 0:
        return "à la toplane"
    elif match_position % 5 == 1:
        return "en jungle"
    elif match_position % 5 == 2:
        return "au mid"
    elif match_position % 5 == 3:
        return "ADC"
    else:
        return "support (e-girl détéctée)"


def generate_in_game_message(player_info: PlayerInfos, match_data: OngoingMatch) -> str:
    player_position_in_match_data: int = match_data['players'].index(player_info['puuid'])
    champ_id: int = match_data['champions'][player_position_in_match_data]

    champion: str = CHAMPIONS.get(champ_id, "un champion inconnu")
    mention: str = f"<@{int(player_info['discord_id'])}>"
    role_message: str = get_role(player_position_in_match_data)

    game_type = match_data.get("gameType", "")
    if game_type == 400:
        return f"{mention} remet les crampons pour une nouvelle game avec **{champion}** {role_message}"
    elif game_type == 420:
        return f"Omg {mention} part en ranked sur avec **{champion}** {role_message} ! Tout pour les e-points"
    elif game_type == 430:
        return f"{mention} a lancé une normale classique vanille #aucuneDraftAucunFun. Je vais même pas dire sur quel champ t'es pour la peine..."
    elif game_type == 450:
        return f"{mention} veut chill et part en ARAM avec **{champion}**"
    elif game_type == 900:
        return f"{mention} joue au mode clash... (Qui fait ça?)"
    else:
        return f"{mention} a lancé une game non détectée par le système (blip-bloup le robot à un problème)"


@tasks.loop(seconds=5)
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
        player_id: str = player_info['puuid']
        current_match: Optional[OngoingMatch] = None

        try:
            current_match = get_current_match(player_id, API_KEY)
        except NoOngoingMatch:
            print(f"No ongoing match for {player_info['name']}")
        except Exception as e:
            print(f"Error checking current match for {player_name}: {e}")

        if current_match:
            # Match detected, adding it to the list of ongoing matches if not already
            if player_id not in ongoing_matches:
                ongoing_matches[player_id] = current_match['gameId']

                message: str = generate_in_game_message(player_info, current_match)
                await channel.send(message)
        else:
            # No match detected. If ongoing match ended, retrieving its data for display
            if player_id in ongoing_matches:
                ended_game_id: int = ongoing_matches.pop(player_id)

                try:
                    last_match_data: Match = get_match_data(ended_game_id, API_KEY)
                    # Generates response
                    message, embed = generate_match_info_response(player_info, last_match_data)
                    embed: Optional[Embed] # Type hints for embed
                    await channel.send(
                        content=message,
                        embed=embed
                    )
                except Exception as e:
                    print(f"Error getting info for match {ended_game_id}: {e}")
