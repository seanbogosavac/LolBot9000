import logging
import re

from api import PlayerStats, RiotAPIError
from config import riot_client
from db import PlayerInfos

from .api_worker import run_blocking
from .bot_instance import bot
from .exceptions import NoPlayerMentioned, UnknownPlayer
from .helpers import generate_match_info_response
from .roster import (
    PlayerActionError,
    add_player,
    ensure_riot_names,
    find_player,
    get_player_by_discord_id,
    list_players,
    remove_player,
    update_player,
)

logger = logging.getLogger(__name__)

USER_MENTION = re.compile(r"<@!?(\d+)>")


async def find_targeted_player(ctx, target) -> PlayerInfos:
    """Resolve a command target (mention or name string) to a registered player."""
    if target is None:
        raise NoPlayerMentioned

    if ctx.message.mentions:
        player = get_player_by_discord_id(str(ctx.message.mentions[0].id))
    else:
        player = find_player(target)

    if player is None:
        raise UnknownPlayer
    return player


@bot.command()
async def lol(ctx, target=None):
    logger.info("Command !lol invoked by %s (target: %s)", ctx.author, target)
    try:
        player: PlayerInfos = await find_targeted_player(ctx, target)
        mention = f"<@{int(player['discord_id'])}>"

        try:
            info: PlayerStats = await run_blocking(riot_client.get_player_info, player["puuid"])
            rank, winrate, streak = info.get("rank", "Unranked"), info.get("winrate", 0), info.get("streak", 0)

            if rank == "Unranked":
                await ctx.send(f"T'as pas de rang **{mention}**, va faire tes ranked là hopopop")
                return

            if streak > 0:
                streak_text = f"🔥 {streak} win streak"
                vibe = "énorme sexe"
            elif streak < 0:
                streak_text = f"💀 {abs(streak)} lose streak"
                vibe = "le gros nullos"
            else:
                streak_text = "pas de streak"
                vibe = "le gros nullos"

            await ctx.send(f"**{mention}** est **{rank}** avec un winrate de **{winrate}%** | {streak_text}, {vibe}\n")
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
    except PlayerActionError as e:
        await ctx.send(str(e))


@bot.command()
async def leaderboard(ctx):
    logger.info("Command !leaderboard invoked by %s", ctx.author)
    try:
        roster = list_players()
    except PlayerActionError as e:
        await ctx.send(str(e))
        return

    TIER_ORDER = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", "EMERALD", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"]
    DIVISION_ORDER = ["IV", "III", "II", "I"]

    def rank_key(rank: str) -> tuple[int, int]:
        parts = rank.upper().split()
        if not parts or parts[0] == "UNRANKED":
            return -1, -1
        tier_i = TIER_ORDER.index(parts[0]) if parts[0] in TIER_ORDER else -1
        div_i = DIVISION_ORDER.index(parts[1]) if len(parts) > 1 and parts[1] in DIVISION_ORDER else -1
        return tier_i, div_i

    if not roster:
        await ctx.send("Can't show leaderboard: no player data to display.")
        return

    stats = []
    for player in roster:
        try:
            info = await run_blocking(riot_client.get_player_info, player["puuid"])
            stats.append({"player": player, "rank": info.get("rank", "Unranked"), "winrate": info.get("winrate", 0)})
        except Exception as e:
            logger.warning("Failed to fetch stats for %s: %s", player["name"], e)
            stats.append({"player": player, "rank": "Unranked", "winrate": 0})

    stats.sort(key=lambda x: rank_key(x["rank"]), reverse=True)
    logger.debug("Leaderboard stats: %s", stats)

    best = stats[0]["player"]
    rows = "\n".join(f" {s['player']['name']:<7}  | {s['rank']:<18} | {s['winrate']}%" for s in stats)
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
        player: PlayerInfos = await find_targeted_player(ctx, target)

        try:
            last_match_id = await run_blocking(riot_client.get_last_match_id, player["puuid"])
            match_data = await run_blocking(riot_client.get_match_data, last_match_id)
            message, embed = generate_match_info_response(player, match_data)
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
    except PlayerActionError as e:
        await ctx.send(str(e))


###
# PLAYER ROSTER MANAGEMENT
###

def parse_player_args(args: list[str], *, require_riot_id: bool = False) -> tuple[str, str | None, str | None]:
    """Split roster command arguments into (name, discord_id, riot_id).

    The Discord account is given as a mention or a raw snowflake, the Riot account as a
    `Pseudo#TAG` Riot ID or a raw puuid. Everything left over is the player name, so
    names with spaces work too:

        !addplayer Maxou <@123456789012345678> Pseudo#EUW
    """
    discord_id: str | None = None
    riot_id: str | None = None
    rest: list[str] = []

    for index, arg in enumerate(args):
        mention = USER_MENTION.fullmatch(arg)
        if mention:
            discord_id = discord_id or mention.group(1)
            continue
        if arg.isdigit() and len(arg) >= 17:
            discord_id = discord_id or arg
            continue
        if riot_id is None and ("#" in arg or (len(arg) >= 16 and index == len(args) - 1)):
            riot_id = arg
            continue
        rest.append(arg)

    name = " ".join(rest)
    if require_riot_id and riot_id is None:
        raise PlayerActionError("Il me faut le compte Riot du joueur, au format `Pseudo#TAG` (ou directement son puuid).")
    return name, discord_id, riot_id


@bot.command()
async def addplayer(ctx, *args: str):
    logger.info("Command !addplayer invoked by %s with args %s", ctx.author, args)
    try:
        name, discord_id, riot_id = parse_player_args(list(args), require_riot_id=True)
        if not name:
            raise PlayerActionError("Donne-moi un pseudo, du style `!addplayer Maxou <@discord> Pseudo#TAG`.")
        if discord_id is None:
            raise PlayerActionError("Tag la personne dont tu veux enregistrer le compte, ou donne son ID Discord.")

        player = await run_blocking(add_player, name, discord_id, riot_id)
        await ctx.send(f"J'ai enregistré **{player['name']}** (<@{int(player['discord_id'])}>) dans la base des joueurs.")
    except PlayerActionError as e:
        await ctx.send(str(e))
    except Exception as e:
        logger.error("Error adding player %s: %s", " ".join(args), e, exc_info=True)
        await ctx.send("G beugé chef")


@bot.command()
async def updateplayer(ctx, *args: str):
    logger.info("Command !updateplayer invoked by %s with args %s", ctx.author, args)
    try:
        name, discord_id, riot_id = parse_player_args(list(args))
        if discord_id is None and riot_id is None:
            raise PlayerActionError("Donne-moi un nouveau Discord ou un nouveau compte Riot à lier.")

        player = await run_blocking(update_player, name, discord_id=discord_id, riot_identifier=riot_id)
        await ctx.send(f"Compte mis à jour pour **{player['name']}** (<@{int(player['discord_id'])}>).")
    except PlayerActionError as e:
        await ctx.send(str(e))
    except Exception as e:
        logger.error("Error updating player %s: %s", " ".join(args), e, exc_info=True)
        await ctx.send("G beugé chef")


@bot.command()
async def removeplayer(ctx, *args: str):
    logger.info("Command !removeplayer invoked by %s with args %s", ctx.author, args)
    name = " ".join(args)
    try:
        player = remove_player(name)
        await ctx.send(f"**{player['name']}** n'est plus dans la base, je le surveille plus.")
    except PlayerActionError as e:
        await ctx.send(str(e))
    except Exception as e:
        logger.error("Error removing player %s: %s", name, e, exc_info=True)
        await ctx.send("G beugé chef")


def _riot_display(player: PlayerInfos) -> str:
    """What `!players` shows for a Riot account: the in-game name, or the puuid head if unknown."""
    return player["riot_name"] or f"`{player['puuid'][:16]}…`"


@bot.command(name="players")
async def listplayers(ctx):
    logger.info("Command !players invoked by %s", ctx.author)
    try:
        roster = list_players()
    except PlayerActionError as e:
        await ctx.send(str(e))
        return

    if not roster:
        await ctx.send("Y'a personne enregistré là. Fais `!addplayer Pseudo <@discord> Riot#TAG`.")
        return

    # Rows imported from the old .env layout only have a puuid, so resolve the in-game
    # names we're missing before printing them.
    roster = await run_blocking(ensure_riot_names, roster)

    rows = "\n".join(f" {p['name']:<12} | <@{int(p['discord_id'])}> | {_riot_display(p)}" for p in roster)
    await ctx.send(
        f"📋 **{len(roster)} joueur(s) enregistrés**\n"
        f"```\n Nom          | Discord                    | Riot\n"
        f"-----------------------------------------------------------\n{rows}\n```"
    )
