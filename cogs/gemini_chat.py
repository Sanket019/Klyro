import discord
from discord.ext import commands
import google.generativeai as genai
import os
import asyncio

class GeminiChat(commands.Cog):
    """🤖 General AI — Ask Gemini anything!"""

    def __init__(self, bot):
        self.bot = bot
        genai.configure(api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_KEY"))
        # Using gemini-pro as it's the most stable universally available free-tier model alias
        self.model = genai.GenerativeModel("gemini-pro")
        self.conversations = {}

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

    @commands.command(name="chat", help="Chat with Gemini AI! e.g. !chat Write a poem")
    async def chat_prefix(self, ctx, *, question: str):
        async with ctx.typing():
            try:
                answer = await self.query_gemini(str(ctx.author.id), question)
                # Discord messages have a 2000 character limit
                if len(answer) > 2000:
                    answer = answer[:1996] + "..."
                await ctx.send(answer)
            except Exception as e:
                await ctx.send(f"❌ Gemini Error: `{e}`")

    @discord.slash_command(name="chat", description="Chat with Gemini AI about anything!")
    async def chat_slash(self, ctx, question: str):
        await ctx.defer()
        try:
            answer = await self.query_gemini(str(ctx.author.id), question)
            if len(answer) > 2000:
                answer = answer[:1996] + "..."
            await ctx.respond(answer)
        except Exception as e:
            await ctx.respond(f"❌ Gemini Error: `{e}`")


def setup(bot):
    bot.add_cog(GeminiChat(bot))
