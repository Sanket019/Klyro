import discord
from discord.ext import commands
import sqlite3
from datetime import timedelta

DB_PATH = "bot_data.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT,
            user_id TEXT,
            moderator_id TEXT,
            reason TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()


async def send_response(ctx, embed=None, content=None, ephemeral=False):
    """Universal send — works for both prefix and slash commands."""
    if hasattr(ctx, 'respond'):
        await ctx.respond(content=content, embed=embed, ephemeral=ephemeral)
    else:
        await ctx.send(content=content, embed=embed)


class Moderation(commands.Cog):
    """🔨 Moderation — Keep your server clean and safe."""

    def __init__(self, bot):
        self.bot = bot

    async def log_action(self, guild, action, moderator, target, reason):
        log_channel = discord.utils.get(guild.text_channels, name="mod-logs")
        if log_channel:
            embed = discord.Embed(title=f"🔨 {action}", color=0x9D00FF)
            embed.add_field(name="Target", value=f"{target.mention} (`{target.id}`)", inline=True)
            embed.add_field(name="Moderator", value=moderator.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            await log_channel.send(embed=embed)

    # ── KICK ──────────────────────────────────────────────────────────────────
    async def _kick(self, ctx, member, reason):
        if member == ctx.author:
            return await send_response(ctx, content="❌ You can't kick yourself!", ephemeral=True)
        if member.top_role >= ctx.author.top_role:
            return await send_response(ctx, content="❌ Can't kick someone with equal or higher role!", ephemeral=True)
        try:
            await member.kick(reason=reason)
            embed = discord.Embed(title="👟 Member Kicked", description=f"**{member.display_name}** was kicked.\n**Reason:** {reason}", color=0x9D00FF)
            await send_response(ctx, embed=embed)
            await self.log_action(ctx.guild, "Kick", ctx.author, member, reason)
        except discord.Forbidden:
            await send_response(ctx, content="❌ I don't have permission to kick that member.")

    @commands.command(name="kick", help="Kick a member. e.g. !kick @user spamming")
    @commands.has_permissions(kick_members=True)
    async def kick_prefix(self, ctx, member: discord.Member, *, reason="No reason provided"):
        await self._kick(ctx, member, reason)

    @discord.slash_command(name="kick", description="Kick a member from the server")
    @commands.has_permissions(kick_members=True)
    async def kick_slash(self, ctx, member: discord.Member, reason: str = "No reason provided"):
        await self._kick(ctx, member, reason)

    # ── BAN ───────────────────────────────────────────────────────────────────
    async def _ban(self, ctx, member, reason):
        if member == ctx.author:
            return await send_response(ctx, content="❌ You can't ban yourself!", ephemeral=True)
        if member.top_role >= ctx.author.top_role:
            return await send_response(ctx, content="❌ Can't ban someone with equal or higher role!", ephemeral=True)
        try:
            await member.ban(reason=reason)
            embed = discord.Embed(title="🔨 Member Banned", description=f"**{member.display_name}** was banned.\n**Reason:** {reason}", color=0x9D00FF)
            await send_response(ctx, embed=embed)
            await self.log_action(ctx.guild, "Ban", ctx.author, member, reason)
        except discord.Forbidden:
            await send_response(ctx, content="❌ I don't have permission to ban that member.")

    @commands.command(name="ban", help="Ban a member. e.g. !ban @user rule violation")
    @commands.has_permissions(ban_members=True)
    async def ban_prefix(self, ctx, member: discord.Member, *, reason="No reason provided"):
        await self._ban(ctx, member, reason)

    @discord.slash_command(name="ban", description="Ban a member from the server")
    @commands.has_permissions(ban_members=True)
    async def ban_slash(self, ctx, member: discord.Member, reason: str = "No reason provided"):
        await self._ban(ctx, member, reason)

    # ── MUTE ──────────────────────────────────────────────────────────────────
    async def _mute(self, ctx, member, duration, reason):
        time_map = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}
        unit = duration[-1].lower()
        try:
            amount = int(duration[:-1])
            if unit not in time_map:
                raise ValueError
            delta = timedelta(**{time_map[unit]: amount})
        except (ValueError, KeyError):
            return await send_response(ctx, content="❌ Invalid duration. Use like `10m`, `1h`, `2d`", ephemeral=True)
        try:
            await member.timeout_for(delta, reason=reason)
            embed = discord.Embed(title="🔇 Member Muted", description=f"**{member.display_name}** timed out for **{duration}**.\n**Reason:** {reason}", color=0x9D00FF)
            await send_response(ctx, embed=embed)
            await self.log_action(ctx.guild, f"Mute ({duration})", ctx.author, member, reason)
        except discord.Forbidden:
            await send_response(ctx, content="❌ I don't have permission to timeout that member.")

    @commands.command(name="mute", help="Timeout a member. e.g. !mute @user 10m spamming")
    @commands.has_permissions(moderate_members=True)
    async def mute_prefix(self, ctx, member: discord.Member, duration: str = "10m", *, reason="No reason provided"):
        await self._mute(ctx, member, duration, reason)

    @discord.slash_command(name="mute", description="Timeout a member. Duration: 10m, 1h, 1d")
    @commands.has_permissions(moderate_members=True)
    async def mute_slash(self, ctx, member: discord.Member, duration: str = "10m", reason: str = "No reason provided"):
        await self._mute(ctx, member, duration, reason)

    # ── UNMUTE ────────────────────────────────────────────────────────────────
    async def _unmute(self, ctx, member):
        try:
            await member.remove_timeout()
            embed = discord.Embed(title="🔊 Member Unmuted", description=f"**{member.display_name}**'s timeout has been removed.", color=0x9D00FF)
            await send_response(ctx, embed=embed)
        except discord.Forbidden:
            await send_response(ctx, content="❌ I don't have permission to remove that timeout.")

    @commands.command(name="unmute", help="Remove a member's timeout. e.g. !unmute @user")
    @commands.has_permissions(moderate_members=True)
    async def unmute_prefix(self, ctx, member: discord.Member):
        await self._unmute(ctx, member)

    @discord.slash_command(name="unmute", description="Remove a member's timeout")
    @commands.has_permissions(moderate_members=True)
    async def unmute_slash(self, ctx, member: discord.Member):
        await self._unmute(ctx, member)

    # ── CLEAR ─────────────────────────────────────────────────────────────────
    @commands.command(name="clear", help="Delete messages. e.g. !clear 20")
    @commands.has_permissions(manage_messages=True)
    async def clear_prefix(self, ctx, amount: int = 10):
        if not 1 <= amount <= 100:
            return await ctx.send("❌ Amount must be between 1 and 100.")
        deleted = await ctx.channel.purge(limit=amount + 1)  # +1 to include the command msg
        msg = await ctx.send(f"🗑️ Deleted **{len(deleted) - 1}** messages.")
        await msg.delete(delay=3)

    @discord.slash_command(name="clear", description="Delete recent messages (1-100)")
    @commands.has_permissions(manage_messages=True)
    async def clear_slash(self, ctx, amount: int = 10):
        if not 1 <= amount <= 100:
            return await ctx.respond("❌ Amount must be between 1 and 100.", ephemeral=True)
        await ctx.defer(ephemeral=True)
        deleted = await ctx.channel.purge(limit=amount)
        await ctx.respond(f"🗑️ Deleted **{len(deleted)}** messages.", ephemeral=True)

    # ── WARN ──────────────────────────────────────────────────────────────────
    async def _warn(self, ctx, member, reason):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO warnings (guild_id, user_id, moderator_id, reason) VALUES (?, ?, ?, ?)",
                  (str(ctx.guild.id), str(member.id), str(ctx.author.id), reason))
        conn.commit()
        c.execute("SELECT COUNT(*) FROM warnings WHERE guild_id=? AND user_id=?", (str(ctx.guild.id), str(member.id)))
        total = c.fetchone()[0]
        conn.close()

        embed = discord.Embed(title="⚠️ Member Warned",
                              description=f"**{member.display_name}** warned. Total warnings: **{total}**\n**Reason:** {reason}",
                              color=0x9D00FF)
        await send_response(ctx, embed=embed)
        try:
            await member.send(f"⚠️ You were warned in **{ctx.guild.name}**.\nReason: {reason}\nTotal warnings: {total}")
        except Exception:
            pass
        await self.log_action(ctx.guild, "Warn", ctx.author, member, reason)

    @commands.command(name="warn", help="Warn a member. e.g. !warn @user breaking rules")
    @commands.has_permissions(moderate_members=True)
    async def warn_prefix(self, ctx, member: discord.Member, *, reason="No reason provided"):
        await self._warn(ctx, member, reason)

    @discord.slash_command(name="warn", description="Warn a member and log it")
    @commands.has_permissions(moderate_members=True)
    async def warn_slash(self, ctx, member: discord.Member, reason: str = "No reason provided"):
        await self._warn(ctx, member, reason)

    # ── WARNINGS ──────────────────────────────────────────────────────────────
    async def _warnings(self, ctx, member):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT reason, moderator_id, timestamp FROM warnings WHERE guild_id=? AND user_id=? ORDER BY timestamp DESC LIMIT 10",
                  (str(ctx.guild.id), str(member.id)))
        rows = c.fetchall()
        conn.close()

        if not rows:
            return await send_response(ctx, content=f"✅ **{member.display_name}** has no warnings.")

        embed = discord.Embed(title=f"⚠️ Warnings for {member.display_name}", color=0x9D00FF)
        for i, (reason, mod_id, timestamp) in enumerate(rows, 1):
            embed.add_field(name=f"#{i} — {timestamp[:10]}", value=f"**Reason:** {reason}\n**By:** <@{mod_id}>", inline=False)
        await send_response(ctx, embed=embed)

    @commands.command(name="warnings", help="View warnings for a member. e.g. !warnings @user")
    @commands.has_permissions(moderate_members=True)
    async def warnings_prefix(self, ctx, member: discord.Member):
        await self._warnings(ctx, member)

    @discord.slash_command(name="warnings", description="View all warnings for a member")
    @commands.has_permissions(moderate_members=True)
    async def warnings_slash(self, ctx, member: discord.Member):
        await self._warnings(ctx, member)

    # ── CLEAR WARNINGS ────────────────────────────────────────────────────────
    async def _clearwarnings(self, ctx, member):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM warnings WHERE guild_id=? AND user_id=?", (str(ctx.guild.id), str(member.id)))
        conn.commit()
        conn.close()
        await send_response(ctx, content=f"🗑️ Cleared all warnings for **{member.display_name}**.")

    @commands.command(name="clearwarnings", help="Clear all warnings for a member. e.g. !clearwarnings @user")
    @commands.has_permissions(administrator=True)
    async def clearwarnings_prefix(self, ctx, member: discord.Member):
        await self._clearwarnings(ctx, member)

    @discord.slash_command(name="clearwarnings", description="Clear all warnings for a member")
    @commands.has_permissions(administrator=True)
    async def clearwarnings_slash(self, ctx, member: discord.Member):
        await self._clearwarnings(ctx, member)

    # ── ERROR HANDLER ─────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use that command.")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("❌ Member not found. Make sure you @mention them.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing argument. Use `!help` to see correct usage.")


def setup(bot):
    bot.add_cog(Moderation(bot))
