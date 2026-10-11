import discord
from discord.ext import commands

from api import RiotClient
from config import API_KEY

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)
riot_client = RiotClient(api_key=API_KEY)
