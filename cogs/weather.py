import discord
from discord.ext import commands
import aiohttp
import os

WMO_CODES = {
    0: ("Clear sky", "☀️"),
    1: ("Mainly clear", "🌤️"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Fog", "🌫️"),
    48: ("Depositing rime fog", "🌫️"),
    51: ("Light drizzle", "🌦️"),
    53: ("Moderate drizzle", "🌦️"),
    55: ("Dense drizzle", "🌦️"),
    56: ("Light freezing drizzle", "🌧️"),
    57: ("Dense freezing drizzle", "🌧️"),
    61: ("Slight rain", "🌧️"),
    63: ("Moderate rain", "🌧️"),
    65: ("Heavy rain", "🌧️"),
    66: ("Light freezing rain", "🌧️"),
    67: ("Heavy freezing rain", "🌧️"),
    71: ("Slight snow fall", "❄️"),
    73: ("Moderate snow fall", "❄️"),
    75: ("Heavy snow fall", "❄️"),
    77: ("Snow grains", "❄️"),
    80: ("Slight rain showers", "🌧️"),
    81: ("Moderate rain showers", "🌧️"),
    82: ("Violent rain showers", "⛈️"),
    85: ("Slight snow showers", "❄️"),
    86: ("Heavy snow showers", "❄️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm with slight hail", "⛈️"),
    99: ("Thunderstorm with heavy hail", "⛈️")
}

async def send_response(ctx, embed=None, content=None, ephemeral=False):
    if hasattr(ctx, 'respond'):
        await ctx.respond(content=content, embed=embed, ephemeral=ephemeral)
    else:
        await ctx.send(content=content, embed=embed)

class Weather(commands.Cog):
    """🌤️ Weather — Current conditions and forecasts."""

    def __init__(self, bot):
        self.bot = bot

    async def get_coordinates(self, city: str):
        async with aiohttp.ClientSession() as session:
            url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None, "Error contacting geocoding service."
                data = await resp.json()
                if "results" not in data or not data["results"]:
                    return None, "City not found. Check the spelling!"
                return data["results"][0], None

    async def fetch_weather_and_forecast(self, lat: float, lon: float):
        async with aiohttp.ClientSession() as session:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=auto&forecast_days=3"
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None, "Error contacting weather service."
                return await resp.json(), None

    # ── WEATHER ───────────────────────────────────────────────────────────────
    async def _weather(self, ctx, city: str):
        geo_data, error = await self.get_coordinates(city)
        if error:
            return await send_response(ctx, content=f"❌ {error}")

        lat = geo_data["latitude"]
        lon = geo_data["longitude"]
        city_name = geo_data["name"]
        country = geo_data.get("country", "")

        weather_data, error = await self.fetch_weather_and_forecast(lat, lon)
        if error:
            return await send_response(ctx, content=f"❌ {error}")

        current = weather_data["current"]
        code = current["weather_code"]
        desc, emoji = WMO_CODES.get(code, ("Unknown", "🌡️"))
        temp = current["temperature_2m"]
        feels = current["apparent_temperature"]
        humidity = current["relative_humidity_2m"]
        wind = current["wind_speed_10m"]

        embed = discord.Embed(
            title=f"{emoji} Weather in {city_name}, {country}",
            description=f"**{desc}**",
            color=0x9D00FF
        )
        embed.add_field(name="🌡️ Temperature", value=f"{temp:.1f}°C (feels like {feels:.1f}°C)", inline=True)
        embed.add_field(name="💧 Humidity", value=f"{humidity}%", inline=True)
        embed.add_field(name="💨 Wind Speed", value=f"{wind:.1f} km/h", inline=True)
        embed.set_footer(text="Data from Open-Meteo (No API Key Required)")
        await send_response(ctx, embed=embed)

    @commands.command(name="weather", help="Get current weather. e.g. !weather Delhi")
    async def weather_prefix(self, ctx, *, city: str):
        await self._weather(ctx, city)

    @discord.slash_command(name="weather", description="Get current weather for a city")
    async def weather_slash(self, ctx, city: str):
        await self._weather(ctx, city)

    # ── FORECAST ──────────────────────────────────────────────────────────────
    async def _forecast(self, ctx, city: str):
        geo_data, error = await self.get_coordinates(city)
        if error:
            return await send_response(ctx, content=f"❌ {error}")

        lat = geo_data["latitude"]
        lon = geo_data["longitude"]
        city_name = geo_data["name"]
        country = geo_data.get("country", "")

        weather_data, error = await self.fetch_weather_and_forecast(lat, lon)
        if error:
            return await send_response(ctx, content=f"❌ {error}")

        daily = weather_data["daily"]

        embed = discord.Embed(
            title=f"📅 3-Day Forecast for {city_name}, {country}",
            color=0x9D00FF
        )

        for i in range(3):
            date = daily["time"][i]
            code = daily["weather_code"][i]
            desc, emoji = WMO_CODES.get(code, ("Unknown", "🌡️"))
            temp_max = daily["temperature_2m_max"][i]
            temp_min = daily["temperature_2m_min"][i]
            embed.add_field(
                name=f"{emoji} {date}",
                value=f"{desc}\n🌡️ {temp_min:.1f}°C - {temp_max:.1f}°C",
                inline=True
            )

        embed.set_footer(text="Data from Open-Meteo (No API Key Required)")
        await send_response(ctx, embed=embed)

    @commands.command(name="forecast", help="Get 3-day forecast. e.g. !forecast Mumbai")
    async def forecast_prefix(self, ctx, *, city: str):
        await self._forecast(ctx, city)

    @discord.slash_command(name="forecast", description="Get a 3-day weather forecast for a city")
    async def forecast_slash(self, ctx, city: str):
        await self._forecast(ctx, city)

def setup(bot):
    bot.add_cog(Weather(bot))
