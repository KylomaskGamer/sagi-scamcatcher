import discord
from discord import app_commands
from discord.ext import commands

from utils.metrics import get_metrics


def _fmt_seconds(seconds: float) -> str:
    seconds = int(max(0, seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, sec = divmod(rem, 60)
    if days:
        return f"{days}d {hours}h {minutes}m {sec}s"
    if hours:
        return f"{hours}h {minutes}m {sec}s"
    if minutes:
        return f"{minutes}m {sec}s"
    return f"{sec}s"


class StatusCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.metrics = get_metrics()

    @app_commands.command(name="status", description="Show bot status and moderation/OCR statistics.")
    async def status(self, interaction: discord.Interaction):
        uptime = self.metrics.uptime_seconds()

        guild_count = len(getattr(self.bot, "guilds", []) or [])
        shard_count = getattr(self.bot, "shard_count", None)
        latency_ms = int((getattr(self.bot, "latency", 0.0) or 0.0) * 1000)

        ocr_avg = self.metrics.ocr_timer.avg_seconds
        ocr_avg_ms = int(ocr_avg * 1000) if ocr_avg is not None else None
        ocr_min_ms = int(self.metrics.ocr_timer.min_seconds * 1000) if self.metrics.ocr_timer.min_seconds is not None else None
        ocr_max_ms = int(self.metrics.ocr_timer.max_seconds * 1000) if self.metrics.ocr_timer.max_seconds is not None else None

        embed = discord.Embed(
            title="Sagi Status",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow(),
        )

        embed.add_field(name="Uptime", value=_fmt_seconds(uptime), inline=True)
        embed.add_field(name="Guilds", value=str(guild_count), inline=True)
        embed.add_field(name="Latency", value=f"{latency_ms} ms", inline=True)

        embed.add_field(
            name="Shards",
            value=str(shard_count) if shard_count is not None else "auto",
            inline=True,
        )

        embed.add_field(
            name="Moderation (since start)",
            value=(
                f"- Staged: `{self.metrics.staged_users}`\n"
                f"- Verified: `{self.metrics.verifications_passed}`\n"
                f"- Timeouts set: `{self.metrics.timeouts_set}`\n"
                f"- Timeouts cleared: `{self.metrics.timeouts_cleared}`\n"
                f"- Bans: `{self.metrics.bans}`\n"
                f"- Softbans: `{self.metrics.softbans}`"
            ),
            inline=False,
        )

        if ocr_avg_ms is None:
            ocr_value = f"- Calls: `{self.metrics.ocr_calls}`\n- Avg: `n/a`"
        else:
            ocr_value = (
                f"- Calls: `{self.metrics.ocr_calls}`\n"
                f"- Avg: `{ocr_avg_ms} ms`\n"
                f"- Min: `{ocr_min_ms} ms`\n"
                f"- Max: `{ocr_max_ms} ms`"
            )
        embed.add_field(name="OCR (since start)", value=ocr_value, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(StatusCog(bot))
