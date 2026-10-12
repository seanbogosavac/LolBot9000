import asyncio
import logging
from discord.ext import tasks
from discord import TextChannel

from api import OngoingMatch, NoOngoingMatch, RiotAPIError
from config import PLAYERS, DISCORD_CHANNEL, CHAMPIONS
from .bot_instance import bot, riot_client
from .helpers import generate_match_info_response
from .types import PlayerInfos

logger = logging.getLogger(__name__)

# Tracks active matches: player puuid → gameId (0 = untracked game type)
ongoing_matches: dict[str, int] = {}

GAME_TYPE_MESSAGES = {
    400: lambda mention, champ: f"{mention} remet les crampons pour une nouvelle game avec **{champ}**",
    420: lambda mention, champ: f"Omg {mention} part en ranked avec **{champ}** ! Tout pour les e-points",
    430: lambda mention, _: f"{mention} a lancé une normale classique vanille #aucuneDraftAucunFun. Je vais même pas dire sur quel champ t'es pour la peine...",
    450: lambda mention, champ: f"{mention} veut chill et part en ARAM avec **{champ}**",
    900: lambda mention, _: f"{mention} joue au mode clash... (Qui fait ça?)",
    2400: lambda mention, champ: f"{mention} part en ARAM tout chaotique avec **{champ}**",
}


def generate_in_game_message(player_info: PlayerInfos, match_data: OngoingMatch) -> str:
    idx = match_data["players"].index(player_info["puuid"])
    champion = CHAMPIONS.get(match_data["champions"][idx], "un champion inconnu")
    mention = "OMG OMG @everyone Yannis" if player_info["name"] == "Yannis" else player_info["name"]
    game_type = match_data.get("gameType", "")
    builder = GAME_TYPE_MESSAGES.get(game_type)
    return builder(mention, champion) if builder else f"{mention} a lancé une game non détectée par le système (blip-bloup le robot à un problème)"


@tasks.loop(seconds=5)
async def check_players_in_game() -> None:
    """Check if players are currently in a game and notify the Discord channel."""
    channel: TextChannel = bot.get_channel(DISCORD_CHANNEL)
    if channel is None:
        try:
            channel = await bot.fetch_channel(DISCORD_CHANNEL)
        except Exception as e:
            logger.error("Failed to fetch channel %s: %s", DISCORD_CHANNEL, e)
            return

    for player_name, player_info in PLAYERS.items():
        puuid = player_info["puuid"]
        current_match: OngoingMatch | None = None

        try:
            current_match = riot_client.get_current_match(puuid)
        except NoOngoingMatch:
            logger.debug("No ongoing match for %s", player_info["name"])
        except RiotAPIError as e:
            logger.error("Riot API error for %s: %s", player_name, e)
        except Exception as e:
            logger.error("Error checking match for %s: %s", player_name, e, exc_info=True)

        if current_match:
            if puuid not in ongoing_matches:
                ongoing_matches[puuid] = current_match["gameId"] if current_match["gameType"] in GAME_TYPE_MESSAGES else 0
                await channel.send(generate_in_game_message(player_info, current_match))
                logger.info("Sent in-game notification for %s (gameId: %s)", player_info["name"], current_match["gameId"])
        elif puuid in ongoing_matches:
            match_id = ongoing_matches.pop(puuid)
            await asyncio.sleep(60)  # Wait for match data to be available

            if match_id != 0:
                try:
                    last_match_id = riot_client.get_last_match_id(puuid)
                    message, embed = generate_match_info_response(player_info, riot_client.get_match_data(last_match_id))
                    await channel.send(content=message, embed=embed)
                    logger.info("Sent post-match info for %s (lastMatchId: %s)", player_info["name"], last_match_id)
                except Exception as e:
                    logger.error("Error fetching post-match data for %s: %s", player_info["name"], e, exc_info=True)
