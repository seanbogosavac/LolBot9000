import logging

from api import PlayerStats, RiotAPIError
from config import PLAYERS
from .bot_instance import bot, riot_client
from .exceptions import NoPlayerMentioned, UnknownPlayer
from .helpers import generate_match_info_response
from .types import PlayerInfos

logger = logging.getLogger(__name__)


async def find_targeted_player(ctx, target) -> str:
    """Resolve a command target (mention or name string) to a known player key."""
    if target is None:
        raise NoPlayerMentioned

    if ctx.message.mentions:
        discord_id = str(ctx.message.mentions[0].id)
        player_name = next((name for name, data in PLAYERS.items() if data["discord_id"] == discord_id), "")
    else:
        player_name = target.lower()

    if player_name not in PLAYERS:
        raise UnknownPlayer
    return player_name


@bot.command()
async def lol(ctx, target=None):
    logger.info("Command !lol invoked by %s (target: %s)", ctx.author, target)
    try:
        player_name: str = await find_targeted_player(ctx, target)
        player: PlayerInfos = PLAYERS[player_name]
        mention = f"<@{int(player['discord_id'])}>"

        try:
            info: PlayerStats = riot_client.get_player_info(player["puuid"])
            rank, winrate = info.get("rank", "Unranked"), info.get("winrate", 0)

            if rank == "Unranked":
                await ctx.send(f"T'as pas de rang **{mention}**, va faire tes ranked là hopopop")
                return

            await ctx.send(f"**{mention}** est **{rank}** avec un winrate de **{winrate}%**, {'énorme sexe' if winrate > 50 else 'le gros nullos'}\n")
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

    TIER_ORDER = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", "EMERALD", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"]
    DIVISION_ORDER = ["IV", "III", "II", "I"]

    def rank_key(rank: str) -> tuple[int, int]:
        parts = rank.upper().split()
        if not parts or parts[0] == "UNRANKED":
            return -1, -1
        tier_i = TIER_ORDER.index(parts[0]) if parts[0] in TIER_ORDER else -1
        div_i = DIVISION_ORDER.index(parts[1]) if len(parts) > 1 and parts[1] in DIVISION_ORDER else -1
        return tier_i, div_i

    stats = []
    for key, player in PLAYERS.items():
        try:
            info = riot_client.get_player_info(player["puuid"])
            stats.append({"key": key, "name": player["name"], "rank": info.get("rank", "Unranked"), "winrate": info.get("winrate", 0)})
        except Exception as e:
            logger.warning("Failed to fetch stats for %s: %s", player["name"], e)
            stats.append({"key": key, "name": player["name"], "rank": "Unranked", "winrate": 0})

    if not stats:
        await ctx.send("Can't show leaderboard: no player data to display.")
        return

    stats.sort(key=lambda x: rank_key(x["rank"]), reverse=True)
    logger.debug("Leaderboard stats: %s", stats)

    best = PLAYERS[stats[0]["key"]]
    rows = "\n".join(f" {p['name']:<7}  | {p['rank']:<18} | {p['winrate']}%" for p in stats)
    message = (
        f"Ok tout le monde gobe le paf de <@{int(best['discord_id'])}>, le **GOAT** du discord\n\n"
        f"🏆 **Classement des Stonkers** 🏆\n"
        f"``` Nom      | Rang               | Winrate\n"
        f"------------------------------------------\n"
        f"{rows}\n```"
    )

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
        player: PlayerInfos = PLAYERS[player_name]

        try:
            last_match_id = riot_client.get_last_match_id(player["puuid"])
            message, embed = generate_match_info_response(player, riot_client.get_match_data(last_match_id))
            await ctx.send(content=message, embed=embed)
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
