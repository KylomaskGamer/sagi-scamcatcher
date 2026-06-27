import asyncio
import datetime
import re
import time

import discord
from discord.ext import commands

import config
import utils.ocr as ocr
from utils.metrics import get_metrics
from utils.server_config import get_store


def _dbg(msg: str) -> None:
    if getattr(config, "DEBUG", False):
        print(f"[AUTOMOD] {msg}")


class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ocr = ocr.OCRProcessor()
        self.server_config = get_store()
        self.metrics = get_metrics()

        self.stagers = set()  # was list, set is better
        self._stagers_lock = asyncio.Lock()

    def _evil_keywords_from_text(self, text: str) -> set[str]:
        lower = text.lower()
        tokens = set(re.findall(r"[a-z0-9']+", lower))

        evil: set[str] = set()
        for keyword in config.SCAM_KEYWORDS:
            keyword_lower = keyword.lower()
            if " " in keyword_lower:
                if keyword_lower in lower:
                    evil.add(keyword_lower)
            else:
                if keyword_lower in tokens:
                    evil.add(keyword_lower)
        return evil

    # ---------------- VIEW ----------------
    class StageView(discord.ui.View):
        def __init__(
            self,
            cog: "AutoMod",
            *,
            guild_id: int,
            user_id: int,
            stage_seconds: int,
            softban_enabled: bool,
            silly_mode: bool,
            stage_expires_unix: int,
            source_message: discord.Message | None,
        ):
            super().__init__(timeout=stage_seconds)
            self.cog = cog
            self.guild_id = guild_id
            self.user_id = user_id
            self.stage_seconds = stage_seconds
            self.softban_enabled = softban_enabled
            self.silly_mode = silly_mode
            self.stage_expires_unix = stage_expires_unix
            self.source_message = source_message
            self.prompt_message: discord.Message | None = None
            self.clicked = False

        # NOTE: discord expects a unicode emoji (or PartialEmoji), not a :name: string.
        @discord.ui.button(emoji="🛡️", style=discord.ButtonStyle.green)
        async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != self.user_id:
                msg = "who are you"
                if self.silly_mode:
                    msg = "who r u. identify urs (silly)elf, lil goblin"
                await interaction.response.send_message(msg, ephemeral=interaction.guild is not None)
                return

            self.clicked = True
            self.stop()

            try:
                await self.cog._clear_stage(self.user_id)
                await self.cog._untimeout_user(self.guild_id, self.user_id)
                self.cog.metrics.verifications_passed += 1
                msg = "okey"
                if self.silly_mode:
                    msg = "okey-dokey, certified hooman"
                await interaction.response.send_message(msg, ephemeral=interaction.guild is not None)
            except Exception:
                await interaction.response.send_message(
                    "..ok i cant untime you out for some reason so uhh wait until it goes out\n"
                    "..i did take note that you pressed te human button! pinkie promise i wont ban you when time is up",
                    ephemeral=interaction.guild is not None,
                )

            try:
                await interaction.message.delete()
            except Exception:
                pass

        async def on_timeout(self):
            for item in self.children:
                item.disabled = True

            if self.prompt_message:
                try:
                    await self.prompt_message.edit(view=self)
                except Exception:
                    pass

            if not self.clicked:
                try:
                    if self.softban_enabled:
                        await self.cog._softban_user(self.guild_id, self.user_id, reason="spambot")
                    else:
                        await self.cog._ban_user(self.guild_id, self.user_id, reason="spambot")
                except Exception:
                    pass
                finally:
                    await self.cog._clear_stage(self.user_id)

    # ---------------- CORE STAGE LOGIC ----------------
    async def _clear_stage(self, user_id: int) -> None:
        async with self._stagers_lock:
            self.stagers.discard(user_id)

    async def _untimeout_user(self, guild_id: int, user_id: int) -> None:
        guild = self.bot.get_guild(guild_id)
        if not guild:
            _dbg(f"_untimeout_user: guild {guild_id} not found")
            return

        member = guild.get_member(user_id)
        if not member:
            try:
                member = await guild.fetch_member(user_id)
            except Exception:
                _dbg(f"_untimeout_user: fetch_member failed guild={guild_id} user={user_id}")
                return

        try:
            await member.edit(timed_out_until=None, reason="AutoMod: verified human")
            self.metrics.timeouts_cleared += 1
            _dbg(f"untimeout ok guild={guild_id} user={user_id}")
        except Exception as e:
            _dbg(f"untimeout failed guild={guild_id} user={user_id} err={type(e).__name__}: {e}")

    async def _softban_user(self, guild_id: int, user_id: int, *, reason: str) -> None:
        guild = self.bot.get_guild(guild_id)
        if not guild:
            _dbg(f"_softban_user: guild {guild_id} not found")
            return

        try:
            target: discord.abc.Snowflake = await self.bot.fetch_user(user_id)
        except Exception:
            target = discord.Object(id=user_id)

        try:
            await guild.ban(target, reason=reason, delete_message_days=0)
            self.metrics.softbans += 1
            _dbg(f"softban: ban ok guild={guild_id} user={user_id} reason={reason}")
        finally:
            try:
                await guild.unban(target, reason="maybe a human lets try again")
                _dbg(f"softban: unban ok guild={guild_id} user={user_id}")
            except Exception as e:
                _dbg(f"softban: unban failed guild={guild_id} user={user_id} err={type(e).__name__}: {e}")

    async def _ban_user(self, guild_id: int, user_id: int, *, reason: str) -> None:
        guild = self.bot.get_guild(guild_id)
        if not guild:
            _dbg(f"_ban_user: guild {guild_id} not found")
            return

        try:
            target: discord.abc.Snowflake = await self.bot.fetch_user(user_id)
        except Exception:
            target = discord.Object(id=user_id)

        try:
            await guild.ban(target, reason=reason, delete_message_days=0)
            self.metrics.bans += 1
            _dbg(f"ban ok guild={guild_id} user={user_id} reason={reason}")
        except Exception as e:
            _dbg(f"ban failed guild={guild_id} user={user_id} err={type(e).__name__}: {e}")

    async def stage_user(self, member: discord.Member, channel: discord.abc.Messageable, source_message: discord.Message | None, cfg: dict):
        async with self._stagers_lock:
            if member.id in self.stagers:
                _dbg(f"stage_user: already staged guild={member.guild.id} user={member.id}")
                return
            self.stagers.add(member.id)
            self.metrics.staged_users += 1

        softban_enabled = bool(cfg.get("softban", True))
        mercy_hours = int(cfg.get("mercy", 12))
        silly_mode = bool(cfg.get("silly_mode", False))
        _dbg(
            f"stage_user: start guild={member.guild.id} user={member.id} mercy_hours={mercy_hours} softban={softban_enabled} silly={silly_mode}"
        )

        if mercy_hours <= 0:
            try:
                if softban_enabled:
                    await self._softban_user(member.guild.id, member.id, reason="spambot")
                else:
                    await self._ban_user(member.guild.id, member.id, reason="spambot")
            finally:
                await self._clear_stage(member.id)
            return

        stage_seconds = mercy_hours * 60 * 60
        future = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=stage_seconds)
        unix = int(future.timestamp())

        try:
            await member.edit(timed_out_until=future, reason="AutoMod: suspected scam image spam")
            self.metrics.timeouts_set += 1
            _dbg(f"timeout set guild={member.guild.id} user={member.id} until_unix={unix}")
        except Exception as e:
            _dbg(f"timeout set failed guild={member.guild.id} user={member.id} err={type(e).__name__}: {e}")

        view = self.StageView(
            self,
            guild_id=member.guild.id,
            user_id=member.id,
            stage_seconds=stage_seconds,
            softban_enabled=softban_enabled,
            silly_mode=silly_mode,
            stage_expires_unix=unix,
            source_message=source_message,
        )

        if silly_mode:
            msg = (
                f"hewwo {member.mention} i detected some **EVIL** activity from you\n"
                f"bonk the shield button to prove ur a real hooman, or i will explode <t:{unix}:R>"
            )
        else:
            punishment = "softban" if softban_enabled else "ban"
            msg = (
                f"hey {member.mention} i detected sus activity from you\n"
                f"click this button to verify you're human, or I'll {punishment} you <t:{unix}:R>"
            )

        try:
            view.prompt_message = await member.send(msg, view=view)
            _dbg(f"prompt DM sent guild={member.guild.id} user={member.id}")
        except discord.Forbidden:
            _dbg(f"prompt DM forbidden guild={member.guild.id} user={member.id}; trying channel fallback")
            try:
                view.prompt_message = await channel.send(
                    msg
                    + "\n-# Couldn't DM you, so I'm posting this here instead.",
                    view=view,
                )
                _dbg(f"prompt channel sent guild={member.guild.id} user={member.id} channel_id={getattr(channel,'id',None)}")
            except Exception as e:
                _dbg(
                    f"prompt channel send failed guild={member.guild.id} user={member.id} channel_id={getattr(channel,'id',None)} err={type(e).__name__}: {e}; clearing stage + untimeout"
                )
                await self._clear_stage(member.id)
                await self._untimeout_user(member.guild.id, member.id)
        except Exception as e:
            _dbg(
                f"prompt DM send failed guild={member.guild.id} user={member.id} err={type(e).__name__}: {e}; clearing stage + untimeout"
            )
            await self._clear_stage(member.id)
            await self._untimeout_user(member.guild.id, member.id)

    # ---------------- MESSAGE LISTENER ----------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        # what if mee6 is hacked? huh?

        if not message.guild or not isinstance(message.author, discord.Member):
            return

        cfg = await self.server_config.get(message.guild.id)
        stage_types = set(cfg.get("stage_types", ["ocr"]))
        ocr_enabled = bool(cfg.get("ocr_enabled", cfg.get("enabled", True)))

        honeypot_channel_ids = set(cfg.get("honeypot_channel_ids", []))
        if honeypot_channel_ids and message.channel.id in honeypot_channel_ids:
            try:
                await message.delete()
            except Exception:
                pass
            _dbg(f"honeypot hit guild={message.guild.id} channel={message.channel.id} author={message.author.id}")

            log_channel_id = cfg.get("log_channel_id")
            if log_channel_id:
                log_channel = message.guild.get_channel(int(log_channel_id))
                if log_channel:
                    try:
                        await log_channel.send(
                            f"AutoMod: honeypot triggered in <#{message.channel.id}> by {message.author.mention}"
                        )
                    except Exception:
                        pass

            if not message.author.bot:
                await self.stage_user(message.author, message.channel, message, cfg)
            return

        min_keywords = int(cfg.get("spam_threshold", getattr(config, "MIN_KEYWORDS", 4)))

        if "threshold" in stage_types and message.content:
            evil = self._evil_keywords_from_text(message.content)
            if len(evil) >= min_keywords:
                _dbg(
                    f"scam-text hit guild={message.guild.id} channel={message.channel.id} author={message.author.id} evil_count={len(evil)} evil={sorted(evil)}"
                )
                try:
                    await message.delete()
                except Exception:
                    pass

                log_channel_id = cfg.get("log_channel_id")
                if log_channel_id:
                    log_channel = message.guild.get_channel(int(log_channel_id))
                    if log_channel:
                        try:
                            prefix = "AutoMod:"
                            if cfg.get("silly_mode"):
                                prefix = "SillyMod:"
                            await log_channel.send(
                                f"{prefix} staged {message.author.mention} for text keywords: {', '.join(sorted(evil))}"
                            )
                        except Exception:
                            pass

                await self.stage_user(message.author, message.channel, message, cfg)
                return

        if "ocr" not in stage_types or not ocr_enabled:
            return

        if not message.attachments:
            return

        max_image_bytes = 100 * 1024 * 1024

        for attachment in message.attachments:
            try:
                if not attachment.content_type or not attachment.content_type.startswith("image"):
                    continue

                if attachment.size and attachment.size > max_image_bytes:
                    continue

                image_bytes = await attachment.read()
                t0 = time.perf_counter()
                text = await self.ocr.extract_text(image_bytes)
                self.metrics.record_ocr(time.perf_counter() - t0)
                evil = self._evil_keywords_from_text(text)

                if len(evil) >= min_keywords:
                    _dbg(
                        f"scam-image hit guild={message.guild.id} channel={message.channel.id} author={message.author.id} evil_count={len(evil)} evil={sorted(evil)}"
                    )
                    try:
                        await message.delete()
                    except Exception:
                        pass

                    log_channel_id = cfg.get("log_channel_id")
                    if log_channel_id:
                        log_channel = message.guild.get_channel(int(log_channel_id))
                        if log_channel:
                            try:
                                prefix = "AutoMod:"
                                if cfg.get("silly_mode"):
                                    prefix = "SillyMod:"
                                await log_channel.send(
                                    f"{prefix} staged {message.author.mention} for scam-image keywords: {', '.join(sorted(evil))}"
                                )
                            except Exception:
                                pass

                    await self.stage_user(message.author, message.channel, message, cfg)
                    break

            except Exception:
                continue


async def setup(bot):
    await bot.add_cog(AutoMod(bot))
