import asyncio
import logging
from discord.ext import tasks
from discord import TextChannel

from lolbot import services
from lolbot.api import OngoingMatch, NoOngoingMatch, RiotAPIError
from lolbot.settings import DISCORD_CHANNEL
from lolbot.db import PlayerInfos

from .api_worker import run_blocking
from .bot_instance import bot
from .helpers import generate_group_match_info_response
from .roster import PlayerActionError, list_players

logger = logging.getLogger(__name__)

# Tracks active matches: player puuid → gameId (0 = untracked game type)
ongoing_matches: dict[str, int] = {}

# Players whose game has ended, waiting for the other tracked players of the same game
# (gameId → players) so that a single recap is posted per match.
pending_recaps: dict[int, list[PlayerInfos]] = {}

# Riot needs a moment to publish match data once a game ends.
POST_MATCH_SETTLE_SECONDS = 60

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
    champion = services.get_champions().get(match_data["champions"][idx], "un champion inconnu")
    mention = "OMG OMG @everyone Yannis" if player_info["name"] == "Yannis" else player_info["name"]
    game_type = match_data.get("gameType", "")
    builder = GAME_TYPE_MESSAGES.get(game_type)
    return builder(mention, champion) if builder else f"{mention} a lancé une game non détectée par le système (blip-bloup le robot à un problème)"


# Riot's app-level limit is 100 requests per 2 minutes. Each pass costs one request per
# player, so at 10s a 4-player roster uses 48 (and ~8 players would still fit). Polling
# faster than this throttles the bot, and a 429 stalls every player's notification because
# the loop is serial.
POLL_SECONDS = 10


@tasks.loop(seconds=POLL_SECONDS)
async def check_players_in_game() -> None:
    """Check if players are currently in a game and notify the Discord channel."""
    # The roster can change at any time, so it is re-read on every tick. A database
    # failure must not kill the task, otherwise monitoring stops until the next restart.
    try:
        roster = list_players()
    except PlayerActionError as e:
        logger.error("Could not read the player roster: %s", e)
        return

    channel: TextChannel = bot.get_channel(DISCORD_CHANNEL)
    if channel is None:
        try:
            channel = await bot.fetch_channel(DISCORD_CHANNEL)
        except Exception as e:
            logger.error("Failed to fetch channel %s: %s", DISCORD_CHANNEL, e)
            return

    # A player removed from the roster mid-game must not hold back the recap of their partners.
    roster_puuids = {p["puuid"] for p in roster}
    for stale in [puuid for puuid in ongoing_matches if puuid not in roster_puuids]:
        ongoing_matches.pop(stale)

    for player_info in roster:
        player_name = player_info["name"]
        puuid = player_info["puuid"]
        current_match: OngoingMatch | None = None

        try:
            current_match = await run_blocking(services.get_riot_client().get_current_match, puuid)
        except NoOngoingMatch:
            logger.debug("No ongoing match for %s", player_name)
        except RiotAPIError as e:
            logger.error("Riot API error for %s: %s", player_name, e)
            continue  # unknown state: do not mistake a failed call for the end of the game
        except Exception as e:
            logger.error("Error checking match for %s: %s", player_name, e, exc_info=True)
            continue

        if current_match:
            if puuid not in ongoing_matches:
                ongoing_matches[puuid] = current_match["gameId"] if current_match["gameType"] in GAME_TYPE_MESSAGES else 0
                await channel.send(generate_in_game_message(player_info, current_match))
                logger.info("Sent in-game notification for %s (gameId: %s)", player_name, current_match["gameId"])
        elif puuid in ongoing_matches:
            match_id = ongoing_matches.pop(puuid)
            if match_id != 0:
                pending_recaps.setdefault(match_id, []).append(player_info)

    # A match is recapped once none of the tracked players is still in it.
    still_running = set(ongoing_matches.values())
    finished = [game_id for game_id in pending_recaps if game_id not in still_running]
    if not finished:
        return

    await asyncio.sleep(POST_MATCH_SETTLE_SECONDS)  # Wait for match data to be available
    for game_id in finished:
        players = pending_recaps.pop(game_id)
        names = ", ".join(p["name"] for p in players)
        try:
            last_match_id = await run_blocking(services.get_riot_client().get_last_match_id, players[0]["puuid"])
            match_data = await run_blocking(services.get_riot_client().get_match_data, last_match_id)
            message, embed = generate_group_match_info_response(players, match_data)
            await channel.send(content=message, embed=embed)
            logger.info("Sent post-match info for %s (lastMatchId: %s)", names, last_match_id)
        except Exception as e:
            logger.error("Error fetching post-match data for %s: %s", names, e, exc_info=True)
