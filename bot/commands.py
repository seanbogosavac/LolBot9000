from typing import Optional

from api.client import get_match_data, get_player_info, get_last_match_id
from config import PLAYERS, API_KEY
from .bot_instance import bot
from .functions.generate_match_info_response import generate_match_info_response
from .types import PlayerInfos


@bot.command()
async def lol(ctx, target=None):
    # Case where noone is mentioned
    if target is None:
        await ctx.send("Oh tu veux les infos de qui ? Dis les termes là !")
        return

    # Somebody is mentioned
    player_name = ""

    if len(ctx.message.mentions) > 0:
        discord_id = str(ctx.message.mentions[0].id)

        for name, data in PLAYERS.items():
            if data["discord_id"] == discord_id:
                player_name = name
                break
    else:
        player_name = target.lower()

    # If the person mentioned is not recognized
    if player_name not in PLAYERS:
        await ctx.send("C'est qui frère ?")
        return

    # Gathering player rank
    player = PLAYERS[player_name]
    mention = f"<@{int(player['discord_id'])}>"
    try:
        # Api call
        info = get_player_info(player['puuid'], API_KEY)
        rank = info.get("rank", "")
        winrate = info.get("winrate", "")

        # Generate a message and send it
        message = f"**{mention}** est **{rank}** avec un winrate de **{winrate}%**, {'énorme sexe' if winrate > 50 else 'le gros nullos'}\n"
        await ctx.send(message)
    except IndexError:
        await ctx.send(f"T'as pas de rang **{mention}**, va faire tes ranked là hopopop")
    except Exception as e:
        print(f"Error fetching info for {target}: {e}")
        await ctx.send("G beugé chef")


@bot.command()
async def leaderboard(ctx):
    stats = []

    for player in PLAYERS.values():
        info = get_player_info(player['puuid'], API_KEY)
        stats.append({
            "name": player['name'],
            "rank": info.get("rank", "Unranked"),
            "winrate": info.get("winrate", "N/A")
        })

    if not stats:
        await ctx.send("Can't show leaderboard: no player data to display.")
        return

    # Define order of tiers and divisions
    tier_order = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"]
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

    # Build message
    message = "🏆 **Classement des goats** 🏆\n"
    for i, player in enumerate(stats, start=1):
        message += f"**{player['name']}** — {player['rank']} ({player['winrate']}% WR)\n"

    try:
        await ctx.send(message)
    except Exception as e:
        print(f"Error sending leaderboard: {e}")
        await ctx.send("G beugé chef")


@bot.command()
async def lastgame(ctx, target=None):
    # Check if there is a target
    if target is None:
        await ctx.send("Oh tu veux les infos de qui ? Dis les termes là !")
        return

    if len(ctx.message.mentions) > 0:
        discord_id: str = str(ctx.message.mentions[0].id)

        player_info: Optional[PlayerInfos] = None
        for name, data in PLAYERS.items():
            if data["discord_id"] == discord_id or name == target.lower():
                player_info = data

        if not player_info:
            await ctx.send("C'est qui frère ?")
            return

        try:
            # Fetch data of the last match played
            last_match_id: int = get_last_match_id(player_info['puuid'], API_KEY)
            last_match_data = get_match_data(last_match_id, API_KEY)

            # Generates response
            message, embed = generate_match_info_response(player_info, last_match_data)
            await ctx.send(
                content=message,
                embed=embed
                )
        except Exception as e:
            print(f"Error fetching info for {target}: {e}")
            await ctx.send("G beugé chef")
