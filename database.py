import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import DictCursor

DATABASE_URL = os.environ.get("DATABASE_URL") or "postgresql://neondb_owner:npg_xtaY3l6GjwSV@ep-royal-river-apeji572.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require"

if not DATABASE_URL:
    print("WARNING: DATABASE_URL not set! Database functions will fail unless set.")
    db_pool = None
else:
    # Initialize a connection pool (min 1, max 10 connections)
    db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, DATABASE_URL)

class DBConnection:
    def __enter__(self):
        if not db_pool:
            raise Exception("Database is not configured. Please set DATABASE_URL.")
        self.conn = db_pool.getconn()
        return self.conn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, 'conn') and self.conn:
            db_pool.putconn(self.conn)

def init_db():
    if not db_pool: return
    with DBConnection() as conn:
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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS warnings (
                id SERIAL PRIMARY KEY,
                guild_id TEXT,
                user_id TEXT,
                moderator_id TEXT,
                reason TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

def set_admin_role(role_id: int):
    with DBConnection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO config (key, value) 
            VALUES (%s, %s) 
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        ''', (str(role_id), str(role_id)))
        conn.commit()

def get_admin_role():
    with DBConnection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM config WHERE key = 'wow_manager_role'")
        row = cursor.fetchone()
        if row:
            return int(row[0])
        return None

def add_match_stats(player_kills):
    not_found = []
    with DBConnection() as conn:
        cursor = conn.cursor()
        for discord_id, kills in player_kills:
            cursor.execute('SELECT 1 FROM players WHERE discord_id = %s', (str(discord_id),))
            if cursor.fetchone():
                cursor.execute('''
                    UPDATE players 
                    SET weekly_matches = weekly_matches + 1,
                        lifetime_matches = lifetime_matches + 1,
                        weekly_kills = weekly_kills + %s,
                        lifetime_kills = lifetime_kills + %s
                    WHERE discord_id = %s
                ''', (kills, kills, str(discord_id)))
            else:
                not_found.append(str(discord_id))
        conn.commit()
    return not_found

def get_player(discord_id):
    with DBConnection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute('SELECT * FROM players WHERE discord_id = %s', (str(discord_id),))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

def reset_weekly():
    with DBConnection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE players SET weekly_matches = 0, weekly_kills = 0')
        conn.commit()

def add_player(discord_id, ign, team):
    try:
        with DBConnection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO players (discord_id, bgmi_ign, team_name)
                VALUES (%s, %s, %s)
            ''', (str(discord_id), ign, team))
            conn.commit()
            return True
    except psycopg2.IntegrityError:
        return False

def remove_player(discord_id):
    with DBConnection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM players WHERE discord_id = %s', (str(discord_id),))
        if cursor.rowcount > 0:
            conn.commit()
            return True
        return False

def update_ign(discord_id, ign):
    with DBConnection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE players SET bgmi_ign = %s WHERE discord_id = %s', (ign, str(discord_id)))
        if cursor.rowcount > 0:
            conn.commit()
            return True
        return False

def set_team(discord_id, team):
    with DBConnection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE players SET team_name = %s WHERE discord_id = %s', (team, str(discord_id)))
        if cursor.rowcount > 0:
            conn.commit()
            return True
        return False

def get_weekly_leaderboard():
    with DBConnection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
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
    with DBConnection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
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

if db_pool:
    init_db()
