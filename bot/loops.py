from discord.ext import tasks
from riot_api.client import get_current_match
from config import PLAYERS, API_KEY, DISCORD_CHANNEL, CHAMPIONS
from .bot_instance import bot

players_in_game = set()


@tasks.loop(seconds=60)
async def check_players_in_game():
    # Get the channel
    channel = bot.get_channel(DISCORD_CHANNEL)
    if channel is None:
        try:
            channel = await bot.fetch_channel(DISCORD_CHANNEL)
        except Exception as e:
            print(f"Failed to fetch channel: {e}")
            return

    for player_name, data in PLAYERS.items():
        puuid = data['puuid']

        try:
            current_match = get_current_match(puuid, API_KEY)
            
            if current_match:
                if puuid not in players_in_game:
                    players_in_game.add(puuid)

                    mention = f"<@{int(data['discord_id'])}>"
                    message = ""
                    champion = ""

                    # Find player's champion
                    if puuid in current_match['players']:
                        champ_id = current_match['champions'][current_match['players'].index(puuid)]
                        champion = CHAMPIONS.get(champ_id, "un champion inconnu")

                    # Write message according to the game type
                    if current_match["gameType"] == '400':
                        message = f"{mention} remet les crampons pour une nouvelle game avec **{champion}**"
                    elif current_match["gameType"] == '420':
                        message = f"Omg {mention} part en ranked sur avec **{champion}** ! Tout pour les e-points"
                    elif current_match["gameType"] == '430':
                        message = f"{mention} a lancé une normale classique vanille #aucuneDraftAucunFun. Je vais même pas dire sur quel champ t'es pour la peine..."
                    elif current_match["gameType"] == '450':
                        message = f"{mention} veut chill et part en ARAM avec **{champion}**"
                    elif current_match["gameType"] == '900':
                        message = f"{mention} joue au mode clash... (Qui fait ça?)"
                    else:
                        return
                    await channel.send(message)

            else:
                if puuid in players_in_game:
                    players_in_game.remove(puuid)

        except Exception as e:
            print(f"Error checking current match for {player_name}: {e}")
