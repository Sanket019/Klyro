import discord
from discord.ext import commands
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Bot setup — prefix "!" for normal commands, slash commands also work
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

def get_prefix(bot, message):
    if not message.guild:
        return "!"
    try:
        with open("prefixes.json", "r") as f:
            prefixes = json.load(f)
        return prefixes.get(str(message.guild.id), "!")
    except (FileNotFoundError, json.JSONDecodeError):
        return "!"

bot = commands.Bot(
    command_prefix=get_prefix,
    intents=intents,
    help_command=None  # We'll make our own !help
)

COGS = [
    "cogs.moderation",
    "cogs.utility",
    "cogs.weather",
    "cogs.sports_ai",
    "cogs.miscellaneous",
]

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")
    print(f"📡 Connected to {len(bot.guilds)} server(s)")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="sports | !help or /help 🏆"
        )
    )

# ── HELP COMMAND (works as both !help and /help) ──────────────────────────────

@bot.command(name="help")
async def help_prefix(ctx):
    await send_help(ctx)

@bot.slash_command(name="help", description="Show all bot commands")
async def help_slash(ctx):
    await send_help(ctx)

async def send_help(ctx):
    embed = discord.Embed(
        title="🤖 Bot Commands",
        description="Use your server's prefix (default `!`) or slash commands `/`!\n",
        color=0x9D00FF
    )
    embed.add_field(name="🏆 Sports AI", value="""
`!ask <question>` — Ask anything about any sport
`!compare <p1> <p2>` — Compare two players
`!records <query>` — Get records & rankings
`!clearcache` — Reset your conversation history
""", inline=False)

    embed.add_field(name="🔨 Moderation", value="""
`!kick @user [reason]` — Kick a member
`!ban @user [reason]` — Ban a member
`!mute @user [duration] [reason]` — Timeout a member
`!unmute @user` — Remove timeout
`!clear [amount]` — Delete messages (default 10)
`!warn @user [reason]` — Warn a member
`!warnings @user` — View warnings
`!clearwarnings @user` — Clear all warnings
""", inline=False)

    embed.add_field(name="⚙️ Utility", value="""
`!remind <time> <message>` — Set a reminder (e.g. `!remind 30m Study DSA`)
`!poll <question> | <opt1> | <opt2>` — Create a poll
`!timer <minutes> [label]` — Countdown timer
`!serverinfo` — Show server info
`!userinfo [@user]` — Show user info
`!ping` — Check bot latency
""", inline=False)

    embed.add_field(name="🌤️ Weather", value="""
`!weather <city>` — Current weather
`!forecast <city>` — 3-day forecast
""", inline=False)

    embed.add_field(name="✨ Miscellaneous", value="""
`!avatar [@user]` — View user's avatar
`!emoji <emoji>` — Enlarge an emoji
`!sticker` — Enlarge a sticker
`!setprefix <prefix>` — Change bot prefix (Admins)
`!about` — Bot information
`!invite` — Bot invite link
""", inline=False)

    embed.set_footer(text="Tip: Slash commands show options as you type!")
    await ctx.respond(embed=embed) if hasattr(ctx, 'respond') else await ctx.send(embed=embed)

# ── LOAD COGS ─────────────────────────────────────────────────────────────────

for cog in COGS:
    try:
        bot.load_extension(cog)
        print(f"✅ Loaded: {cog}")
    except Exception as e:
        print(f"❌ Failed to load {cog}: {e}")

bot.run(os.getenv("DISCORD_TOKEN"))
