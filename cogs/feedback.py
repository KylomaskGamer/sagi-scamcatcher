import discord
from discord import app_commands
from discord.ext import commands

import config
import re


def _dbg(msg: str) -> None:
    if getattr(config, "DEBUG", False):
        print(f"[FEEDBACK] {msg}")


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max(0, max_len - 1)] + "…"


class FeedbackCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _extract_user_id_from_embed(self, message: discord.Message) -> int | None:
        if not message.embeds:
            return None

        embed = message.embeds[0]
        footer_text = (embed.footer.text or "") if embed.footer else ""
        m = re.search(r"\bfeedback_user_id:(\d{15,25})\b", footer_text)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                return None

        for field in embed.fields:
            if field.name.strip().lower() != "from":
                continue
            m = re.search(r"`(\d{15,25})`", field.value or "")
            if m:
                try:
                    return int(m.group(1))
                except ValueError:
                    return None

        return None

    async def _dm_user(self, user_id: int, content: str, *, reference: discord.Message) -> bool:
        try:
            user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
        except Exception:
            return False

        embed = discord.Embed(
            title="Dev Reply to Your Feedback",
            description=_truncate(content, 4000),
            color=getattr(config, "EMBED_COLOR", 0x7D2D1F),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="Reference", value=f"Feedback ID: `{reference.id}`", inline=False)

        try:
            await user.send(embed=embed)
            return True
        except Exception:
            return False

    async def _send_to_devs(
        self,
        *,
        author: discord.abc.User,
        content: str,
        guild: discord.Guild | None,
        channel: discord.abc.Messageable | None,
        jump_url: str | None,
        source: str,
    ) -> None:
        feedback_channel_id = int(getattr(config, "FEEDBACK_CHANNEL_ID", 0) or 0)
        _dbg(f"_send_to_devs: feedback_channel_id={feedback_channel_id} source={source} author={author.id}")
        if not feedback_channel_id:
            raise RuntimeError("FEEDBACK_CHANNEL_ID is not configured")

        feedback_channel = self.bot.get_channel(feedback_channel_id)
        if feedback_channel is None:
            _dbg(f"_send_to_devs: cache miss, fetching channel {feedback_channel_id}")
            feedback_channel = await self.bot.fetch_channel(feedback_channel_id)

        embed = discord.Embed(
            title="New Feedback",
            description=_truncate(content, 4000),
            color=getattr(config, "EMBED_COLOR", 0x7D2D1F),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="From", value=f"{author} (`{author.id}`)", inline=False)
        embed.add_field(name="Source", value=source, inline=True)
        embed.set_footer(text=f"feedback_user_id:{author.id}")

        if guild is not None:
            embed.add_field(name="Guild", value=f"{guild.name} (`{guild.id}`)", inline=False)
        else:
            embed.add_field(name="Guild", value="DM / Unknown", inline=False)

        if channel is not None and hasattr(channel, "id"):
            try:
                channel_id = int(getattr(channel, "id"))
                channel_value = f"<#{channel_id}> (`{channel_id}`)"
            except Exception:
                channel_value = "Unknown"
            embed.add_field(name="Channel", value=channel_value, inline=False)

        if jump_url:
            embed.add_field(name="Jump", value=jump_url, inline=False)

        await feedback_channel.send(embed=embed)
        _dbg(f"_send_to_devs: sent embed to channel {feedback_channel_id}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        feedback_channel_id = int(getattr(config, "FEEDBACK_CHANNEL_ID", 0) or 0)
        if not feedback_channel_id or message.channel.id != feedback_channel_id:
            return
        _dbg(f"on_message: reply candidate msg={message.id} author={message.author.id}")

        if not message.reference or not message.reference.message_id:
            return

        if not message.guild or not isinstance(message.author, discord.Member):
            return

        perms = message.author.guild_permissions
        if not (perms.administrator or perms.manage_guild or perms.manage_messages or perms.moderate_members):
            _dbg(f"on_message: insufficient perms author={message.author.id}")
            return

        try:
            referenced = message.reference.resolved
            if referenced is None:
                referenced = await message.channel.fetch_message(message.reference.message_id)
        except Exception:
            return

        user_id = self._extract_user_id_from_embed(referenced)
        if not user_id:
            _dbg(f"on_message: couldn't extract user id from referenced msg={referenced.id}")
            return

        body = (message.content or "").strip()
        if message.attachments:
            attachment_lines = "\n".join(a.url for a in message.attachments if a.url)
            if attachment_lines:
                body = (body + "\n\n" + attachment_lines).strip()

        if not body:
            return

        ok = await self._dm_user(user_id, body, reference=referenced)
        _dbg(f"on_message: dm_user user_id={user_id} ok={ok}")
        try:
            await message.add_reaction("✅" if ok else "⚠️")
        except Exception:
            pass

    @app_commands.command(name="feedback", description="Send a message to the Sagi devs.")
    @app_commands.describe(message="Your feedback (bugs, suggestions, etc.)")
    async def feedback_slash(self, interaction: discord.Interaction, message: str):
        _dbg(f"slash: /feedback invoked by user={interaction.user.id} guild={getattr(interaction.guild,'id',None)}")
        content = (message or "").strip()
        if not content:
            await interaction.response.send_message("Please include a message.", ephemeral=True)
            return

        try:
            await self._send_to_devs(
                author=interaction.user,
                content=content,
                guild=interaction.guild,
                channel=interaction.channel,
                jump_url=None,
                source="slash",
            )
        except Exception:
            await interaction.response.send_message(
                "Couldn't send feedback right now — try again later.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message("Thanks! Sent to the devs.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(FeedbackCog(bot))
