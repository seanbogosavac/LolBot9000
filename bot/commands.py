import logging
from typing import Optional

from api import PlayerStats, RiotAPIError
from config import PLAYERS
from .bot_instance import bot, riot_client
from .exceptions.NoPlayerMentioned import NoPlayerMentioned
from .exceptions.UnknownPlayer import UnknownPlayer
from .functions.find_targeted_player import find_targeted_player
from .functions.generate_match_info_response import generate_match_info_response
from .types import PlayerInfos

logger = logging.getLogger(__name__)


@bot.command()
async def lol(ctx, target=None):
    logger.info("Command !lol invoked by %s (target: %s)", ctx.author, target)
    try:
        player_name: str = await find_targeted_player(ctx, target)
        player: PlayerInfos = PLAYERS[player_name]

        mention: str = f"<@{int(player['discord_id'])}>"
        try:
            # Api call
            info: PlayerStats = riot_client.get_player_info(player['puuid'])
            rank: str = info.get("rank", "Unranked")
            winrate: int = info.get("winrate", 0)

            if rank == "Unranked":
                await ctx.send(f"T'as pas de rang **{mention}**, va faire tes ranked là hopopop")
                return

            # Generate a message and send it
            message = f"**{mention}** est **{rank}** avec un winrate de **{winrate}%**, {'énorme sexe' if winrate > 50 else 'le gros nullos'}\n"
            await ctx.send(message)
        except RiotAPIError as e:
            logger.error("Riot API error fetching info for %s: %s", target, e)
            await ctx.send("Impossible de récupérer les informations depuis l'API Riot.")
        except Exception as e:
            logger.error("Error fetching info for %s: %s", target, e, exc_info=True)
            await ctx.send("G beugé chef")

    except NoPlayerMentioned:
        await ctx.send("Oh tu veux les infos de qui ? Dis les termes là !")
    except UnknownPlayer:
        await ctx.send("C'est qui frère ?")


@bot.command()
async def leaderboard(ctx):
    logger.info("Command !leaderboard invoked by %s", ctx.author)
    stats = []

    for key, player in PLAYERS.items():
        try:
            info = riot_client.get_player_info(player['puuid'])
            stats.append({
                "key": key,
                "name": player['name'],
                "rank": info.get("rank", "Unranked"),
                "winrate": info.get("winrate", 0)
            })
        except Exception as e:
            logger.warning("Failed to fetch stats for %s in leaderboard: %s", player['name'], e)
            stats.append({
                "key": key,
                "name": player['name'],
                "rank": "Unranked",
                "winrate": 0
            })

    if not stats:
        await ctx.send("Can't show leaderboard: no player data to display.")
        return

    # Define order of tiers and divisions
    tier_order = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", "EMERALD", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"]
    division_order = ["IV", "III", "II", "I"]

    def rank_key(rank):
        rank = rank.upper()
        if rank == "UNRANKED":
            return -1, -1
        parts = rank.split()
        tier = parts[0]
        division = parts[1] if len(parts) > 1 else ""
        tier_index = tier_order.index(tier) if tier in tier_order else -1
        div_index = division_order.index(division) if division in division_order else -1
        return tier_index, div_index

    # Sort players by rank
    stats.sort(key=lambda x: rank_key(x["rank"]), reverse=True)
    logger.debug("Leaderboard stats: %s", stats)

    # Build message
    best_player: PlayerInfos = PLAYERS[stats[0]["key"]]
    best_player_mention: str = f"<@{int(best_player['discord_id'])}>"

    message = (
        f"Ok tout le monde gobe le paf de {best_player_mention}, le **GOAT** du discord\n\n"
        f"🏆 **Classement des Stonkers** 🏆\n"
        f"``` Nom      | Rang               | Winrate\n"
        f"------------------------------------------\n"
    )

    for i, player in enumerate(stats, start=1):
        message += f" {player['name']:<7}  | {player['rank']:<18} | {player['winrate']}%\n"
    message += "```"

    try:
        await ctx.send(message)
    except Exception as e:
        logger.error("Error sending leaderboard: %s", e, exc_info=True)
        await ctx.send("G beugé chef")


@bot.command()
async def lastgame(ctx, target=None):
    logger.info("Command !lastgame invoked by %s (target: %s)", ctx.author, target)
    try:
        player_name: str = await find_targeted_player(ctx, target)
        player_info: PlayerInfos = PLAYERS[player_name]
        try:
            # Fetch data of the last match played
            last_match_id: str = riot_client.get_last_match_id(player_info['puuid'])
            last_match_data = riot_client.get_match_data(last_match_id)

            # Generates response
            message, embed = generate_match_info_response(player_info, last_match_data)
            await ctx.send(
                content=message,
                embed=embed
            )
        except RiotAPIError as e:
            logger.error("Riot API error fetching last match for %s: %s", target, e)
            await ctx.send("Impossible de récupérer les données du dernier match.")
        except Exception as e:
            logger.error("Error fetching info for %s: %s", target, e, exc_info=True)
            await ctx.send("G beugé chef")

    except NoPlayerMentioned:
        await ctx.send("Oh tu veux les infos de qui ? Dis les termes là !")
    except UnknownPlayer:
        await ctx.send("C'est qui frère ?")
