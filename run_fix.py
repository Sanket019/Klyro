import re

with open("database.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Fix literal \n if it exists and double WHERE clauses
content = content.replace(
    r"JOIN players p ON p.guild_id = mh.guild_id AND p.discord_id = mh.discord_id\n            WHERE mh.guild_id = %s",
    "JOIN players p ON p.guild_id = mh.guild_id AND p.discord_id = mh.discord_id\n            WHERE mh.guild_id = %s"
)

# get_match_history
content = content.replace("""
            WHERE mh.guild_id = %s
            ORDER BY mh.logged_at DESC
            LIMIT %s
        ''', (limit * 20,))""", """
            WHERE mh.guild_id = %s
            ORDER BY mh.logged_at DESC
            LIMIT %s
        ''', (guild_id, limit * 20))""")

# get_daily_mvp
content = content.replace("""
            WHERE mh.guild_id = %s
            WHERE mh.match_date = %s
            GROUP BY mh.discord_id, p.bgmi_ign, p.team_name
            ORDER BY total_kills DESC, matches_today DESC
            LIMIT 1
        ''', (date,))""", """
            WHERE mh.guild_id = %s AND mh.match_date = %s
            GROUP BY mh.discord_id, p.bgmi_ign, p.team_name
            ORDER BY total_kills DESC, matches_today DESC
            LIMIT 1
        ''', (guild_id, date))""")

# get_daily_summary
content = content.replace("""
            WHERE mh.guild_id = %s
            WHERE mh.match_date = %s
            GROUP BY mh.discord_id, p.bgmi_ign, p.team_name
            ORDER BY total_kills DESC
        ''', (date,))""", """
            WHERE mh.guild_id = %s AND mh.match_date = %s
            GROUP BY mh.discord_id, p.bgmi_ign, p.team_name
            ORDER BY total_kills DESC
        ''', (guild_id, date))""")

# get_weekly_leaderboard
content = content.replace("""
            SELECT bgmi_ign, team_name, weekly_matches, weekly_kills
            FROM players
            WHERE weekly_matches > 0 OR weekly_kills > 0
            ORDER BY team_name, weekly_kills DESC
        ''')""", """
            SELECT bgmi_ign, team_name, weekly_matches, weekly_kills
            FROM players
            WHERE guild_id = %s AND (weekly_matches > 0 OR weekly_kills > 0)
            ORDER BY team_name, weekly_kills DESC
        ''', (guild_id,))""")

# get_lifetime_leaderboard
content = content.replace("""
            SELECT bgmi_ign, lifetime_matches, lifetime_kills
            FROM players
            WHERE lifetime_matches > 0 OR lifetime_kills > 0
            ORDER BY lifetime_kills DESC
        ''')""", """
            SELECT bgmi_ign, lifetime_matches, lifetime_kills
            FROM players
            WHERE guild_id = %s AND (lifetime_matches > 0 OR lifetime_kills > 0)
            ORDER BY lifetime_kills DESC
        ''', (guild_id,))""")

# get_team_stats
content = content.replace("""
            FROM players
            WHERE LOWER(team_name) != 'bench'
            GROUP BY team_name
            ORDER BY total_kills DESC
        ''')""", """
            FROM players
            WHERE guild_id = %s AND LOWER(team_name) != 'bench'
            GROUP BY team_name
            ORDER BY total_kills DESC
        ''', (guild_id,))""")

# get_weekly_winner
content = content.replace("""
            FROM players
            WHERE weekly_kills > 0
            ORDER BY weekly_kills DESC
            LIMIT 1
        ''')""", """
            FROM players
            WHERE guild_id = %s AND weekly_kills > 0
            ORDER BY weekly_kills DESC
            LIMIT 1
        ''', (guild_id,))""")

with open("database.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Database query fixes applied.")
