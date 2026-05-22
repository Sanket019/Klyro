import discord
from discord.ext import commands
import asyncio
from datetime import datetime


async def send_response(ctx, embed=None, content=None, ephemeral=False):
    if hasattr(ctx, 'respond'):
        await ctx.respond(content=content, embed=embed, ephemeral=ephemeral)
    else:
        await ctx.send(content=content, embed=embed)


class Utility(commands.Cog):
    """⚙️ Utility — Reminders, polls, timers, server info and more."""

    def __init__(self, bot):
        self.bot = bot

    def parse_duration(self, duration: str):
        """Returns seconds from a string like 10m, 2h, 30s"""
        time_map = {"s": 1, "m": 60, "h": 3600}
        unit = duration[-1].lower()
        if unit not in time_map:
            raise ValueError("Invalid unit")
        amount = int(duration[:-1])
        return amount * time_map[unit], duration

    # ── PING ──────────────────────────────────────────────────────────────────
    @commands.command(name="ping", help="Check bot latency")
    async def ping_prefix(self, ctx):
        await ctx.send(f"🏓 Pong! Latency: **{round(self.bot.latency * 1000)}ms**")

    @discord.slash_command(name="ping", description="Check bot latency")
    async def ping_slash(self, ctx):
        await ctx.respond(f"🏓 Pong! Latency: **{round(self.bot.latency * 1000)}ms**")

    # ── REMIND ────────────────────────────────────────────────────────────────
    async def _remind(self, ctx, duration: str, message: str):
        try:
            seconds, label = self.parse_duration(duration)
        except (ValueError, IndexError):
            return await send_response(ctx, content="❌ Invalid duration. Use like `30s`, `10m`, `2h`", ephemeral=True)

        await send_response(ctx, content=f"⏰ Got it! I'll remind you about **{message}** in **{duration}**.")
        await asyncio.sleep(seconds)

        embed = discord.Embed(
            title="⏰ Reminder!",
            description=message,
            color=0x9D00FF,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="Your reminder is here!")
        try:
            await ctx.author.send(embed=embed)
        except Exception:
            pass
        await ctx.channel.send(f"🔔 {ctx.author.mention} — reminder: **{message}**", embed=embed)

    @commands.command(name="remind", help="Set a reminder. e.g. !remind 30m Study DSA")
    async def remind_prefix(self, ctx, duration: str, *, message: str):
        await self._remind(ctx, duration, message)

    @discord.slash_command(name="remind", description="Set a reminder! e.g. duration: 30m, message: Study DSA")
    async def remind_slash(self, ctx, duration: str, message: str):
        await self._remind(ctx, duration, message)

    # ── POLL ──────────────────────────────────────────────────────────────────
    async def _poll(self, ctx, question: str, options: list):
        if len(options) < 2 or len(options) > 4:
            return await send_response(ctx, content="❌ Provide 2–4 options separated by `,`\nExample: `!poll Best team?, CSK, MI, RCB`", ephemeral=True)

        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
        
        # Better UI layout for the poll
        description = "\n\n".join(f"{emojis[i]} **{opt}**" for i, opt in enumerate(options))

        embed = discord.Embed(title=f"📊 {question}", description=description, color=0x9D00FF)
        embed.set_footer(text=f"Poll by {ctx.author.display_name} • React to vote!")

        if hasattr(ctx, 'respond'):
            await ctx.respond("📊 Poll created!", ephemeral=True)
            poll_msg = await ctx.channel.send(embed=embed)
        else:
            poll_msg = await ctx.send(embed=embed)

        for i in range(len(options)):
            await poll_msg.add_reaction(emojis[i])

    @commands.command(name="poll", help='Create a poll. e.g. !poll Best team?, CSK, MI, RCB')
    async def poll_prefix(self, ctx, *, query: str):
        parts = [p.strip() for p in query.split(",") if p.strip()]
        if len(parts) < 3:
            return await send_response(ctx, content="❌ Provide a question and 2–4 options separated by `,`\nExample: `!poll Best team?, CSK, MI, RCB`", ephemeral=True)
        question = parts[0]
        options = parts[1:]
        await self._poll(ctx, question, options)

    @discord.slash_command(name="poll", description='Create a poll. Options separated by commas e.g. "CSK, MI, RCB"')
    async def poll_slash(self, ctx, question: str, options: str):
        opts = [o.strip() for o in options.split(",") if o.strip()]
        await self._poll(ctx, question, opts)

    # ── TIMER ─────────────────────────────────────────────────────────────────
    async def _timer(self, ctx, minutes: int, label: str):
        if not 1 <= minutes <= 60:
            return await send_response(ctx, content="❌ Timer must be 1–60 minutes.", ephemeral=True)

        embed = discord.Embed(
            title=f"⏱️ {label}",
            description=f"Timer started for **{minutes} minute(s)**!\nI'll ping you when done.",
            color=0x9D00FF
        )
        await send_response(ctx, embed=embed)
        await asyncio.sleep(minutes * 60)

        done_embed = discord.Embed(
            title=f"✅ {label} — Time's up!",
            description=f"Your **{minutes} minute** timer is done!",
            color=0x9D00FF
        )
        await ctx.channel.send(content=ctx.author.mention, embed=done_embed)

    @commands.command(name="timer", help="Start a countdown. e.g. !timer 25 Pomodoro")
    async def timer_prefix(self, ctx, minutes: int, *, label: str = "Timer"):
        await self._timer(ctx, minutes, label)

    @discord.slash_command(name="timer", description="Start a countdown timer (max 60 minutes)")
    async def timer_slash(self, ctx, minutes: int, label: str = "Timer"):
        await self._timer(ctx, minutes, label)

    # ── SERVERINFO ────────────────────────────────────────────────────────────
    async def _serverinfo(self, ctx):
        guild = ctx.guild
        embed = discord.Embed(title=f"🏠 {guild.name}", color=0x9D00FF, timestamp=datetime.utcnow())
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="👑 Owner", value=guild.owner.mention, inline=True)
        embed.add_field(name="👥 Members", value=str(guild.member_count), inline=True)
        embed.add_field(name="💬 Channels", value=str(len(guild.channels)), inline=True)
        embed.add_field(name="🎭 Roles", value=str(len(guild.roles)), inline=True)
        embed.add_field(name="🌍 Region", value=str(guild.preferred_locale), inline=True)
        embed.add_field(name="📅 Created", value=guild.created_at.strftime("%d %b %Y"), inline=True)
        embed.set_footer(text=f"Server ID: {guild.id}")
        await send_response(ctx, embed=embed)

    @commands.command(name="serverinfo", help="Show server information")
    async def serverinfo_prefix(self, ctx):
        await self._serverinfo(ctx)

    @discord.slash_command(name="serverinfo", description="Show server information")
    async def serverinfo_slash(self, ctx):
        await self._serverinfo(ctx)

    # ── USERINFO ──────────────────────────────────────────────────────────────
    async def _userinfo(self, ctx, member):
        if member is None:
            member = ctx.author
        roles = [r.mention for r in member.roles if r.name != "@everyone"]
        embed = discord.Embed(title=f"👤 {member.display_name}", color=0x9D00FF, timestamp=datetime.utcnow())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Username", value=str(member), inline=True)
        embed.add_field(name="ID", value=str(member.id), inline=True)
        embed.add_field(name="Bot?", value="✅ Yes" if member.bot else "❌ No", inline=True)
        embed.add_field(name="📅 Joined Server", value=member.joined_at.strftime("%d %b %Y"), inline=True)
        embed.add_field(name="📅 Account Created", value=member.created_at.strftime("%d %b %Y"), inline=True)
        embed.add_field(name=f"🎭 Roles ({len(roles)})", value=" ".join(roles) if roles else "None", inline=False)
        await send_response(ctx, embed=embed)

    @commands.command(name="userinfo", help="Show user info. e.g. !userinfo @user")
    async def userinfo_prefix(self, ctx, member: discord.Member = None):
        await self._userinfo(ctx, member)

    @discord.slash_command(name="userinfo", description="Show user info (leave blank for yourself)")
    async def userinfo_slash(self, ctx, member: discord.Member = None):
        await self._userinfo(ctx, member)


def setup(bot):
    bot.add_cog(Utility(bot))
