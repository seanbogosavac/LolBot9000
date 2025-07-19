from riot_api.client import get_player_info, get_last_match_id, get_match_data
from config import PLAYERS, API_KEY
from .bot_instance import bot
from .functions.generate_match_embed import generate_match_embed
from .functions.generate_kda_message import generate_kda_message


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
        # Gather data about the player
        player = PLAYERS[player_name]
        info = get_player_info(player['puuid'], API_KEY)
        rank = info.get("rank", "")
        winrate = info.get("winrate", "")

        # Generate a message and send it
        mention = f"<@{int(player['discord_id'])}>"
        message = f"**{mention}** est **{rank}** avec un winrate de **{winrate}%**, {'énorme sexe' if winrate > 50 else 'le gros nullos'}\n"
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
        # Gather data about the player's last match
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

        # Generate and send the match data
        message = generate_kda_message(player_data, player['discord_id'])
        embed = generate_match_embed(player_name, last_match_data, player['puuid'])
        await ctx.send(
            content=message,
            embed=embed
            )
    except Exception as e:
        print(f"Error fetching info for {target}: {e}")
        await ctx.send("G beugé chef")
