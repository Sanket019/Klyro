import sqlite3
import os

DB_PATH = "bgmi_stats.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                discord_id TEXT PRIMARY KEY,
                bgmi_ign TEXT,
                team_name TEXT,
                weekly_matches INTEGER DEFAULT 0,
                weekly_kills INTEGER DEFAULT 0,
                lifetime_matches INTEGER DEFAULT 0,
                lifetime_kills INTEGER DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        conn.commit()

def set_admin_role(role_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO config (key, value) 
            VALUES ('wow_manager_role', ?) 
            ON CONFLICT(key) DO UPDATE SET value = ?
        ''', (str(role_id), str(role_id)))
        conn.commit()

def get_admin_role():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM config WHERE key = 'wow_manager_role'")
        row = cursor.fetchone()
        if row:
            return int(row[0])
        return None

def add_match_stats(player_kills):
    not_found = []
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        for discord_id, kills in player_kills:
            cursor.execute('SELECT 1 FROM players WHERE discord_id = ?', (str(discord_id),))
            if cursor.fetchone():
                cursor.execute('''
                    UPDATE players 
                    SET weekly_matches = weekly_matches + 1,
                        lifetime_matches = lifetime_matches + 1,
                        weekly_kills = weekly_kills + ?,
                        lifetime_kills = lifetime_kills + ?
                    WHERE discord_id = ?
                ''', (kills, kills, str(discord_id)))
            else:
                not_found.append(str(discord_id))
        conn.commit()
    return not_found

def get_player(discord_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM players WHERE discord_id = ?', (str(discord_id),))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

def reset_weekly():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE players SET weekly_matches = 0, weekly_kills = 0')
        conn.commit()

def add_player(discord_id, ign, team):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO players (discord_id, bgmi_ign, team_name)
                VALUES (?, ?, ?)
            ''', (str(discord_id), ign, team))
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False

def remove_player(discord_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM players WHERE discord_id = ?', (str(discord_id),))
        if cursor.rowcount > 0:
            conn.commit()
            return True
        return False

def update_ign(discord_id, ign):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE players SET bgmi_ign = ? WHERE discord_id = ?', (ign, str(discord_id)))
        if cursor.rowcount > 0:
            conn.commit()
            return True
        return False

def set_team(discord_id, team):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE players SET team_name = ? WHERE discord_id = ?', (team, str(discord_id)))
        if cursor.rowcount > 0:
            conn.commit()
            return True
        return False

def get_weekly_leaderboard():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT bgmi_ign, team_name, weekly_matches, weekly_kills
            FROM players
            WHERE weekly_matches > 0 OR weekly_kills > 0
            ORDER BY team_name, weekly_kills DESC
        ''')
        rows = cursor.fetchall()
        
    teams = {}
    for row in rows:
        team = row['team_name']
        if team not in teams:
            teams[team] = []
        matches = row['weekly_matches']
        kills = row['weekly_kills']
        avg = kills / matches if matches > 0 else 0.0
        teams[team].append({
            "ign": row['bgmi_ign'],
            "matches": matches,
            "kills": kills,
            "avg": avg
        })
    # ensure sorting within teams by kills DESC
    for t in teams:
        teams[t].sort(key=lambda x: x['kills'], reverse=True)
    return teams

def get_lifetime_leaderboard():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT bgmi_ign, lifetime_matches, lifetime_kills
            FROM players
            WHERE lifetime_matches > 0 OR lifetime_kills > 0
            ORDER BY lifetime_kills DESC
        ''')
        rows = cursor.fetchall()
        
    players = []
    for row in rows:
        matches = row['lifetime_matches']
        kills = row['lifetime_kills']
        avg = kills / matches if matches > 0 else 0.0
        players.append({
            "ign": row['bgmi_ign'],
            "matches": matches,
            "kills": kills,
            "avg": avg
        })
    return players

# Initialize DB when module is imported
init_db()
