import logging
from time import sleep
from typing import Dict, Optional
from discord.ext import tasks
from discord import TextChannel

from .types import PlayerInfos
from .bot_instance import bot, riot_client
from .functions.generate_match_info_response import generate_match_info_response
from api import OngoingMatch, NoOngoingMatch, RiotAPIError
from config import PLAYERS, DISCORD_CHANNEL, CHAMPIONS

logger = logging.getLogger(__name__)

# Map ongoing matches (player puuid to ongoing gameId)
ongoing_matches: Dict[str, int] = {}


def yannis_le_ghosteur(player_info: PlayerInfos) -> str:
    if player_info['name'] == "Yannis":
        return "OMG OMG @everyone Yannis"
    else:
        return f"{player_info['name']}"


def generate_in_game_message(player_info: PlayerInfos, match_data: OngoingMatch) -> str:
    player_position_in_match_data: int = match_data['players'].index(player_info['puuid'])
    champ_id: int = match_data['champions'][player_position_in_match_data]

    champion: str = CHAMPIONS.get(champ_id, "un champion inconnu")
    mention: str = yannis_le_ghosteur(player_info)

    game_type = match_data.get("gameType", "")
    if game_type == 400:
        return f"{mention} remet les crampons pour une nouvelle game avec **{champion}**"
    elif game_type == 420:
        return f"Omg {mention} part en ranked avec **{champion}** ! Tout pour les e-points"
    elif game_type == 430:
        return f"{mention} a lancé une normale classique vanille #aucuneDraftAucunFun. Je vais même pas dire sur quel champ t'es pour la peine..."
    elif game_type == 450:
        return f"{mention} veut chill et part en ARAM avec **{champion}**"
    elif game_type == 900:
        return f"{mention} joue au mode clash... (Qui fait ça?)"
    elif game_type == 2400:
        return f"{mention} part en ARAM tout chaotique avec **{champion}**"
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
            logger.error("Failed to fetch channel %s: %s", DISCORD_CHANNEL, e)
            return

    for player_name, player_info in PLAYERS.items():
        player_id: str = player_info['puuid']
        current_match: Optional[OngoingMatch] = None

        try:
            current_match = riot_client.get_current_match(player_id)
        except NoOngoingMatch:
            logger.debug("No ongoing match for %s", player_info['name'])
        except RiotAPIError as e:
            logger.error("Riot API error checking current match for %s: %s", player_name, e)
        except Exception as e:
            logger.error("Error checking current match for %s: %s", player_name, e, exc_info=True)

        if current_match:
            # Match detected, adding it to the list of ongoing matches if not already
            if player_id not in ongoing_matches:
                # If the match type is special, insert a 0 to prevent from trying to display post-match info
                if current_match["gameType"] in {400, 420, 430, 450, 2400}:
                    ongoing_matches[player_id] = current_match['gameId']
                else:
                    ongoing_matches[player_id] = 0

                message: str = generate_in_game_message(player_info, current_match)
                await channel.send(message)
                logger.info("Sent in-game notification for %s (gameId: %s)", player_info['name'], current_match['gameId'])
        else:
            # No match detected. If ongoing match ended, retrieving its data for display
            if player_id in ongoing_matches:
                match_id: int = ongoing_matches.pop(player_id)
                sleep(60)

                # Check if the match data can be retrieved
                if match_id != 0:
                    try:
                        # Fetch data of the last match played
                        last_match_id: str = riot_client.get_last_match_id(player_info['puuid'])
                        last_match_data = riot_client.get_match_data(last_match_id)

                        # Generates response
                        message, embed = generate_match_info_response(player_info, last_match_data)
                        await channel.send(
                            content=message,
                            embed=embed
                        )
                        logger.info("Sent post-match info for %s (lastMatchId: %s)", player_info['name'], last_match_id)
                    except Exception as e:
                        logger.error("Error fetching info for the ended match of %s: %s", player_info['name'], e, exc_info=True)
