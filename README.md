# 🤖 Discord Sports & Utility Bot

A feature-rich Discord bot with **AI-powered sports Q&A**, moderation, utility tools, and weather — supporting both `!prefix` and `/slash` commands.

---

## ✨ Features

| Category | Commands |
|---|---|
| 🏆 Sports AI | `ask`, `compare`, `records`, `clearcache` |
| 🔨 Moderation | `kick`, `ban`, `mute`, `unmute`, `clear`, `warn`, `warnings`, `clearwarnings` |
| ⚙️ Utility | `remind`, `poll`, `timer`, `serverinfo`, `userinfo`, `ping` |
| 🌤️ Weather | `weather`, `forecast` |
| ✨ Miscellaneous | `avatar`, `emoji`, `sticker`, `setprefix`, `about`, `invite` |

---

## 🚀 Setup Guide

### 1. Clone the repo
```bash
git clone https://github.com/yourusername/discord-bot
cd discord-bot
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up your `.env` file
```bash
cp .env.example .env
# Now open .env and fill in your keys
```

### 4. Get your API keys

| Key | Where to get it |
|---|---|
| `DISCORD_TOKEN` | [discord.com/developers](https://discord.com/developers/applications) → New App → Bot → Token |
| `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com) (free tier available) |

### 5. Invite your bot to a server
- In Discord Developer Portal → OAuth2 → URL Generator
- Scopes: `bot` + `applications.commands`
- Permissions: `Administrator` (for full functionality)
- Copy the URL and open it in browser

### 6. Run the bot
```bash
python main.py
```

---

## 💬 Command Examples

```
!ask how many runs did Kohli score in IPL 2023?
!ask how many goals did Kane score in UCL 2025-26?
!compare Messi Ronaldo UCL career
!records top 5 wicket takers in T20 World Cup
!weather Mumbai
!forecast Delhi
!remind 25m Take a break
!poll Best IPL team? | CSK | MI | RCB
!timer 25 Pomodoro session
!warn @user spamming
!mute @user 10m cool down
!clear 20
!avatar @user
!emoji <:custom_emoji:123456789012345678>
!sticker (with an attached sticker)
!setprefix ?
!about
!invite

```

All of these also work as `/slash` commands!

---

## 🏗️ Project Structure

```
discord-bot/
├── main.py              # Bot startup + help command
├── requirements.txt
├── .env.example         # Template for environment variables
└── cogs/
    ├── sports_ai.py     # AI-powered sports Q&A
    ├── moderation.py    # Kick, ban, mute, warn etc.
    ├── utility.py       # Reminders, polls, timers
    ├── weather.py       # Weather & forecasts
    └── miscellaneous.py # Avatar, emojis, invite, setprefix, etc.
```

---

## 🛠️ Built With
- [py-cord](https://docs.pycord.dev/) — Discord bot framework
- [Google Gemini](https://aistudio.google.com) — AI sports Q&A
- [Open-Meteo](https://open-meteo.com) — Weather data (No API key required)
- SQLite — Warning logs storage
