import discord
from discord import app_commands
from discord.ext import commands

from utils.server_config import get_store


class HoneypotCog(commands.GroupCog, name="honeypot"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.store = get_store()

    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.command(name="activate", description="Activate honeypot in the current channel.")
    async def activate(self, interaction: discord.Interaction):
        cfg = await self.store.get(interaction.guild.id)
        channel_id = int(interaction.channel_id)

        channel_ids = set(cfg.get("honeypot_channel_ids", []))
        channel_ids.add(channel_id)
        await self.store.set(interaction.guild.id, "honeypot_channel_ids", sorted(channel_ids))

        extra = ""
        channel_name = (getattr(interaction.channel, "name", "") or "").lower()
        if "honey" in channel_name or "pot" in channel_name:
            extra = "\n-# Fun fact: channel names don't really bait bots. But it can't hurt."

        await interaction.response.send_message(
            f"Honeypot activated in <#{channel_id}>.{extra}",
            ephemeral=True,
        )

    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.command(name="deactivate", description="Deactivate honeypot in the current channel.")
    async def deactivate(self, interaction: discord.Interaction):
        cfg = await self.store.get(interaction.guild.id)
        channel_id = int(interaction.channel_id)

        channel_ids = set(cfg.get("honeypot_channel_ids", []))
        if channel_id in channel_ids:
            channel_ids.remove(channel_id)
            await self.store.set(interaction.guild.id, "honeypot_channel_ids", sorted(channel_ids))

        await interaction.response.send_message(
            f"Honeypot deactivated in <#{channel_id}>.", ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(HoneypotCog(bot))
