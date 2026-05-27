import discord
from discord.ext import commands
from discord import Member
import database as db

# ── Change these to match your server ─────────────────────
ADMIN_ROLE = "Scrim Manager"   # Role name that can use admin commands
EMBED_COLOR = 0xa855f7         # Neon purple — matches Klyro theme
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
#   COG
# ══════════════════════════════════════════════════════════

def is_admin_check():
    async def predicate(ctx: commands.Context):
        if ctx.author.guild_permissions.administrator:
            return True
        admin_role_id = db.get_admin_role()
        if admin_role_id:
            if any(r.id == admin_role_id for r in ctx.author.roles):
                return True
            raise commands.MissingRole(admin_role_id)
        else:
            if any(r.name == ADMIN_ROLE for r in ctx.author.roles):
                return True
            raise commands.MissingRole(ADMIN_ROLE)
    return commands.check(predicate)

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
        """
        Log match stats for multiple players at once.
        Usage: !addmatchstats @player1 kills1 @player2 kills2 ...
        """
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

        # Parse pairs: (member, kills)
        for i in range(0, len(args), 2):
            raw_mention = args[i]
            raw_kills   = args[i + 1]

            # Resolve member
            try:
                # Try to convert mention/ID to Member
                member = await commands.MemberConverter().convert(ctx, raw_mention)
            except commands.BadArgument:
                errors.append(f"• Could not find player: `{raw_mention}`")
                continue

            # Validate kills
            try:
                kills = int(raw_kills)
                if kills < 0:
                    raise ValueError
            except ValueError:
                errors.append(f"• Invalid kills value `{raw_kills}` for {member.display_name}")
                continue

            player_kills.append((str(member.id), kills))

        if not player_kills:
            embed = discord.Embed(
                description="❌ No valid player-kill pairs found.",
                color=ERROR_COLOR
            )
            return await ctx.send(embed=embed)

        # Write to DB
        not_found = db.add_match_stats(player_kills)

        # Build response embed
        embed = discord.Embed(
            title="✅ Stats Successfully Entered Boss",
            color=SUCCESS_COLOR
        )

        logged_lines = []
        for discord_id, kills in player_kills:
            if discord_id not in not_found:
                player = db.get_player(discord_id)
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
            embed.add_field(
                name="❌ Errors",
                value="\n".join(errors),
                inline=False
            )

        embed.set_footer(text="Both Weekly & Overall stats updated.")
        await ctx.send(embed=embed)

    # ══════════════════════════════════════════════════════
    #   !resetweekly
    # ══════════════════════════════════════════════════════
    @commands.command(name="resetweekly")
    @is_admin_check()
    async def reset_weekly(self, ctx: commands.Context):
        """Wipe all weekly stats. Overall stats untouched."""

        # Confirmation prompt
        confirm_embed = discord.Embed(
            title="⚠️ Confirm Weekly Reset",
            description=(
                "This will **zero out ALL weekly stats** for every player.\n"
                "Overall stats will **not** be affected.\n\n"
                "React with ✅ to confirm or ❌ to cancel."
            ),
            color=0xffd166
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
            db.reset_weekly()
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
    #   !manageteam [action] @player [value]
    # ══════════════════════════════════════════════════════
    @commands.command(name="manageteam")
    @is_admin_check()
    async def manage_team(self, ctx: commands.Context, action: str, member: Member, *, value: str = None):
        """
        Manage player registrations.
        Actions:
          add        @player IGN [team]   — Register new player
          remove     @player              — Remove player from DB
          update_ign @player NewIGN       — Update in-game name
          set_team   @player TeamName     — Move player to a team
        """
        action = action.lower()
        discord_id = str(member.id)

        # ── ADD ──────────────────────────────────────────
        if action == "add":
            if not value:
                return await ctx.send(embed=discord.Embed(
                    description="❌ Usage: `!manageteam add @player IGN [TeamName]`",
                    color=ERROR_COLOR
                ))

            parts = value.split()
            ign  = parts[0]
            team = " ".join(parts[1:]) if len(parts) > 1 else "Bench"

            success = db.add_player(discord_id, ign, team)
            if success:
                embed = discord.Embed(
                    title="✅ Player Added",
                    color=SUCCESS_COLOR
                )
                embed.add_field(name="Discord", value=member.mention, inline=True)
                embed.add_field(name="IGN",     value=ign,            inline=True)
                embed.add_field(name="Team",    value=team,           inline=True)
            else:
                embed = discord.Embed(
                    description=f"❌ {member.mention} is already registered.",
                    color=ERROR_COLOR
                )
            await ctx.send(embed=embed)

        # ── REMOVE ───────────────────────────────────────
        elif action == "remove":
            success = db.remove_player(discord_id)
            if success:
                embed = discord.Embed(
                    title="🗑️ Player Removed",
                    description=f"{member.mention} and all their stats have been deleted.",
                    color=SUCCESS_COLOR
                )
            else:
                embed = discord.Embed(
                    description=f"❌ {member.mention} is not in the database.",
                    color=ERROR_COLOR
                )
            await ctx.send(embed=embed)

        # ── UPDATE IGN ───────────────────────────────────
        elif action == "update_ign":
            if not value:
                return await ctx.send(embed=discord.Embed(
                    description="❌ Usage: `!manageteam update_ign @player NewIGN`",
                    color=ERROR_COLOR
                ))
            success = db.update_ign(discord_id, value.strip())
            if success:
                embed = discord.Embed(
                    title="✏️ IGN Updated",
                    description=f"{member.mention}'s IGN → **{value.strip()}**",
                    color=SUCCESS_COLOR
                )
            else:
                embed = discord.Embed(
                    description=f"❌ {member.mention} not found. Register first with `!manageteam add`.",
                    color=ERROR_COLOR
                )
            await ctx.send(embed=embed)

        # ── SET TEAM ─────────────────────────────────────
        elif action == "set_team":
            if not value:
                return await ctx.send(embed=discord.Embed(
                    description="❌ Usage: `!manageteam set_team @player TeamName`\nExample: `!manageteam set_team @Kohli Team Alpha`",
                    color=ERROR_COLOR
                ))
            success = db.set_team(discord_id, value.strip())
            if success:
                embed = discord.Embed(
                    title="🏷️ Team Updated",
                    description=f"{member.mention} → **{value.strip()}**",
                    color=SUCCESS_COLOR
                )
            else:
                embed = discord.Embed(
                    description=f"❌ {member.mention} not found.",
                    color=ERROR_COLOR
                )
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
                color=ERROR_COLOR
            )
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
            embed = discord.Embed(
                description="❌ Usage: `!leaderboard weekly` or `!leaderboard overall`",
                color=ERROR_COLOR
            )
            await ctx.send(embed=embed)

    # ── Weekly leaderboard ───────────────────────────────
    async def _send_weekly_leaderboard(self, ctx: commands.Context):
        teams = db.get_weekly_leaderboard()

        if not teams:
            return await ctx.send(embed=discord.Embed(
                description="📭 No players in the database yet.",
                color=ERROR_COLOR
            ))

        embed = discord.Embed(
            title="🎮 WoW Weekly Leaderboard",
            color=EMBED_COLOR
        )

        for team_name, players in teams.items():
            lines = []
            team_rank = 1
            for p in players:
                medal = MEDALS.get(team_rank, f"`#{team_rank}`")
                ign   = p["ign"][:14]
                line  = f"{medal} **{ign}** — `M:{p['matches']}` `K:{p['kills']}` `AVG:{p['avg']:.2f}`"
                lines.append(line)
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

    # ── Lifetime leaderboard ─────────────────────────────
    async def _send_lifetime_leaderboard(self, ctx: commands.Context):
        players = db.get_lifetime_leaderboard()

        if not players:
            return await ctx.send(embed=discord.Embed(
                description="📭 No players in the database yet.",
                color=ERROR_COLOR
            ))

        embed = discord.Embed(
            title="👑 WoW Overall Leaderboard",
            color=0xffd166  # gold for overall
        )

        lines = []
        for rank, p in enumerate(players, start=1):
            medal = MEDALS.get(rank, f"`#{rank}`")
            ign   = p["ign"][:14]
            line  = f"{medal} **{ign}** — `M:{p['matches']}` `K:{p['kills']}` `AVG:{p['avg']:.2f}`"
            lines.append(line)

            if len(lines) == 10:
                embed.add_field(name="\u200b", value="\n".join(lines), inline=False)
                lines = []

        if lines:
            embed.add_field(name="\u200b", value="\n".join(lines), inline=False)

        total_kills = sum(p["kills"] for p in players)
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
            db.set_admin_role(role.id)
            embed = discord.Embed(
                description=f"✅ Wow Manager role has been successfully set to {role.mention}",
                color=SUCCESS_COLOR
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("Usage: `!assign wow manager @role`")

    # ══════════════════════════════════════════════════════
    #   !bgmihelp
    # ══════════════════════════════════════════════════════
    @commands.command(name="bgmihelp")
    async def bgmi_help(self, ctx: commands.Context):
        embed = discord.Embed(
            title="🎮 WoW Bot — Command Reference",
            color=EMBED_COLOR
        )
        embed.add_field(
            name="📊 Leaderboards (Everyone)",
            value=(
                "`!leaderboard weekly` — Weekly stats grouped by team\n"
                "`!leaderboard overall` — All-time kills ranked globally\n"
                "`!lb` — Shortcut for leaderboard"
            ),
            inline=False
        )
        embed.add_field(
            name=f"⚙️ Admin Commands (`{ADMIN_ROLE}` only)",
            value=(
                "`!assign wow manager @role` — Assign manager role (Admin only)\n"
                "`!addmatchstats @p1 k1 @p2 k2 ...` — Log match kills\n"
                "`!resetweekly` — Wipe weekly stats (with confirmation)\n"
                "`!manageteam add @p IGN [Team]` — Register player\n"
                "`!manageteam remove @p` — Delete player\n"
                "`!manageteam update_ign @p NewIGN` — Update IGN\n"
                "`!manageteam set_team @p TeamName` — Move to team"
            ),
            inline=False
        )
        embed.add_field(
            name="📝 Team Names",
            value="Use exact team names like `Team Alpha`, `Team Bravo`, or `Bench`",
            inline=False
        )
        embed.set_footer(text="Klyro Bot • BGMI Module")
        await ctx.send(embed=embed)

    # ══════════════════════════════════════════════════════
    #   !dbstatus
    # ══════════════════════════════════════════════════════
    @commands.command(name="dbstatus")
    @commands.has_permissions(administrator=True)
    async def db_status(self, ctx: commands.Context):
        """Check the database connection status (Admin only)"""
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

    @bgmi_help.error
    @add_match_stats.error
    @reset_weekly.error
    @manage_team.error
    @assign_role.error
    @db_status.error
    async def bgmi_admin_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                description="❌ You need Administrator permissions to use this command!",
                color=ERROR_COLOR
            )
            await ctx.send(embed=embed)
        elif isinstance(error, (commands.MissingRole, commands.CheckAnyFailure)):
            admin_role_id = db.get_admin_role()
            role_mention = f"<@&{admin_role_id}>" if admin_role_id else f"`{ADMIN_ROLE}`"
            embed = discord.Embed(
                description=f"❌ You need the {role_mention} role (or Administrator) to use this command!",
                color=ERROR_COLOR
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MemberNotFound):
            embed = discord.Embed(
                description="❌ Could not find that member. Make sure to ping them correctly.",
                color=ERROR_COLOR
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.RoleNotFound):
            embed = discord.Embed(
                description="❌ Could not find that role. Make sure to ping it correctly.",
                color=ERROR_COLOR
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                description=f"❌ Invalid argument provided: {error}",
                color=ERROR_COLOR
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                description=f"❌ An error occurred: {str(error)}",
                color=ERROR_COLOR
            )
            await ctx.send(embed=embed)


# ── Cog loader ────────────────────────────────────────────
def setup(bot):
    bot.add_cog(BGMICog(bot))