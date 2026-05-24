# 🤖 Klyro - Multipurpose Discord Bot

Klyro is a feature-rich, multipurpose Discord bot designed to bring AI chat, sports intelligence, moderation tools, utility features, weather info, and general fun to your server. It supports both custom prefix commands and modern Discord slash (`/`) commands.

## 🛠️ Technology Stack

* **Python 3 & Py-cord**: The core language and Discord API wrapper.
* **Google Gemini AI (`gemini-1.5-flash`)**: Powers the General AI chat and the specialized Sports AI.
* **Open-Meteo API**: Keyless API used for real-time weather and forecasting.
* **Flask & Gunicorn**: Used alongside threading to maintain a lightweight web server, satisfying cloud hosting port-binding requirements.
* **Render**: Cloud platform used for continuous deployment.

## ✨ Features & Commands

### 🤖 General AI
Have open-ended conversations with the AI:
* `!chat <question>` — Chat with Gemini AI about anything!

### 🏆 Sports AI
Get instant answers to sports queries, compare players, and find records:
* `!ask <question>` — Ask anything about cricket, football, F1, NBA, and more.
* `!compare <player1> <player2> [context]` — Compare two players side-by-side.
* `!records <query>` — Look up sports records, rankings, and histories.
* `!clearcache` — Clear your conversation history with the AI.

### 🔨 Moderation
Keep your server clean, organized, and secure:
* `!kick @user [reason]` — Kick a member.
* `!ban @user [reason]` — Ban a member.
* `!mute @user <duration> [reason]` — Timeout a member (e.g. `10m`, `1h`, `1d`).
* `!unmute @user` — Remove a timeout.
* `!warn @user [reason]` — Issue a warning to a member.
* `!warnings @user` — View warning logs for a member.
* `!clearwarnings @user` — Clear all warning logs for a member.
* `!clear <amount>` — Delete recent messages (default is 10, max 100).

### ⚙️ Utility
Everyday tools to help manage actions and server information:
* `!remind <duration> <message>` — Set a reminder (e.g. `!remind 30m Take a break`).
* `!poll <question>, <option1>, <option2>` — Create a reaction-based poll (comma-separated).
* `!timer <minutes> [label]` — Start a countdown timer.
* `!serverinfo` — Display details about the current server.
* `!userinfo [@user]` — Display details about a user's account.
* `!ping` — Check the bot's current connection latency.

### 🌤️ Weather
Get weather forecasts and current conditions:
* `!weather <city>` — Get current temperature, humidity, wind, and conditions.
* `!forecast <city>` — Get a 3-day weather forecast.

### ✨ Miscellaneous
General utility and configuration commands:
* `!avatar [@user]` — View and download a user's full-size avatar.
* `!emoji <emoji>` — Enlarge custom emojis.
* `!sticker` — Enlarge stickers sent with the command.
* `!setprefix <prefix>` — Customise the bot's text command prefix for your server (Admin-only).
* `!about` — View information about the bot.
* `!invite` — Generate a link to invite the bot to your own servers.

---

*Note: All commands can be run using the server's command prefix or by typing `/` to use slash commands.*
