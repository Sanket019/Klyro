import discord
from discord.ext import commands
import google.generativeai as genai
import os
import asyncio

SPORT_KEYWORDS = [
    "cricket", "ipl", "bcci", "test match", "odi", "t20", "wc", "world cup",
    "runs", "wickets", "century", "fifty", "innings", "over", "bowler", "batsman",
    "batter", "stumped", "lbw", "caught", "bowled", "six", "four", "no ball",
    "wide", "ashes", "rbi", "crease", "pitch", "drs", "powerplay", "rcb", "csk",
    "mi", "kkr", "srh", "dc", "gt", "lsg", "pbks", "rr",
    "football", "soccer", "fifa", "epl", "premier league", "la liga", "serie a",
    "bundesliga", "champions league", "goal", "penalty", "offside", "assist",
    "psg", "barcelona", "real madrid", "arsenal", "chelsea", "manchester",
    "liverpool", "messi", "ronaldo", "mbappe", "transfer", "red card", "yellow card",
    "tennis", "wimbledon", "us open", "french open", "australian open", "grand slam",
    "ace", "deuce", "set", "match point", "serve", "djokovic", "federer", "nadal",
    "sinner", "alcaraz", "wta", "atp",
    "match", "score", "live score", "fixture", "player", "team", "tournament",
    "championship", "league", "season", "stats", "record", "trophy", "final",
    "semifinal", "quarter final", "standings", "table", "ranking", "coach",
    "nba", "basketball", "nfl", "formula 1", "f1", "grand prix", "olympics",
    "badminton", "hockey", "kabaddi", "wrestling", "boxing", "ufc",
]

SYSTEM_PROMPT = """You are Klyro Sports, an expert sports analyst and statistician built into a Discord bot.

You have deep knowledge of:
- Cricket (IPL, Test, ODI, T20I, World Cups, domestic leagues)
- Football/Soccer (Premier League, La Liga, Champions League, FIFA World Cup, etc.)
- Tennis (all Grand Slams, ATP, WTA)
- Basketball (NBA), Formula 1, Olympics, and other major sports

When answering:
- Be direct and precise — give the actual stats/scores asked
- Format numbers clearly (e.g. "142 runs off 87 balls")
- For live scores: mention if your data may not be real-time and suggest checking a live source
- For historical records: be confident and accurate
- Keep responses concise — this is Discord, not an essay
- Use relevant emojis sparingly for readability (🏏 ⚽ 🎾 🏀)
- If you're unsure about very recent events (last few weeks), say so clearly

Never say you cannot access the internet — just answer from your training knowledge and flag if the event is very recent."""


class SportsCog(commands.Cog, name="Sports"):
    """🏆 Sports stats, records and scores powered by Gemini AI"""

    def __init__(self, bot):
        self.bot = bot
        genai.configure(api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_KEY"))
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=SYSTEM_PROMPT
        )
        self.conversations = {}
        self._locks = {}  # ✅ Per-user lock to prevent concurrent Gemini calls

    def is_sports_query(self, text: str) -> bool:
        text_lower = text.lower()
        return any(kw in text_lower for kw in SPORT_KEYWORDS)

    def _get_lock(self, user_id: str) -> asyncio.Lock:
        if user_id not in self._locks:
            self._locks[user_id] = asyncio.Lock()
        return self._locks[user_id]

    async def query_sports(self, user_id: str, question: str) -> str:
        async with self._get_lock(user_id):  # ✅ Prevent concurrent calls per user
            if user_id not in self.conversations:
                self.conversations[user_id] = []

            history = self.conversations[user_id]
            gemini_history = [
                {"role": "user" if m["role"] == "user" else "model",
                 "parts": [m["content"]]}
                for m in history
            ]

            chat = self.model.start_chat(history=gemini_history)

            loop = asyncio.get_running_loop()  # ✅ Fixed: use get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: chat.send_message(question)
            )
            answer = response.text

            history.append({"role": "user",  "content": question})
            history.append({"role": "model", "content": answer})

            if len(history) > 10:
                self.conversations[user_id] = history[-10:]

            return answer

    def build_embed(self, question: str, answer: str, author: discord.Member) -> discord.Embed:
        q = question.lower()
        if any(k in q for k in ["cricket", "ipl", "runs", "wicket", "bcci", "rcb", "csk", "mi", "kkr"]):
            color, icon = 0x00cc44, "🏏"
        elif any(k in q for k in ["football", "soccer", "goal", "premier", "fifa", "psg", "arsenal"]):
            color, icon = 0x3d85c8, "⚽"
        elif any(k in q for k in ["tennis", "wimbledon", "grand slam", "serve", "ace"]):
            color, icon = 0xffcc00, "🎾"
        elif any(k in q for k in ["basketball", "nba"]):
            color, icon = 0xff6b00, "🏀"
        elif any(k in q for k in ["formula", "f1", "grand prix"]):
            color, icon = 0xff0000, "🏎️"
        else:
            color, icon = 0xa855f7, "🏆"

        embed = discord.Embed(title=f"{icon}  Sports Query", color=color)
        embed.add_field(name="❓ Question", value=f"*{question[:200]}*", inline=False)

        # ✅ Split long answers across fields properly
        if len(answer) <= 1024:
            embed.add_field(name="📊 Answer", value=answer, inline=False)
        else:
            chunks = [answer[i:i+1024] for i in range(0, min(len(answer), 2048), 1024)]
            embed.add_field(name="📊 Answer", value=chunks[0], inline=False)
            for chunk in chunks[1:]:
                embed.add_field(name="\u200b", value=chunk, inline=False)
            if len(answer) > 2048:
                embed.add_field(name="\u200b", value="*...response truncated. Ask a more specific question for full details.*", inline=False)

        embed.set_footer(
            text=f"Asked by {author.display_name}  •  Powered by Gemini 2.0  •  Live scores may be delayed",
            icon_url=author.display_avatar.url
        )
        embed.timestamp = discord.utils.utcnow()
        return embed

    # ✅ NEW: Auto-respond to sports messages without a command
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.content.startswith("!"):  # Don't double-handle commands
            return
        if self.is_sports_query(message.content):
            async with message.channel.typing():
                try:
                    answer = await self.query_sports(str(message.author.id), message.content)
                    embed = self.build_embed(message.content, answer, message.author)
                    await message.reply(embed=embed, mention_author=False)
                except Exception as e:
                    await message.reply(f"❌ Sports Error: `{e}`", mention_author=False)

    @commands.command(name="sports", aliases=["sp", "cricket", "football", "score"])
    async def sports(self, ctx: commands.Context, *, question: str):
        """Ask anything about any sport."""
        async with ctx.typing():
            try:
                answer = await self.query_sports(str(ctx.author.id), question)
                embed = self.build_embed(question, answer, ctx.author)
                await ctx.send(embed=embed)
            except Exception as e:
                await ctx.send(embed=discord.Embed(
                    description=f"❌ Sports Error: `{e}`",
                    color=0xff4757
                ))

    @commands.command(name="livescore", aliases=["live", "ls"])
    async def livescore(self, ctx: commands.Context, *, match: str):
        """Get live or latest score for a match."""
        async with ctx.typing():
            try:
                question = f"Give me the live or most recent score and match status for: {match}. If you don't have real-time data, give the latest result you know and clearly say your data may not be live."
                answer = await self.query_sports(str(ctx.author.id), question)
                embed = self.build_embed(f"Live Score: {match}", answer, ctx.author)
                embed.title = "📡  Live Score"
                await ctx.send(embed=embed)
            except Exception as e:
                await ctx.send(embed=discord.Embed(
                    description=f"❌ Error: `{e}`",
                    color=0xff4757
                ))

    @commands.command(name="player", aliases=["playerstats", "ps"])
    async def player(self, ctx: commands.Context, *, query: str):
        """Get stats for any player."""
        async with ctx.typing():
            try:
                question = f"Give me detailed career stats and records for: {query}"
                answer = await self.query_sports(str(ctx.author.id), question)
                embed = self.build_embed(f"Player: {query}", answer, ctx.author)
                embed.title = "👤  Player Stats"
                await ctx.send(embed=embed)
            except Exception as e:
                await ctx.send(embed=discord.Embed(
                    description=f"❌ Error: `{e}`",
                    color=0xff4757
                ))

    @commands.command(name="clearsports")
    async def clearsports(self, ctx: commands.Context):
        """Reset your sports conversation history."""
        self.conversations.pop(str(ctx.author.id), None)
        self._locks.pop(str(ctx.author.id), None)
        await ctx.send(embed=discord.Embed(
            description="✅ Your sports conversation history has been cleared.",
            color=0x00ff88
        ))

    @commands.command(name="sportshelp")
    async def sportshelp(self, ctx: commands.Context):
        embed = discord.Embed(title="🏆 Klyro Sports — Commands", color=0xa855f7)
        embed.add_field(
            name="📋 Commands",
            value=(
                "`!sports <question>` — Ask anything about any sport\n"
                "`!sp` — Shortcut for !sports\n"
                "`!livescore <match>` — Live/latest score for a match\n"
                "`!live` / `!ls` — Shortcut for !livescore\n"
                "`!player <name + query>` — Player career stats\n"
                "`!clearsports` — Reset conversation memory"
            ),
            inline=False
        )
        embed.add_field(
            name="💡 Example Queries",
            value=(
                "`!sports who won ipl 2026`\n"
                "`!sports virat kohli test centuries`\n"
                "`!livescore ind vs eng`\n"
                "`!player messi career goals`\n"
                "`!player djokovic grand slam wins`"
            ),
            inline=False
        )
        embed.add_field(
            name="⚠️ Note",
            value="Powered by Gemini AI. Historical stats are accurate. Live scores may not be real-time — verify on ESPNCricinfo / Google for ongoing matches.",
            inline=False
        )
        embed.set_footer(text="Klyro Bot • Sports Module")
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(SportsCog(bot))