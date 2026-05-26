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

class BGMICog(commands.Cog, name="BGMI"):
    """BGMI Clan Leaderboard System for Klyro Bot"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Permission check helper ──────────────────────────
    def is_admin(self, ctx: commands.Context) -> bool:
        return any(r.name == ADMIN_ROLE for r in ctx.author.roles)

    def admin_only(self):
        async def predicate(ctx):
            if not self.is_admin(ctx):
                raise commands.MissingRole(ADMIN_ROLE)
            return True
        return commands.check(predicate)

    # ══════════════════════════════════════════════════════
    #   !addmatchstats @p1 k1 @p2 k2 ...
    # ══════════════════════════════════════════════════════
    @commands.command(name="addmatchstats")
    @commands.check_any(commands.has_role(ADMIN_ROLE))
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

        embed.set_footer(text="Both Weekly & Lifetime stats updated.")
        await ctx.send(embed=embed)

    # ══════════════════════════════════════════════════════
    #   !resetweekly
    # ══════════════════════════════════════════════════════
    @commands.command(name="resetweekly")
    @commands.check_any(commands.has_role(ADMIN_ROLE))
    async def reset_weekly(self, ctx: commands.Context):
        """Wipe all weekly stats. Lifetime untouched."""

        # Confirmation prompt
        confirm_embed = discord.Embed(
            title="⚠️ Confirm Weekly Reset",
            description=(
                "This will **zero out ALL weekly stats** for every player.\n"
                "Lifetime stats will **not** be affected.\n\n"
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
                description="All weekly kills and matches have been wiped to **0**.\nLifetime stats remain unchanged.",
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
    @commands.check_any(commands.has_role(ADMIN_ROLE))
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
    #   !leaderboard [weekly|lifetime]
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
                description="❌ Usage: `!leaderboard weekly` or `!leaderboard lifetime`",
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
            title="🎮 BGMI Weekly Leaderboard",
            description=(
                "`Rank  IGN              M    K    AVG `\n"
                "`────────────────────────────────────`"
            ),
            color=EMBED_COLOR
        )
        embed.set_thumbnail(url="https://i.imgur.com/HaFl2R6.png")  # BGMI logo (replace if needed)

        global_rank = 1  # rank across entire weekly board
        team_rank_map = {}  # separate rank per team

        for team_name, players in teams.items():
            lines = []
            team_rank = 1
            for p in players:
                medal = MEDALS.get(team_rank, f"`#{team_rank:>2}`")
                ign   = p["ign"][:15].ljust(15)
                line  = (
                    f"{medal} `{ign}` "
                    f"`M:{p['matches']:>3}` "
                    f"`K:{p['kills']:>4}` "
                    f"`{p['avg']:>5.2f}`"
                )
                lines.append(line)
                team_rank += 1

            team_icon = "🔴" if "alpha" in team_name.lower() else "🔵" if "bravo" in team_name.lower() else "⚪"
            embed.add_field(
                name=f"{team_icon} {team_name}",
                value="\n".join(lines) if lines else "*No stats yet*",
                inline=False
            )

        total_matches = sum(
            p["matches"]
            for players in teams.values()
            for p in players
        )
        total_players = sum(len(v) for v in teams.values())

        embed.set_footer(
            text=f"👥 {total_players} players • 🔫 Total matches tracked: {total_matches // max(total_players, 1)}"
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
            title="👑 BGMI Lifetime Leaderboard",
            description=(
                "`Rank  IGN              Matches  Kills  AVG  `\n"
                "`──────────────────────────────────────────`"
            ),
            color=0xffd166  # gold for lifetime
        )

        lines = []
        for rank, p in enumerate(players, start=1):
            medal = MEDALS.get(rank, f"`#{rank:>2}`")
            ign   = p["ign"][:15].ljust(15)
            line  = (
                f"{medal} `{ign}` "
                f"`M:{p['matches']:>4}` "
                f"`K:{p['kills']:>5}` "
                f"`{p['avg']:>5.2f}`"
            )
            lines.append(line)

            # Split into multiple fields if >20 lines (Discord embed limit)
            if len(lines) == 20:
                embed.add_field(name="\u200b", value="\n".join(lines), inline=False)
                lines = []

        if lines:
            embed.add_field(name="\u200b", value="\n".join(lines), inline=False)

        total_kills = sum(p["kills"] for p in players)
        embed.set_footer(text=f"👥 {len(players)} players • 🔫 Total lifetime kills: {total_kills}")
        embed.timestamp = ctx.message.created_at
        await ctx.send(embed=embed)

    # ══════════════════════════════════════════════════════
    #   !bgmihelp
    # ══════════════════════════════════════════════════════
    @commands.command(name="bgmihelp")
    async def bgmi_help(self, ctx: commands.Context):
        embed = discord.Embed(
            title="🎮 BGMI Bot — Command Reference",
            color=EMBED_COLOR
        )
        embed.add_field(
            name="📊 Leaderboards (Everyone)",
            value=(
                "`!leaderboard weekly` — Weekly stats grouped by team\n"
                "`!leaderboard lifetime` — All-time kills ranked globally\n"
                "`!lb` — Shortcut for leaderboard"
            ),
            inline=False
        )
        embed.add_field(
            name=f"⚙️ Admin Commands (`{ADMIN_ROLE}` only)",
            value=(
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


# ── Cog loader ────────────────────────────────────────────
async def setup(bot: commands.Bot):
    await bot.add_cog(BGMICog(bot))
