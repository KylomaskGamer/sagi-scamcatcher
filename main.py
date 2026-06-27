import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import traceback
from config import DISCORD_TOKEN, COMMAND_PREFIX, SHARD_COUNT

intents = discord.Intents.default()
intents.message_content = True
bot = commands.AutoShardedBot(
    command_prefix=COMMAND_PREFIX,
    intents=intents,
    shard_count=SHARD_COUNT,
)

@bot.event
async def on_ready():
    print(f"Sagi is online! Logged in as {bot.user}")
    await bot.change_presence(activity=discord.CustomActivity(name="Beating up scambots! Again! Hell yeah!"))
    await bot.tree.sync()

@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"[COMMAND ERROR] {type(error).__name__}: {error}")
    traceback.print_exception(type(error), error, error.__traceback__)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    print(f"[APP COMMAND ERROR] {type(error).__name__}: {error}")
    traceback.print_exception(type(error), error, error.__traceback__)

async def load_cogs():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            mod = f'cogs.{filename[:-3]}'
            try:
                await bot.load_extension(mod)
                print(f"Loaded {filename}")
            except commands.errors.NoEntryPointError as e:
                pass

async def main():
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN is not set")
    async with bot:
        await load_cogs()
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
