import discord
from discord.ext import commands
import os
import json
from dotenv import load_dotenv
from keep_alive import keep_alive

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
    "cogs.miscellaneous",
    "cogs.gemini_chat",
    "cogs.bgmi",
]

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")
    print(f"📡 Connected to {len(bot.guilds)} server(s)")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="!help or /help 🤖"
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
    p = ctx.prefix
    embed = discord.Embed(
        title="🤖 Bot Commands",
        description=f"Use your server's prefix (`{p}`) or slash commands `/`!\n",
        color=0x9D00FF
    )
    embed.add_field(name="🎮 BGMI Custom Matches", value=f"""
`{p}lb weekly` — Weekly stats grouped by team
`{p}lb overall` — All-time kills ranked globally
`{p}bgmihelp` — Show all BGMI commands
""", inline=False)

    embed.add_field(name="🔨 Moderation", value=f"""
`{p}kick @user [reason]` — Kick a member
`{p}ban @user [reason]` — Ban a member
`{p}mute @user [duration] [reason]` — Timeout a member
`{p}unmute @user` — Remove timeout
`{p}clear [amount]` — Delete messages (default 10)
`{p}warn @user [reason]` — Warn a member
`{p}warnings @user` — View warnings
`{p}clearwarnings @user` — Clear all warnings
""", inline=False)

    embed.add_field(name="⚙️ Utility", value=f"""
`{p}remind <time> <message>` — Set a reminder (e.g. `{p}remind 30m Study DSA`)
`{p}poll <question>, <opt1>, <opt2>` — Create a poll
`{p}timer <minutes> [label]` — Countdown timer
`{p}serverinfo` — Show server info
`{p}userinfo [@user]` — Show user info
`{p}ping` — Check bot latency
""", inline=False)

    embed.add_field(name="🌤️ Weather", value=f"""
`{p}weather <city>` — Current weather
`{p}forecast <city>` — 3-day forecast
""", inline=False)

    embed.add_field(name="✨ Miscellaneous", value=f"""
`{p}avatar [@user]` — View user's avatar
`{p}emoji <emoji>` — Enlarge an emoji
`{p}sticker` — Enlarge a sticker
`{p}setprefix <prefix>` — Change bot prefix (Admins)
`{p}about` — Bot information
`{p}invite` — Bot invite link
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

keep_alive()
bot.run(os.getenv("TOKEN"))
