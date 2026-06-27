import discord
from discord.ext import commands
from discord import app_commands

from utils.server_config import get_store


def _config_permission_check():
    async def predicate(interaction: discord.Interaction) -> bool:
        # Require Manage Server.
        member = interaction.user
        return bool(getattr(member, "guild_permissions", None) and member.guild_permissions.manage_guild)

    return app_commands.check(predicate)


def mercy_label(mercy: int) -> str:
    if mercy <= 0:
        return "Merciless"
    if mercy <= 6:
        return "Low"
    if mercy <= 12:
        return "Medium"
    if mercy <= 18:
        return "High"
    return "Overexaggerated"


class ServerConfigCog(commands.GroupCog, name="config"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.store = get_store()

    @app_commands.guild_only()
    @_config_permission_check()
    @app_commands.command(name="view", description="View this server's bot configuration.")
    async def view(self, interaction: discord.Interaction):
        cfg = await self.store.get(interaction.guild.id)

        def yn(v: bool) -> str:
            return "✅ Enabled" if v else "❌ Disabled"

        log_channel_id = cfg.get("log_channel_id")
        if log_channel_id:
            log_channel_value = f"<#{log_channel_id}>"
        else:
            log_channel_value = "None"

        softban_value = yn(bool(cfg.get("softban")))
        mercy = int(cfg.get("mercy", 12))
        mercy_value = f"{mercy}h ({mercy_label(mercy)})"
        silly_value = yn(bool(cfg.get("silly_mode")))

        honeypots = cfg.get("honeypot_channel_ids", [])
        if honeypots:
            shown = honeypots[:10]
            honeypot_value = ", ".join(f"<#{cid}>" for cid in shown)
            if len(honeypots) > len(shown):
                honeypot_value += f" (+{len(honeypots) - len(shown)} more)"
        else:
            honeypot_value = "None"

        stage_types = cfg.get("stage_types", ["ocr"])
        if stage_types:
            stage_types_value = ", ".join(sorted(stage_types))
        else:
            stage_types_value = "ocr"

        spam_threshold_value = str(int(cfg.get("spam_threshold", 4)))

        embed = discord.Embed(title="Server Config", color=discord.Color.dark_gold())
        embed.add_field(name="OCR Scanning", value=yn(bool(cfg.get("ocr_enabled"))), inline=True)
        embed.add_field(name="Detection Types", value=stage_types_value, inline=True)
        embed.add_field(name="Spam Threshold", value=spam_threshold_value, inline=True)
        embed.add_field(name="Log Channel", value=log_channel_value, inline=True)
        embed.add_field(name="Softban Mode", value=softban_value, inline=True)
        embed.add_field(name="Mercy", value=mercy_value, inline=True)
        embed.add_field(name="Silly Mode", value=silly_value, inline=True)
        embed.add_field(name="Honeypot Channels", value=honeypot_value, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.guild_only()
    @_config_permission_check()
    @app_commands.command(name="ocr_enabled", description="Enable/disable OCR scanning for images in this server.")
    async def ocr_enabled(self, interaction: discord.Interaction, enabled: bool):
        await self.store.set(interaction.guild.id, "ocr_enabled", bool(enabled))
        await interaction.response.send_message(f"OCR scanning is now {'enabled' if enabled else 'disabled'}.", ephemeral=True)

    @app_commands.guild_only()
    @_config_permission_check()
    @app_commands.command(
        name="stage_mode",
        description="Choose what triggers staging (ocr, threshold, or both).",
    )
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="ocr (image OCR keywords)", value="ocr"),
            app_commands.Choice(name="threshold (plain text keywords)", value="threshold"),
            app_commands.Choice(name="both", value="both"),
        ]
    )
    async def stage_mode(self, interaction: discord.Interaction, mode: app_commands.Choice[str]):
        if mode.value == "both":
            value = ["ocr", "threshold"]
        else:
            value = [mode.value]
        await self.store.set(interaction.guild.id, "stage_types", value)
        await interaction.response.send_message(f"Detection mode set to: `{mode.value}`.", ephemeral=True)

    @app_commands.guild_only()
    @_config_permission_check()
    @app_commands.command(
        name="spam_threshold",
        description="Set how many scam keywords are required to stage a user (1-50).",
    )
    async def spam_threshold(self, interaction: discord.Interaction, threshold: int):
        if threshold < 1 or threshold > 50:
            await interaction.response.send_message("Spam threshold must be between 1 and 50.", ephemeral=True)
            return
        await self.store.set(interaction.guild.id, "spam_threshold", int(threshold))
        await interaction.response.send_message(f"Spam threshold set to `{threshold}`.", ephemeral=True)

    @app_commands.guild_only()
    @_config_permission_check()
    @app_commands.command(name="log_channel", description="Set the log channel (or clear it).")
    async def log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        if channel is None:
            await self.store.set(interaction.guild.id, "log_channel_id", None)
            await interaction.response.send_message("Log channel cleared.", ephemeral=True)
            return

        await self.store.set(interaction.guild.id, "log_channel_id", int(channel.id))
        await interaction.response.send_message(f"Log channel set to {channel.mention}.", ephemeral=True)

    @app_commands.guild_only()
    @_config_permission_check()
    @app_commands.command(name="softban", description="Enable/disable softbans.")
    async def softban(self, interaction: discord.Interaction, enabled: bool):
        await self.store.set(interaction.guild.id, "softban", bool(enabled))
        action = "softban (ban then unban)" if enabled else "ban"
        await interaction.response.send_message(f"Punishment mode set to: `{action}`.", ephemeral=True)

    @app_commands.guild_only()
    @_config_permission_check()
    @app_commands.command(name="mercy", description="Set mercy level in hours (0-24).")
    async def mercy(self, interaction: discord.Interaction, hours: int):
        if hours < 0:
            await interaction.response.send_message(
                "Mercy must be `0` or higher.",
                ephemeral=True,
            )
            return

        if hours > 24:
            await interaction.response.send_message("Mercy must be `24` hours or less.", ephemeral=True)
            return

        await self.store.set(interaction.guild.id, "mercy", int(hours))
        await interaction.response.send_message(f"Mercy set to `{hours}h` ({mercy_label(hours)}).", ephemeral=True)

    @app_commands.guild_only()
    @_config_permission_check()
    @app_commands.command(name="silly_mode", description="Make the bot's messages VERY SILLY.")
    async def silly_mode(self, interaction: discord.Interaction, enabled: bool):
        await self.store.set(interaction.guild.id, "silly_mode", bool(enabled))
        await interaction.response.send_message(f"Silly mode is now {'enabled' if enabled else 'disabled'}.", ephemeral=True)

    @app_commands.guild_only()
    @_config_permission_check()
    @app_commands.command(name="reset", description="Reset this server's config to defaults.")
    async def reset(self, interaction: discord.Interaction):
        await self.store.reset(interaction.guild.id)
        await interaction.response.send_message("Server config reset to defaults.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(ServerConfigCog(bot))
