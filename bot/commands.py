from discord.ext import commands
from riot_api.client import get_player_info
from config import PLAYERS, API_KEY
from .bot_instance import bot

@bot.command()
async def lol(ctx, target=None):
    if target is None:
        await ctx.send("Oh tu veux les infos de qui ? Dis les termes là !")
        return

    player_name = None

    if len(ctx.message.mentions) > 0:
        discord_id = str(ctx.message.mentions[0].id)

        for name, data in PLAYERS.items():
            if data["discord_id"] == discord_id:
                player_name = name
                break
    else:
        player_name = target.lower()

    if player_name not in PLAYERS:
        await ctx.send("C'est qui frère ?")
        return

    try:
        info = get_player_info(PLAYERS[player_name]['puuid'], API_KEY)
        rank = info.get("rank", "")
        winrate = info.get("winrate", "")

        mention = f"<@{int(PLAYERS[player_name]['discord_id'])}>"
        message = ""
        if winrate > 50:
            message = f"**{mention}** est **{rank}** avec un winrate de **{winrate}%**, énorme sexe\n"
        else:
            message = f"**{mention}** est **{rank}** avec un winrate de **{winrate}%**, le gros nullos\n"

        await ctx.send(message)
    except IndexError:
        await ctx.send(f"T'as pas de rang **{mention}**, va faire tes ranked là hopopop")
    except Exception as e:
        print(f"Error fetching info for {target}: {e}")
        await ctx.send("G beugé chef")
