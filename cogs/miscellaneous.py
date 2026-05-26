import discord
from discord.ext import commands
import json
import os
import re

async def send_response(ctx, embed=None, content=None, ephemeral=False):
    if hasattr(ctx, 'respond'):
        await ctx.respond(content=content, embed=embed, ephemeral=ephemeral)
    else:
        await ctx.send(content=content, embed=embed)

class Miscellaneous(commands.Cog):
    """✨ Miscellaneous — Avatars, emojis, prefix and bot info."""

    def __init__(self, bot):
        self.bot = bot

    # ── AVATAR ────────────────────────────────────────────────────────────────
    async def _avatar(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        embed = discord.Embed(title=f"👤 {member.display_name}'s Avatar", color=0x9D00FF)
        embed.set_image(url=member.display_avatar.url)
        await send_response(ctx, embed=embed)

    @commands.command(name="avatar", help="View someone's avatar")
    async def avatar_prefix(self, ctx, member: discord.Member = None):
        await self._avatar(ctx, member)

    @discord.slash_command(name="avatar", description="View someone's avatar")
    async def avatar_slash(self, ctx, member: discord.Member = None):
        await self._avatar(ctx, member)

    # ── ENLARGE EMOJI ─────────────────────────────────────────────────────────
    async def _emoji(self, ctx, emoji: str):
        # Extract custom emoji ID: <:name:id> or <a:name:id>
        match = re.search(r'<a?:[a-zA-Z0-9_]+:([0-9]+)>', emoji)
        if match:
            emoji_id = match.group(1)
            is_animated = emoji.startswith("<a:")
            ext = "gif" if is_animated else "png"
            url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}?size=1024"
            embed = discord.Embed(title="🖼️ Enlarged Emoji", color=0x9D00FF)
            embed.set_image(url=url)
            await send_response(ctx, embed=embed)
        else:
            await send_response(ctx, content="❌ Please provide a valid custom emoji.", ephemeral=True)

    @commands.command(name="emoji", help="Enlarge a custom emoji")
    async def emoji_prefix(self, ctx, emoji: str):
        await self._emoji(ctx, emoji)

    @discord.slash_command(name="emoji", description="Enlarge a custom emoji")
    async def emoji_slash(self, ctx, emoji: str):
        await self._emoji(ctx, emoji)

    # ── ENLARGE STICKER ───────────────────────────────────────────────────────
    @commands.command(name="sticker", help="Enlarge a sticker (send a sticker with the command)")
    async def sticker_prefix(self, ctx):
        if ctx.message.stickers:
            sticker = ctx.message.stickers[0]
            embed = discord.Embed(title=f"🖼️ Enlarged Sticker: {sticker.name}", color=0x9D00FF)
            embed.set_image(url=sticker.url)
            await send_response(ctx, embed=embed)
        else:
            await send_response(ctx, content="❌ Please send a sticker with this command.")

    @discord.slash_command(name="sticker", description="Enlarge a sticker (Not fully supported via slash, use prefix)")
    async def sticker_slash(self, ctx):
        await send_response(ctx, content="⚠️ Please use the prefix command (e.g. `!sticker`) and send a sticker with it.", ephemeral=True)

    # ── SET PREFIX ────────────────────────────────────────────────────────────
    async def _setprefix(self, ctx, prefix: str):
        if not ctx.author.guild_permissions.administrator:
            return await send_response(ctx, content="❌ You need Administrator permissions to change the prefix.", ephemeral=True)
            
        guild_id = str(ctx.guild.id)
        prefixes = {}
        if os.path.exists("prefixes.json"):
            with open("prefixes.json", "r") as f:
                try:
                    prefixes = json.load(f)
                except json.JSONDecodeError:
                    prefixes = {}
                
        prefixes[guild_id] = prefix
        
        with open("prefixes.json", "w") as f:
            json.dump(prefixes, f, indent=4)
            
        await send_response(ctx, content=f"✅ Bot prefix has been updated to `{prefix}`")

    @commands.command(name="setprefix", help="Set the bot's prefix for this server")
    @commands.has_permissions(administrator=True)
    async def setprefix_prefix(self, ctx, prefix: str):
        await self._setprefix(ctx, prefix)

    @discord.slash_command(name="setprefix", description="Set the bot's prefix for this server")
    @discord.default_permissions(administrator=True)
    async def setprefix_slash(self, ctx, prefix: str):
        await self._setprefix(ctx, prefix)

    # ── ABOUT ─────────────────────────────────────────────────────────────────
    async def _about(self, ctx):
        embed = discord.Embed(
            title="🤖 About Moderation Utility AI",
            description="I am a multi-purpose bot featuring general AI, moderation, weather, and more!",
            color=0x9D00FF
        )
        embed.add_field(name="Servers", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="Ping", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.set_footer(text="Thank you for using this bot!")
        await send_response(ctx, embed=embed)

    @commands.command(name="about", help="Bot information")
    async def about_prefix(self, ctx):
        await self._about(ctx)

    @discord.slash_command(name="about", description="Bot information")
    async def about_slash(self, ctx):
        await self._about(ctx)

    # ── INVITE ────────────────────────────────────────────────────────────────
    async def _invite(self, ctx):
        invite_url = discord.utils.oauth_url(self.bot.user.id, permissions=discord.Permissions(8))
        embed = discord.Embed(
            title="📨 Invite Me!",
            description=f"[Click here to invite me to your server!]({invite_url})",
            color=0x9D00FF
        )
        await send_response(ctx, embed=embed)

    @commands.command(name="invite", help="Get the bot's invite link")
    async def invite_prefix(self, ctx):
        await self._invite(ctx)

    @discord.slash_command(name="invite", description="Get the bot's invite link")
    async def invite_slash(self, ctx):
        await self._invite(ctx)


def setup(bot):
    bot.add_cog(Miscellaneous(bot))
