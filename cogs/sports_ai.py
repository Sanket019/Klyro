import discord
from discord.ext import commands
import google.generativeai as genai
import os
import asyncio


SYSTEM_PROMPT = """You are a world-class sports statistics expert assistant for a Discord bot.

You have deep knowledge of:
🏏 CRICKET — IPL, Test cricket, ODIs, T20Is, T20 World Cup, Asia Cup, BBL, The Hundred
   - Player stats: runs, wickets, averages, strike rates, centuries, fifers
   - Team records, series results, head-to-head records, milestones

⚽ FOOTBALL — EPL, La Liga, Bundesliga, Serie A, Ligue 1, UCL, Europa League, World Cup, EURO
   - Goals, assists, clean sheets, appearances, trophies
   - Season-by-season breakdowns, transfer history

🏀 BASKETBALL — NBA, EuroLeague stats and records
🎾 TENNIS — ATP, WTA, Grand Slam stats
🏎️ F1 — Race results, championships, driver stats
🏑 Hockey, Rugby, Baseball — general knowledge

RESPONSE RULES:
- Be conversational but precise — like a knowledgeable friend
- Use emojis to make it fun and readable on Discord
- For stats, always mention the context (season, tournament, format)
- For player comparisons, use a clear side-by-side format
- If unsure about very recent events (last few weeks), say so honestly
- Keep answers concise but complete
- Use **bold** for player names and key numbers"""


def make_sports_embed(answer: str, title: str, author_name: str, color=0x9D00FF):
    embed = discord.Embed(description=answer, color=color)
    embed.set_author(name=title)
    embed.set_footer(text=f"Asked by {author_name} • Use !ask or /ask for follow-ups!")
    return embed


class SportsAI(commands.Cog):
    """🏆 Sports AI — Ask ANYTHING about sports in plain English!"""

    def __init__(self, bot):
        self.bot = bot
        genai.configure(api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_KEY"))
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=SYSTEM_PROMPT
        )
        self.conversations = {}  # Per-user conversation memory

    def get_history(self, user_id: str):
        if user_id not in self.conversations:
            self.conversations[user_id] = []
        return self.conversations[user_id]

    def trim_history(self, user_id: str):
        if len(self.conversations[user_id]) > 10:
            self.conversations[user_id] = self.conversations[user_id][-10:]

    async def query_gemini(self, user_id: str, question: str) -> str:
        history = self.get_history(user_id)
        
        gemini_history = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [msg["content"]]})
            
        chat = self.model.start_chat(history=gemini_history)
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: chat.send_message(question)
        )
        answer = response.text
        
        history.append({"role": "user", "content": question})
        history.append({"role": "model", "content": answer})
        self.trim_history(user_id)
        return answer

    # ── !ask ──────────────────────────────────────────────────────────────────
    @commands.command(name="ask", help="Ask anything about sports! e.g. !ask how many runs did Kohli score in IPL 2023")
    async def ask_prefix(self, ctx, *, question: str):
        async with ctx.typing():
            try:
                answer = await self.query_gemini(str(ctx.author.id), question)
                embed = make_sports_embed(answer, "🏆 Sports Stats", ctx.author.display_name)
                await ctx.send(embed=embed)
            except Exception as e:
                await ctx.send(f"❌ Something went wrong: `{e}`")

    @discord.slash_command(name="ask", description="Ask anything about sports! e.g. how many runs did Kohli score in IPL 2023")
    async def ask_slash(self, ctx, *, question: str):
        await ctx.defer()
        try:
            answer = await self.query_gemini(str(ctx.author.id), question)
            embed = make_sports_embed(answer, "🏆 Sports Stats", ctx.author.display_name)
            await ctx.respond(embed=embed)
        except Exception as e:
            await ctx.respond(f"❌ Something went wrong: `{e}`")

    # ── !compare ──────────────────────────────────────────────────────────────
    @commands.command(name="compare", help="Compare two players! e.g. !compare Kohli Rohit IPL")
    async def compare_prefix(self, ctx, player1: str, player2: str, *, context: str = "overall career"):
        async with ctx.typing():
            try:
                question = f"Compare {player1} vs {player2} in {context}. Give a clear side-by-side stats breakdown."
                answer = await self.query_gemini(str(ctx.author.id), question)
                embed = make_sports_embed(answer, f"⚔️ {player1} vs {player2}", ctx.author.display_name, color=0x9D00FF)
                await ctx.send(embed=embed)
            except Exception as e:
                await ctx.send(f"❌ Error: `{e}`")

    @discord.slash_command(name="compare", description="Compare two players! e.g. Kohli vs Rohit in IPL")
    async def compare_slash(self, ctx, player1: str, player2: str, context: str = "overall career"):
        await ctx.defer()
        try:
            question = f"Compare {player1} vs {player2} in {context}. Give a clear side-by-side stats breakdown."
            answer = await self.query_gemini(str(ctx.author.id), question)
            embed = make_sports_embed(answer, f"⚔️ {player1} vs {player2}", ctx.author.display_name, color=0x9D00FF)
            await ctx.respond(embed=embed)
        except Exception as e:
            await ctx.respond(f"❌ Error: `{e}`")

    # ── !records ──────────────────────────────────────────────────────────────
    @commands.command(name="records", help="Get sports records! e.g. !records highest run scorer in IPL history")
    async def records_prefix(self, ctx, *, query: str):
        async with ctx.typing():
            try:
                question = f"Tell me about sports records: {query}. Focus on rankings, historical data, and milestone stats."
                answer = await self.query_gemini(str(ctx.author.id), question)
                embed = make_sports_embed(answer, "🏅 Sports Records", ctx.author.display_name, color=0x9D00FF)
                await ctx.send(embed=embed)
            except Exception as e:
                await ctx.send(f"❌ Error: `{e}`")

    @discord.slash_command(name="records", description="Get records & rankings! e.g. highest run scorer in IPL history")
    async def records_slash(self, ctx, *, query: str):
        await ctx.defer()
        try:
            question = f"Tell me about sports records: {query}. Focus on rankings, historical data, and milestone stats."
            answer = await self.query_gemini(str(ctx.author.id), question)
            embed = make_sports_embed(answer, "🏅 Sports Records", ctx.author.display_name, color=0x9D00FF)
            await ctx.respond(embed=embed)
        except Exception as e:
            await ctx.respond(f"❌ Error: `{e}`")

    # ── !clearcache ───────────────────────────────────────────────────────────
    @commands.command(name="clearcache", help="Clear your sports conversation history")
    async def clearcache_prefix(self, ctx):
        self.conversations.pop(str(ctx.author.id), None)
        await ctx.send("🗑️ Your conversation history has been cleared! Fresh start.", delete_after=5)

    @discord.slash_command(name="clearcache", description="Clear your conversation history with the bot")
    async def clearcache_slash(self, ctx):
        self.conversations.pop(str(ctx.author.id), None)
        await ctx.respond("🗑️ Cleared! Fresh start.", ephemeral=True)


def setup(bot):
    bot.add_cog(SportsAI(bot))
