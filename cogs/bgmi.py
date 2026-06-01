import discord
from discord.ext import commands
from discord import Member
from datetime import datetime, timezone
import asyncio
import database as db

# ── Change these to match your server ─────────────────────
ADMIN_ROLE = "Scrim Manager"
EMBED_COLOR = 0xa855f7
ERROR_COLOR = 0xff4757
SUCCESS_COLOR = 0x00ff88

# Medal emojis for top 3
MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}

# ══════════════════════════════════════════════════════════
#   HELPER — Format table rows as monospace text
# ══════════════════════════════════════════════════════════

def make_row(rank: int, ign: str, matches: int, kills: int, avg: float) -> str:
    medal = MEDALS.get(rank, f"`#{rank:>2}`")
    ign_trunc = ign[:14].ljust(14)
    return f"{medal} `{ign_trunc}` `M:{matches:>3}` `K:{kills:>4}` `AVG:{avg:>5.2f}`"


# ══════════════════════════════════════════════════════════
#   PERMISSION CHECK
# ══════════════════════════════════════════════════════════

def is_admin_check():
    async def predicate(ctx: commands.Context):
        if ctx.author.guild_permissions.administrator:
            return True
        admin_role_id = db.get_admin_role(str(ctx.guild.id))
        if admin_role_id:
            if any(r.id == admin_role_id for r in ctx.author.roles):
                return True
            raise commands.MissingRole(admin_role_id)
        else:
            if any(r.name == ADMIN_ROLE for r in ctx.author.roles):
                return True
            raise commands.MissingRole(ADMIN_ROLE)
    return commands.check(predicate)


# ══════════════════════════════════════════════════════════
#   COG
# ══════════════════════════════════════════════════════════

class BGMICog(commands.Cog, name="BGMI"):
    """BGMI Clan Leaderboard System for Klyro Bot"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ══════════════════════════════════════════════════════
    #   !addmatchstats @p1 k1 @p2 k2 ...
    # ══════════════════════════════════════════════════════
    @commands.command(name="addmatchstats")
    @is_admin_check()
    async def add_match_stats(self, ctx: commands.Context, *args):
        if len(args) == 0 or len(args) % 2 != 0:
            embed = discord.Embed(
                title="❌ Invalid Usage",
                description=(
                    "**Usage:** `!addmatchstats @player1 kills1 @player2 kills2 ...`\n"
                    "Example: `!addmatchstats @Starc 8 @Rabada 12 @Ponting 5`"
                ),
                color=ERROR_COLOR
            )
            return await ctx.send(embed=embed)

        player_kills = []
        errors = []

        for i in range(0, len(args), 2):
            raw_mention = args[i]
            raw_kills   = args[i + 1]
            try:
                member = await commands.MemberConverter().convert(ctx, raw_mention)
            except commands.BadArgument:
                errors.append(f"• Could not find player: `{raw_mention}`")
                continue
            try:
                kills = int(raw_kills)
                if kills < 0:
                    raise ValueError
            except ValueError:
                errors.append(f"• Invalid kills value `{raw_kills}` for {member.display_name}")
                continue
            player_kills.append((str(member.id), kills))

        if not player_kills:
            return await ctx.send(embed=discord.Embed(
                description="❌ No valid player-kill pairs found.",
                color=ERROR_COLOR
            ))

        # Write to DB — stats + match history
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        not_found = db.add_match_stats(str(ctx.guild.id), player_kills)
        db.log_match_history(str(ctx.guild.id), player_kills, today)

        embed = discord.Embed(title="✅ Stats Successfully Entered Boss", color=SUCCESS_COLOR)

        logged_lines = []
        for discord_id, kills in player_kills:
            if discord_id not in not_found:
                player = db.get_player(str(ctx.guild.id), discord_id)
                ign = player["bgmi_ign"] if player else f"<@{discord_id}>"
                logged_lines.append(f"• **{ign}** — {kills} kills")

        if logged_lines:
            embed.add_field(
                name=f"📊 Logged {len(logged_lines)} player(s)",
                value="\n".join(logged_lines),
                inline=False
            )
        if not_found:
            embed.add_field(
                name="⚠️ Not in database (skipped)",
                value="\n".join([f"• <@{uid}>" for uid in not_found])
                      + "\n*Use `!manageteam add @player IGN` to register them first.*",
                inline=False
            )
        if errors:
            embed.add_field(name="❌ Errors", value="\n".join(errors), inline=False)

        embed.set_footer(text="Both Weekly & Overall stats updated.")
        await ctx.send(embed=embed)

    # ══════════════════════════════════════════════════════
    #   !resetweekly
    # ══════════════════════════════════════════════════════
    @commands.command(name="resetweekly")
    @is_admin_check()
    async def reset_weekly(self, ctx: commands.Context):
        confirm_embed = discord.Embed(
            title="⚠️ Confirm Weekly Reset",
            description=(
                "This will **zero out ALL weekly stats** for every player.\n"
                "Overall stats will **not** be affected.\n\n"
                "React with ✅ to confirm or ❌ to cancel."
            ),
            color=0x39ff14
        )
        msg = await ctx.send(embed=confirm_embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
        except TimeoutError:
            await msg.edit(embed=discord.Embed(description="⏰ Reset cancelled — timed out.", color=ERROR_COLOR))
            return

        if str(reaction.emoji) == "✅":
            db.reset_weekly(str(ctx.guild.id))
            embed = discord.Embed(
                title="🔄 Weekly Stats Reset",
                description="All weekly kills and matches have been wiped to **0**.\nOverall stats remain unchanged.",
                color=SUCCESS_COLOR
            )
            embed.set_footer(text=f"Reset by {ctx.author.display_name}")
            await msg.edit(embed=embed)
        else:
            await msg.edit(embed=discord.Embed(description="❌ Weekly reset cancelled.", color=ERROR_COLOR))

    # ══════════════════════════════════════════════════════
    #   !resetoverall
    # ══════════════════════════════════════════════════════
    @commands.command(name="resetoverall")
    @is_admin_check()
    async def reset_overall(self, ctx: commands.Context):
        """Wipe all lifetime stats and match history. Strictly Admin only."""
        confirm_embed = discord.Embed(
            title="⚠️ Confirm Overall Reset",
            description=(
                "**This will permanently delete:**\n"
                "• All **lifetime kills & matches** for every player\n"
                "• Entire **match history** log\n\n"
                "Weekly stats will **not** be affected.\n"
                "**This cannot be undone.**\n\n"
                "React with ✅ to confirm or ❌ to cancel."
            ),
            color=0xff4757
        )
        msg = await ctx.send(embed=confirm_embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
        except TimeoutError:
            await msg.edit(embed=discord.Embed(
                description="⏰ Reset cancelled — timed out.", color=ERROR_COLOR))
            return

        if str(reaction.emoji) == "✅":
            db.reset_overall(str(ctx.guild.id))
            embed = discord.Embed(
                title="🗑️ Overall Stats Reset",
                description=(
                    "All **lifetime kills, matches** and **match history** have been permanently deleted.\n"
                    "Weekly stats remain unchanged."
                ),
                color=SUCCESS_COLOR
            )
            embed.set_footer(text=f"Reset by {ctx.author.display_name}")
            await msg.edit(embed=embed)
        else:
            await msg.edit(embed=discord.Embed(
                description="❌ Overall reset cancelled.", color=ERROR_COLOR))

    # ══════════════════════════════════════════════════════
    #   !manageteam [action] @player [value]
    # ══════════════════════════════════════════════════════
    @commands.command(name="manageteam")
    @is_admin_check()
    async def manage_team(self, ctx: commands.Context, action: str, member: Member, *, value: str = None):
        action = action.lower()
        discord_id = str(member.id)

        if action == "add":
            if not value:
                return await ctx.send(embed=discord.Embed(
                    description="❌ Usage: `!manageteam add @player IGN [TeamName]`", color=ERROR_COLOR))
            parts = value.split()
            ign  = parts[0]
            team = " ".join(parts[1:]) if len(parts) > 1 else "Bench"
            success = db.add_player(str(ctx.guild.id), discord_id, ign, team)
            if success:
                embed = discord.Embed(title="✅ Player Added", color=SUCCESS_COLOR)
                embed.add_field(name="Discord", value=member.mention, inline=True)
                embed.add_field(name="IGN",     value=ign,            inline=True)
                embed.add_field(name="Team",    value=team,           inline=True)
            else:
                embed = discord.Embed(description=f"❌ {member.mention} is already registered.", color=ERROR_COLOR)
            await ctx.send(embed=embed)

        elif action == "remove":
            success = db.remove_player(str(ctx.guild.id), discord_id)
            if success:
                embed = discord.Embed(
                    title="🗑️ Player Removed",
                    description=f"{member.mention} and all their stats have been deleted.",
                    color=SUCCESS_COLOR)
            else:
                embed = discord.Embed(description=f"❌ {member.mention} is not in the database.", color=ERROR_COLOR)
            await ctx.send(embed=embed)

        elif action == "update_ign":
            if not value:
                return await ctx.send(embed=discord.Embed(
                    description="❌ Usage: `!manageteam update_ign @player NewIGN`", color=ERROR_COLOR))
            success = db.update_ign(str(ctx.guild.id), discord_id, value.strip())
            if success:
                embed = discord.Embed(
                    title="✏️ IGN Updated",
                    description=f"{member.mention}'s IGN → **{value.strip()}**",
                    color=SUCCESS_COLOR)
            else:
                embed = discord.Embed(
                    description=f"❌ {member.mention} not found. Register first with `!manageteam add`.",
                    color=ERROR_COLOR)
            await ctx.send(embed=embed)

        elif action == "set_team":
            if not value:
                return await ctx.send(embed=discord.Embed(
                    description="❌ Usage: `!manageteam set_team @player TeamName`", color=ERROR_COLOR))
            success = db.set_team(str(ctx.guild.id), discord_id, value.strip())
            if success:
                embed = discord.Embed(
                    title="🏷️ Team Updated",
                    description=f"{member.mention} → **{value.strip()}**",
                    color=SUCCESS_COLOR)
            else:
                embed = discord.Embed(description=f"❌ {member.mention} not found.", color=ERROR_COLOR)
            await ctx.send(embed=embed)

        else:
            embed = discord.Embed(
                title="❌ Unknown Action",
                description=(
                    "Valid actions:\n"
                    "• `add @player IGN [Team]`\n"
                    "• `remove @player`\n"
                    "• `update_ign @player NewIGN`\n"
                    "• `set_team @player TeamName`"
                ),
                color=ERROR_COLOR)
            await ctx.send(embed=embed)

    # ══════════════════════════════════════════════════════
    #   !leaderboard [weekly|overall]
    # ══════════════════════════════════════════════════════
    @commands.command(name="leaderboard", aliases=["lb"])
    async def leaderboard(self, ctx: commands.Context, mode: str = "weekly"):
        mode = mode.lower()
        if mode == "weekly":
            await self._send_weekly_leaderboard(ctx)
        elif mode in ("lifetime", "overall", "all"):
            await self._send_lifetime_leaderboard(ctx)
        else:
            await ctx.send(embed=discord.Embed(
                description="❌ Usage: `!leaderboard weekly` or `!leaderboard overall`",
                color=ERROR_COLOR))

    async def _send_weekly_leaderboard(self, ctx: commands.Context):
        teams = db.get_weekly_leaderboard(str(ctx.guild.id))
        if not teams:
            return await ctx.send(embed=discord.Embed(
                description="📭 No players in the database.", color=ERROR_COLOR))

        embed = discord.Embed(title="🎮 WoW Weekly Leaderboard", color=EMBED_COLOR)

        for team_name, players in teams.items():
            lines = []
            team_rank = 1
            for p in players:
                medal = MEDALS.get(team_rank, f"`#{team_rank}`")
                ign   = p["ign"][:14]
                line  = f"{medal} `{ign}  ` — `M: {p['matches']} `  `K: {p['kills']} `  `AVG: {p['avg']:.2f} `"
                lines.append(line)
                lines.append("")
                team_rank += 1

            team_icon = "🔴" if "alpha" in team_name.lower() else "🔵" if "bravo" in team_name.lower() else "⚪"
            embed.add_field(
                name=f"{team_icon} **{team_name}**",
                value="\n".join(lines).rstrip() if lines else "*No stats yet*",
                inline=False
            )

        total_matches = sum(p["matches"] for pl in teams.values() for p in pl)
        total_players = sum(len(v) for v in teams.values())
        embed.set_footer(
            text=f"👥 {total_players} players  •  Total matches tracked: {total_matches // max(total_players, 1)}",
            icon_url="https://sm.ign.com/ign_in/screenshot/default/battlegrounds-mobile-india-pre-register-battlegrounds-mobile_dvq9.png"
        )
        embed.timestamp = ctx.message.created_at
        await ctx.send(embed=embed)

    async def _send_lifetime_leaderboard(self, ctx: commands.Context):
        players = db.get_lifetime_leaderboard(str(ctx.guild.id))
        if not players:
            return await ctx.send(embed=discord.Embed(
                description="📭 No players in the database.", color=ERROR_COLOR))

        embed = discord.Embed(title="👑 WoW Overall Leaderboard", color=0x39ff14)

        lines = []
        for rank, p in enumerate(players, start=1):
            medal = MEDALS.get(rank, f"`#{rank}`")
            ign   = p["ign"][:14]
            line  = f"{medal} `{ign}  ` — `M: {p['matches']} `  `K: {p['kills']} `  `AVG: {p['avg']:.2f} `"
            lines.append(line)
            lines.append("")
            if len(lines) >= 20:
                embed.add_field(name="\u200b", value="\n".join(lines).rstrip(), inline=False)
                lines = []
        if lines:
            embed.add_field(name="\u200b", value="\n".join(lines).rstrip(), inline=False)

        embed.set_footer(
            text=f"👥 {len(players)} players",
            icon_url="https://sm.ign.com/ign_in/screenshot/default/battlegrounds-mobile-india-pre-register-battlegrounds-mobile_dvq9.png"
        )
        embed.timestamp = ctx.message.created_at
        await ctx.send(embed=embed)

    # ══════════════════════════════════════════════════════
    #   !assign wow manager @role
    # ══════════════════════════════════════════════════════
    @commands.command(name="assign")
    @commands.has_permissions(administrator=True)
    async def assign_role(self, ctx, module: str, role_type: str, role: discord.Role):
        if module.lower() == "wow" and role_type.lower() == "manager":
            db.set_admin_role(str(ctx.guild.id), role.id)
            embed = discord.Embed(
                description=f"✅ Wow Manager role has been successfully set to {role.mention}",
                color=SUCCESS_COLOR
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("Usage: `!assign wow manager @role`")

    # ══════════════════════════════════════════════════════
    #   NEW: !matchhistory [n]
    # ══════════════════════════════════════════════════════
    @commands.command(name="matchhistory", aliases=["mh"])
    async def match_history(self, ctx: commands.Context, limit: int = 5):
        """Show last N match sessions. Usage: !matchhistory [5]"""
        if limit < 1 or limit > 20:
            limit = 5

        sessions = db.get_match_history(str(ctx.guild.id), limit)
        if not sessions:
            return await ctx.send(embed=discord.Embed(
                description="📭 No match history found.", color=ERROR_COLOR))

        embed = discord.Embed(
            title="📜 Match History",
            description=f"Last **{len(sessions)}** match session(s)",
            color=EMBED_COLOR
        )

        for i, session in enumerate(sessions, start=1):
            lines = []
            for rank, p in enumerate(session['players'], start=1):
                medal = MEDALS.get(rank, f"`#{rank}`")
                lines.append(f"{medal} **{p['ign']}** — `K: {p['kills']}`")

            embed.add_field(
                name=f"Match {i}  •  {session['logged_at']}",
                value="\n".join(lines) if lines else "*No data*",
                inline=False
            )

        embed.set_footer(text="Klyro Bot • WoW Match History")
        embed.timestamp = ctx.message.created_at
        await ctx.send(embed=embed)

    # ══════════════════════════════════════════════════════
    #   NEW: !teamstats
    # ══════════════════════════════════════════════════════
    @commands.command(name="teamstats", aliases=["tvt"])
    async def team_stats(self, ctx: commands.Context):
        """Team vs Team weekly scoreboard."""
        teams = db.get_team_stats(str(ctx.guild.id))
        if not teams:
            return await ctx.send(embed=discord.Embed(
                description="📭 No team data found.", color=ERROR_COLOR))

        embed = discord.Embed(
            title="⚔️ Team vs Team — Weekly",
            description="Comparing all teams by weekly performance",
            color=EMBED_COLOR
        )

        TEAM_ICONS = ["🔴", "🔵", "🟢", "🟡"]
        for i, team in enumerate(teams):
            icon = TEAM_ICONS[i] if i < len(TEAM_ICONS) else "⚪"
            rank_label = "🏆 Leading" if i == 0 else f"#{i+1}"
            embed.add_field(
                name=f"{icon} {team['team']}  —  {rank_label}",
                value=(
                    f"`Total Matches:` **{team['matches']}**\n"
                    f"`Total Kills  :` **{team['kills']}**\n"
                    f"`Avg Kills/M  :` **{team['avg']}**\n"
                    f"`Players      :` **{team['players']}**"
                ),
                inline=True
            )

        if len(teams) == 2:
            diff = abs(teams[0]['kills'] - teams[1]['kills'])
            leader = teams[0]['team']
            embed.add_field(
                name="\u200b",
                value=f"**{leader}** leads by **{diff}** kills this week",
                inline=False
            )

        embed.set_footer(text="Klyro Bot • Weekly Team Standings")
        embed.timestamp = ctx.message.created_at
        await ctx.send(embed=embed)

    # ══════════════════════════════════════════════════════
    #   NEW: !stats @player
    # ══════════════════════════════════════════════════════
    @commands.command(name="stats")
    async def player_stats(self, ctx: commands.Context, member: Member = None):
        """Personal stats card. Usage: !stats @player or !stats (for yourself)"""
        if member is None:
            member = ctx.author

        stats = db.get_personal_stats(str(ctx.guild.id), str(member.id))
        if not stats:
            return await ctx.send(embed=discord.Embed(
                description=f"❌ {member.mention} is not registered in the database.",
                color=ERROR_COLOR))

        career_matches = stats.get('lifetime_matches', 0)
        career_kills = stats.get('lifetime_kills', 0)
        career_avg = round(career_kills / career_matches, 1) if career_matches > 0 else 0.0
        
        if career_matches == 0:
            category = "Did not play"
        elif career_avg < 10:
            category = "🤡 Jhatula Player"
        elif career_avg < 14:
            category = "🔥 Emerging Player"
        elif career_avg < 20:
            category = "💎 Elite Player"
        else:
            category = "👑 Jonathan ka Left Tatta"

        embed = discord.Embed(
            title=f"📊 {stats['ign']}  —  Stats Card",
            description=f"### {category}",
            color=0x39ff14
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        embed.add_field(name="Team",          value=f"`{stats['team']}`",           inline=True)
        rank_display = f"`#{stats['lifetime_rank']}`" if stats['lifetime_kills'] > 0 else "`--`"
        embed.add_field(name="Career Rank",   value=rank_display, inline=True)
        embed.add_field(name="Best Match",    value=f"`{stats['best_match']} kills`", inline=True)

        embed.add_field(
            name="📅 This Week",
            value=(
                f"`Matches :` **{stats['weekly_matches']}**\n"
                f"`Kills   :` **{stats['weekly_kills']}**\n"
                f"`AVG     :` **{stats['weekly_avg']}**"
            ),
            inline=True
        )
        embed.add_field(
            name="🏆 Career",
            value=(
                f"`Matches :` **{stats['lifetime_matches']}**\n"
                f"`Kills   :` **{stats['lifetime_kills']}**\n"
                f"`AVG     :` **{stats['lifetime_avg']}**"
            ),
            inline=True
        )

        embed.set_footer(
            text="Klyro Bot • Player Stats",
            icon_url="https://sm.ign.com/ign_in/screenshot/default/battlegrounds-mobile-india-pre-register-battlegrounds-mobile_dvq9.png"
        )
        embed.timestamp = ctx.message.created_at
        await ctx.send(embed=embed)

    # ══════════════════════════════════════════════════════
    #   NEW: !weekwinner
    # ══════════════════════════════════════════════════════
    @commands.command(name="weekwinner", aliases=["ww"])
    async def week_winner(self, ctx: commands.Context):
        """Crown the weekly top killer. Run before !resetweekly."""
        winner = db.get_weekly_winner(str(ctx.guild.id))
        if not winner:
            return await ctx.send(embed=discord.Embed(
                description="📭 No weekly data found yet.", color=ERROR_COLOR))

        embed = discord.Embed(
            title="🏆 Weekly Winner",
            description=f"This week's top performer is...",
            color=0x39ff14
        )

        user_id = int(winner['discord_id'])
        user = self.bot.get_user(user_id)
        if not user:
            try:
                user = await self.bot.fetch_user(user_id)
            except discord.NotFound:
                user = None

        if user:
            embed.set_thumbnail(url=user.display_avatar.url)

        embed.add_field(name="\u200b", value=(
            f"# 🥇  {winner['ign']}\n"
            f"**Team:** {winner['team']}\n\n"
            f"`M: {winner['matches']} `  `K: {winner['kills']} `  `AVG: {winner['avg']}`"
        ), inline=False)
        embed.set_footer(text="Klyro Bot • Weekly Winner  |  Run !resetweekly to start a new week")
        embed.timestamp = ctx.message.created_at
        await ctx.send(embed=embed)

        await asyncio.sleep(10)
        if str(ctx.author.id) == str(winner['discord_id']):
            await ctx.send(f"{ctx.author.mention} Practice like you have never won and play like you have never lost 🫡.")
        else:
            await ctx.send(f"{ctx.author.mention} BSDK tere liye sapna hai ye Jhat ke baal 😂 mdc muh me lele ab {winner['ign']} ka.")

    # ══════════════════════════════════════════════════════
    #   NEW: !today_mvp  &  !today_summary
    # ══════════════════════════════════════════════════════
    @commands.command(name="today_mvp")
    async def today_mvp(self, ctx: commands.Context, date: str = None):
        """MVP for today (or a specific date). Usage: !today_mvp [YYYY-MM-DD]"""
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        else:
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                return await ctx.send(embed=discord.Embed(
                    description="❌ Invalid format. Use `!today_mvp YYYY-MM-DD`",
                    color=ERROR_COLOR))

        mvp = db.get_daily_mvp(str(ctx.guild.id), date)
        if not mvp:
            return await ctx.send(embed=discord.Embed(
                description=f"📭 No match data found for **{date}**.", color=ERROR_COLOR))

        display_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d %B %Y")
        embed = discord.Embed(
            title=f"🏆 MVP — {display_date}",
            color=0x39ff14
        )

        user_id = int(mvp['discord_id'])
        user = self.bot.get_user(user_id)
        if not user:
            try:
                user = await self.bot.fetch_user(user_id)
            except discord.NotFound:
                user = None

        if user:
            embed.set_thumbnail(url=user.display_avatar.url)

        embed.add_field(name="\u200b", value=(
            f"# 🥇  {mvp['ign']}\n"
            f"**Team:** {mvp['team']}\n\n"
            f"`M: {mvp['matches']} `  `K: {mvp['kills']} `"
        ), inline=False)
        embed.set_footer(
            text=f"Date: {date}  •  Klyro Bot",
            icon_url="https://sm.ign.com/ign_in/screenshot/default/battlegrounds-mobile-india-pre-register-battlegrounds-mobile_dvq9.png"
        )
        embed.timestamp = ctx.message.created_at
        await ctx.send(embed=embed)

        await asyncio.sleep(10)
        if str(ctx.author.id) == str(mvp['discord_id']):
            await ctx.send(f"{ctx.author.mention} Aaj toh {ctx.author.display_name} ne maa hi chod di.")
        else:
            await ctx.send(f"{ctx.author.mention} kya re LODE {ctx.author.display_name} apna naam dhund rha tha kya grind kar bkl 😂.")

    @commands.command(name="today_summary")
    async def today_summary(self, ctx: commands.Context, date: str = None):
        """Full kill summary for today (or a specific date). Usage: !today_summary [YYYY-MM-DD]"""
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        else:
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                return await ctx.send(embed=discord.Embed(
                    description="❌ Invalid format. Use `!today_summary YYYY-MM-DD`",
                    color=ERROR_COLOR))

        summary = db.get_daily_summary(str(ctx.guild.id), date)
        if not summary:
            return await ctx.send(embed=discord.Embed(
                description=f"📭 No match data found for **{date}**.", color=ERROR_COLOR))

        display_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d %B %Y")
        embed = discord.Embed(
            title=f"📊 Day Summary — {display_date}",
            color=EMBED_COLOR
        )

        lines = []
        for rank, p in enumerate(summary, start=1):
            medal = MEDALS.get(rank, f"`#{rank}`")
            lines.append(f"{medal} **{p['ign']}** — `M: {p['matches']} `  `K: {p['kills']} `")
            lines.append("")

        embed.add_field(name="\u200b", value="\n".join(lines).rstrip(), inline=False)
        embed.set_footer(
            text=f"Date: {date}  •  Klyro Bot",
            icon_url="https://sm.ign.com/ign_in/screenshot/default/battlegrounds-mobile-india-pre-register-battlegrounds-mobile_dvq9.png"
        )
        embed.timestamp = ctx.message.created_at
        await ctx.send(embed=embed)

    # ══════════════════════════════════════════════════════
    #   !bgmihelp
    # ══════════════════════════════════════════════════════
    @commands.command(name="bgmihelp")
    async def bgmi_help(self, ctx: commands.Context):
        p = ctx.prefix
        embed = discord.Embed(title="🎮 WoW Bot — Command Reference", color=EMBED_COLOR)
        embed.add_field(
            name="📊 Leaderboards (Everyone)",
            value=(
                f"`{p}leaderboard weekly` — Weekly stats grouped by team\n"
                f"`{p}leaderboard overall` — All-time Kills \n"
                f"`{p}lb` — Shortcut for leaderboard"
            ),
            inline=False
        )
        embed.add_field(
            name="📈 Stats Commands (Everyone)",
            value=(
                f"`{p}stats @player` — Personal stats card\n"
                f"`{p}teamstats` — Team vs Team weekly scoreboard\n"
                f"`{p}tvt` — Shortcut for teamstats\n"
                f"`{p}weekwinner` — Crown this week's top killer\n"
                f"`{p}today_mvp` — MVP of today\n"
                f"`{p}today_summary` — Full kill summary for today\n"
                f"`{p}matchhistory [n]` — Last N match sessions (default 5)\n"
                f"`{p}mh` — Shortcut for match history\n"
                f"`{p}team` — View today's active playing 5 for all teams"
            ),
            inline=False
        )
        embed.add_field(
            name=f"⚙️ Admin Commands (`{ADMIN_ROLE}` only)",
            value=(
                f"`{p}assign wow manager @role` — Assign manager role (Admin only)\n"
                f"`{p}addmatchstats @p1 k1 @p2 k2 ...` — Enter match kills\n"
                f"`{p}manageteam add @p IGN [Team]` — Register player\n"
                f"`{p}manageteam remove @p` — Delete player\n"
                f"`{p}manageteam update_ign @p NewIGN` — Update IGN\n"
                f"`{p}manageteam set_team @p TeamName` — Move to team\n"
                f"`{p}playing TeamName @p1 @p2 @p3 @p4 @p5` — Set playing 5 lineup"
            ),
            inline=False
        )
        embed.add_field(
            name="📝 Team Names & Lineups",
            value=(
                "Use exact team names like `Team Alpha`, `Team Bravo`, or `Bench`.\n"
                f"Admins: use `{p}playing` to lock in the 5 playing members for a team.\n"
                f"Everyone: use `{p}team` to view the merged lineups for all teams."
            ),
            inline=False
        )
        embed.add_field(
            name="⚠️ Danger Zone (System & Resets)",
            value=(
                "`!resetweekly` — Resets weekly stats (with confirmation)\n"
                "`!resetoverall` — Resets lifetime stats + match history (with confirmation)\n"
                "`!dbstatus` — Check database connection status (Admin only)"
            ),
            inline=False
        )
        embed.set_footer(text="Klyro Bot • BGMI Module")
        await ctx.send(embed=embed)

    # ══════════════════════════════════════════════════════
    #   !playing
    # ══════════════════════════════════════════════════════
    @commands.command(name="playing")
    async def set_playing(self, ctx: commands.Context, team_name: str, p1: Member, p2: Member, p3: Member, p4: Member, p5: Member):
        if not await self.check_admin(ctx): return
        
        discord_ids = [p1.id, p2.id, p3.id, p4.id, p5.id]
        db.set_playing_lineup(str(ctx.guild.id), team_name, discord_ids)
        
        embed = discord.Embed(
            title="✅ Playing 5 Lineup Set",
            description=f"Successfully locked in the playing 5 for **{team_name}**.",
            color=EMBED_COLOR
        )
        embed.add_field(name="Players", value=f"{p1.mention} {p2.mention} {p3.mention} {p4.mention} {p5.mention}")
        await ctx.send(embed=embed)

    @set_playing.error
    async def set_playing_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ **Usage:** `{ctx.prefix}playing \"Team Name\" @p1 @p2 @p3 @p4 @p5`\nYou must mention exactly 5 players.",)

    # ══════════════════════════════════════════════════════
    #   !team
    # ══════════════════════════════════════════════════════
    @commands.command(name="team")
    async def view_teams(self, ctx: commands.Context):
        lineups = db.get_all_playing_lineups(str(ctx.guild.id))
        
        if not lineups:
            embed = discord.Embed(
                title="👥 Today's Playing Lineups",
                description="No playing lineups have been set for today yet.",
                color=EMBED_COLOR
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="👥 Today's Playing Lineups",
            description="Active 5-man rosters for today's matches.",
            color=EMBED_COLOR
        )
        
        for team, players in lineups.items():
            player_list = "\n".join([f"• `{p['ign']}` (<@{p['discord_id']}>)" for p in players])
            embed.add_field(name=team, value=player_list, inline=True)
            
        await ctx.send(embed=embed)

    # ══════════════════════════════════════════════════════
    #   !dbstatus
    # ══════════════════════════════════════════════════════
    @commands.command(name="dbstatus")
    @commands.has_permissions(administrator=True)
    async def db_status(self, ctx: commands.Context):
        import os
        url = os.environ.get("DATABASE_URL")
        if not url:
            db_type = "Fallback Neon Postgres (Hardcoded)"
            masked_url = "Using default Neon URL"
        else:
            db_type = "Custom Environment Database"
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                masked_url = f"{parsed.scheme}://{parsed.username}:******@{parsed.hostname}{parsed.path}"
            except Exception:
                masked_url = "Invalid/Error parsing URL"

        connected = False
        error_msg = None
        try:
            with db.DBConnection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                connected = True
        except Exception as e:
            error_msg = str(e)

        embed = discord.Embed(
            title="🗄️ Database Status",
            color=SUCCESS_COLOR if connected else ERROR_COLOR
        )
        embed.add_field(name="Connection Status", value="🟢 Connected" if connected else f"🔴 Failed: {error_msg}", inline=False)
        embed.add_field(name="Database Configuration", value=db_type, inline=False)
        embed.add_field(name="Database URL (Masked)", value=f"`{masked_url}`", inline=False)

        if connected:
            try:
                with db.DBConnection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM players")
                    players_count = cursor.fetchone()[0]
                    cursor.execute("SELECT COUNT(*) FROM config")
                    config_count = cursor.fetchone()[0]
                embed.add_field(name="Stats", value=f"• Registered Players: {players_count}\n• Config Key-Values: {config_count}", inline=False)
            except Exception as e:
                embed.add_field(name="Stats Error", value=str(e), inline=False)

        await ctx.send(embed=embed)

    # ── Error handlers ───────────────────────────────────
    @bgmi_help.error
    @add_match_stats.error
    @reset_weekly.error
    @reset_overall.error
    @manage_team.error
    @assign_role.error
    @db_status.error
    async def bgmi_admin_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(embed=discord.Embed(
                description="❌ You need Administrator permissions to use this command!",
                color=ERROR_COLOR), delete_after=5.0)
        elif isinstance(error, (commands.MissingRole, commands.CheckAnyFailure)):
            admin_role_id = db.get_admin_role(str(ctx.guild.id))
            role_mention = f"<@&{admin_role_id}>" if admin_role_id else f"`{ADMIN_ROLE}`"
            await ctx.send(embed=discord.Embed(
                description=f"❌ You need the {role_mention} role (or Administrator) to use this command!",
                color=ERROR_COLOR), delete_after=5.0)
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(embed=discord.Embed(
                description="❌ Could not find that member. Make sure to ping them correctly.\n\nType `!bgmihelp` for a list of valid commands.",
                color=ERROR_COLOR), delete_after=5.0)
        elif isinstance(error, commands.RoleNotFound):
            await ctx.send(embed=discord.Embed(
                description="❌ Could not find that role. Make sure to ping it correctly.\n\nType `!bgmihelp` for a list of valid commands.",
                color=ERROR_COLOR), delete_after=5.0)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=discord.Embed(
                description=f"❌ Missing required argument: `{error.param.name}`\n\nType `!bgmihelp` for a list of valid commands.",
                color=ERROR_COLOR), delete_after=5.0)
        elif isinstance(error, commands.BadArgument):
            await ctx.send(embed=discord.Embed(
                description=f"❌ Invalid argument provided: {error}\n\nType `!bgmihelp` for a list of valid commands.",
                color=ERROR_COLOR), delete_after=5.0)
        elif isinstance(error, commands.CommandNotFound):
            pass # Ignore command not found since other cogs handle it
        else:
            await ctx.send(embed=discord.Embed(
                description=f"❌ An error occurred: {str(error)}\n\nType `!bgmihelp` for a list of valid commands.",
                color=ERROR_COLOR), delete_after=5.0)


# ── Cog loader ────────────────────────────────────────────
def setup(bot):
    bot.add_cog(BGMICog(bot))