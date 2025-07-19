from discord.ext import commands
from riot_api.client import get_player_info, get_last_match_id, get_match_data
from config import PLAYERS, API_KEY
from .bot_instance import bot
from .functions import format_match_embed

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
        player = PLAYERS[player_name]
        info = get_player_info(player['puuid'], API_KEY)
        rank = info.get("rank", "")
        winrate = info.get("winrate", "")

        mention = f"<@{int(player['discord_id'])}>"
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


@bot.command()
async def lastgame(ctx, target=None):
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
        player = PLAYERS[player_name]
        last_match_id = get_last_match_id(player['puuid'], API_KEY)
        last_match_data = get_match_data(last_match_id, API_KEY)
        if not last_match_data:
            await ctx.send("J'ai pas de données pour ce guy")
            return
        
        # Find the participant data for the requested player
        player_data = None
        for p in last_match_data['participants']:
            if p['puuid'] == player['puuid']:
                player_data = p
                break
        if not player_data:
            await ctx.send("Aaaaaaaaaaah je te trouve pas dans le match")
            return

        message = ""
        mention = f"<@{int(player['discord_id'])}>"

        player_kda = (player_data['kills'] + player_data['assists']) / player_data['deaths']
        if player_data['win'] == True:
            if player_kda > 5:
                message = f"**{mention}** a retourné l'équipe adverse avec un KDA aussi gros que son sexe\n"
            if player_kda < 0.5:
                message = f"**{mention}** a gagné sa dernière game mais vu ses stats c'est pas graçe à lui, bref...\n"
            else:
                message = f"**{mention}** a gagné sa dernière game\n"
        elif player_data['win'] == False:
            if player_kda > 5:
                message = f"**{mention}** t'a perdu ta dernière game mais nonobstant tu restes le goat\n"
            if player_kda < 0.5:
                message = f"**{mention}** essaie de mieux jouer la prochaine fois nan ? Histoire de pas faire perdre 40 min a tes mates ?\n"
            else:
                message = f"**{mention}** a perdu sa dernière game\n"

        
        embed = format_match_embed(player_name, last_match_data, player['puuid'])
        await ctx.send(
            content=message,
            embed=embed
            )
    except Exception as e:
        print(f"Error fetching info for {target}: {e}")
        await ctx.send("G beugé chef")
