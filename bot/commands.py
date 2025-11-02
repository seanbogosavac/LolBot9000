from api.client import get_match_data, get_player_info, get_last_match_id
from config import PLAYERS, API_KEY
from .bot_instance import bot
from .functions.generate_match_info_response import generate_match_info_response
from .functions.get_targeted_player_info import get_targeted_player_info

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
async def lastgame(ctx, target=None):
    # Check if there is a target
    if target is None:
        await ctx.send("Oh tu veux les infos de qui ? Dis les termes là !")
        return

    # Gathers data about the targeted player
    player_info = await get_targeted_player_info(ctx, target)
    if not player_info:
        await ctx.send("C'est qui frère ?")
        return

    try:
        # Fetch data of the last match played
        last_match_id = get_last_match_id(player_info['puuid'], API_KEY)
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
