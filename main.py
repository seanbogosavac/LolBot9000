import os
import discord
from dotenv import load_dotenv
from src.riot_api import get_player_info
from discord.ext import commands

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
API_KEY = os.getenv("RIOT_API_KEY")
PUUID = {"sean": os.getenv("ID_SEAN"),
         "maxime": os.getenv("ID_MAXIME"),
         "thomas": os.getenv("ID_THOMAS"),
         "yannis": os.getenv("ID_YANNIS")}

#infomax = get_player_info(PUUID["maxime"], API_KEY)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print("LolBot9000 up and running")

@bot.command()
async def lol(ctx, summoner_name: str):
    summoner_name = summoner_name.lower()
    if summoner_name not in PUUID:
        await ctx.send(f"❌ Player '{summoner_name}' not found.")
        return

    puuid = PUUID[summoner_name]
    try:
        info = get_player_info(puuid, API_KEY)
        # You can adjust this part based on the structure of `info`
        rank = info.get("rank", "Unknown")
        tier = info.get("tier", "")
        lp = info.get("leaguePoints", 0)
        wins = info.get("wins", 0)
        losses = info.get("losses", 0)

        await ctx.send(
            f"📊 **{summoner_name.capitalize()}** is ranked **{tier} {rank}** with **{lp} LP**.\n"
            f"✅ {wins} Wins | ❌ {losses} Losses"
        )
    except Exception as e:
        print(f"Error fetching info for {summoner_name}: {e}")
        await ctx.send("⚠️ Failed to fetch player info.")

bot.run(DISCORD_TOKEN)
