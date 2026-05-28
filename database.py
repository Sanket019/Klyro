import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import DictCursor

DATABASE_URL = os.environ.get("DATABASE_URL") or "postgresql://neondb_owner:npg_xtaY3l6GjwSV@ep-royal-river-apeji572.c-7.us-east-1.aws.neon.tech/neondb?sslmode=require"

if not DATABASE_URL:
    print("WARNING: DATABASE_URL not set! Database functions will fail unless set.")
    db_pool = None
else:
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
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='players' and column_name='guild_id';")
        if not cursor.fetchone():
            cursor.execute("DROP TABLE IF EXISTS players")
            cursor.execute("DROP TABLE IF EXISTS config")
            cursor.execute("DROP TABLE IF EXISTS match_history")
            cursor.execute("DROP TABLE IF EXISTS playing_lineup")

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                guild_id TEXT NOT NULL,
                discord_id TEXT NOT NULL,
                bgmi_ign TEXT,
                team_name TEXT,
                weekly_matches INTEGER DEFAULT 0,
                weekly_kills INTEGER DEFAULT 0,
                lifetime_matches INTEGER DEFAULT 0,
                lifetime_kills INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, discord_id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config (
                guild_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                PRIMARY KEY (guild_id, key)
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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS match_history (
                id SERIAL PRIMARY KEY,
                guild_id TEXT NOT NULL,
                discord_id TEXT NOT NULL,
                kills INTEGER NOT NULL DEFAULT 0,
                match_date TEXT NOT NULL,
                logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS playing_lineup (
                guild_id TEXT NOT NULL,
                team_name TEXT NOT NULL,
                discord_id TEXT NOT NULL,
                PRIMARY KEY (guild_id, team_name, discord_id)
            )
        ''')
        conn.commit()

# ── ALL EXISTING FUNCTIONS (unchanged) ────────────────────

def set_admin_role(guild_id: str, role_id: int):
    with DBConnection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO config (key, value)
            VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        ''', (guild_id, 'wow_manager_role', str(role_id)))
        conn.commit()

def get_admin_role(guild_id: str):
    with DBConnection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM config WHERE guild_id = %s AND key = 'wow_manager_role'", (guild_id,))
        row = cursor.fetchone()
        if row:
            return int(row[0])
        return None

def add_match_stats(guild_id: str, player_kills):
    not_found = []
    with DBConnection() as conn:
        cursor = conn.cursor()
        for discord_id, kills in player_kills:
            cursor.execute('SELECT 1 FROM players WHERE guild_id = %s AND discord_id = %s', (guild_id, str(discord_id)))
            if cursor.fetchone():
                cursor.execute('''
                    UPDATE players
                    SET weekly_matches = weekly_matches + 1,
                        lifetime_matches = lifetime_matches + 1,
                        weekly_kills = weekly_kills + %s,
                        lifetime_kills = lifetime_kills + %s
                    WHERE discord_id = %s
                ''', (kills, kills, guild_id, str(discord_id)))
            else:
                not_found.append(str(discord_id))
        conn.commit()
    return not_found

def get_player(guild_id: str, discord_id):
    with DBConnection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute('SELECT * FROM players WHERE guild_id = %s AND discord_id = %s', (str(discord_id),))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

def reset_weekly(guild_id: str):
    with DBConnection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE players SET weekly_matches = 0, weekly_kills = 0 WHERE guild_id = %s', (guild_id,))
        conn.commit()

def add_player(guild_id: str, discord_id, ign, team):
    try:
        with DBConnection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO players (discord_id, bgmi_ign, team_name)
                VALUES (%s, %s, %s)
            ''', (guild_id, str(discord_id), ign, team))
            conn.commit()
            return True
    except psycopg2.IntegrityError:
        return False

def remove_player(guild_id: str, discord_id):
    with DBConnection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM players WHERE guild_id = %s AND discord_id = %s', (str(discord_id),))
        if cursor.rowcount > 0:
            conn.commit()
            return True
        return False

def update_ign(guild_id: str, discord_id, ign):
    with DBConnection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE players SET bgmi_ign = %s WHERE guild_id = %s AND discord_id = %s', (ign, guild_id, str(discord_id)))
        if cursor.rowcount > 0:
            conn.commit()
            return True
        return False

def set_team(guild_id: str, discord_id, team):
    with DBConnection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE players SET team_name = %s WHERE guild_id = %s AND discord_id = %s', (team, guild_id, str(discord_id)))
        if cursor.rowcount > 0:
            conn.commit()
            return True
        return False

def reset_overall(guild_id: str):
    """Zero out all lifetime stats and clear match history. Weekly untouched."""
    with DBConnection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE players SET lifetime_matches = 0, lifetime_kills = 0 WHERE guild_id = %s', (guild_id,))
        cursor.execute('DELETE FROM match_history WHERE guild_id = %s', (guild_id,))
        conn.commit()

def get_weekly_leaderboard(guild_id: str):
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
    for t in teams:
        teams[t].sort(key=lambda x: x['kills'], reverse=True)
    return teams

def get_lifetime_leaderboard(guild_id: str):
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

# ══════════════════════════════════════════════════════════
#   NEW: MATCH HISTORY
# ══════════════════════════════════════════════════════════

def log_match_history(guild_id: str, player_kills: list, match_date: str):
    """Log per-match kills into match_history for a given date."""
    with DBConnection() as conn:
        cursor = conn.cursor()
        for discord_id, kills in player_kills:
            cursor.execute('SELECT 1 FROM players WHERE guild_id = %s AND discord_id = %s', (guild_id, str(discord_id)))
            if cursor.fetchone():
                cursor.execute(
                    'INSERT INTO match_history (guild_id, discord_id, kills, match_date) VALUES (%s, %s, %s, %s)',
                    (guild_id, str(discord_id), kills, match_date)
                )
        conn.commit()

def get_match_history(guild_id: str, limit: int = 5) -> list:
    """Returns last N match entries grouped by logged_at timestamp."""
    with DBConnection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        # Get distinct match sessions (group by date + minute logged)
        cursor.execute('''
            SELECT
                mh.match_date,
                mh.logged_at,
                p.bgmi_ign,
                mh.kills
            FROM match_history mh
            JOIN players p ON p.guild_id = mh.guild_id AND p.discord_id = mh.discord_id\n            WHERE mh.guild_id = %s
            ORDER BY mh.logged_at DESC
            LIMIT %s
        ''', (limit * 20,))  # fetch enough rows
        rows = cursor.fetchall()

    # Group by (match_date, minute) to reconstruct sessions
    from collections import OrderedDict
    sessions = OrderedDict()
    for row in rows:
        key = row['match_date'] + '_' + row['logged_at'].strftime('%H:%M')
        if key not in sessions:
            sessions[key] = {
                'date': row['match_date'],
                'logged_at': row['logged_at'].strftime('%d %b %Y %H:%M'),
                'players': []
            }
        sessions[key]['players'].append({
            'ign': row['bgmi_ign'],
            'kills': row['kills']
        })

    # Sort each session players by kills desc
    result = []
    for s in sessions.values():
        s['players'].sort(key=lambda x: x['kills'], reverse=True)
        result.append(s)
        if len(result) >= limit:
            break
    return result

# ══════════════════════════════════════════════════════════
#   NEW: TEAM VS TEAM
# ══════════════════════════════════════════════════════════

def get_team_stats(guild_id: str) -> list:
    """Returns weekly stats grouped per team (non-Bench)."""
    with DBConnection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute('''
            SELECT
                team_name,
                COUNT(*) AS player_count,
                SUM(weekly_kills) AS total_kills,
                SUM(weekly_matches) AS total_matches
            FROM players
            WHERE LOWER(team_name) != 'bench'
            GROUP BY team_name
            ORDER BY total_kills DESC
        ''')
        rows = cursor.fetchall()
    result = []
    for row in rows:
        matches = row['total_matches'] or 0
        kills   = row['total_kills'] or 0
        result.append({
            'team':    row['team_name'],
            'players': row['player_count'],
            'kills':   kills,
            'matches': matches,
            'avg':     round(kills / matches, 2) if matches > 0 else 0.0
        })
    return result

# ══════════════════════════════════════════════════════════
#   NEW: PERSONAL STATS
# ══════════════════════════════════════════════════════════

def get_personal_stats(guild_id: str, discord_id: str) -> dict | None:
    """Returns full stats for a single player including lifetime rank."""
    with DBConnection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute('SELECT * FROM players WHERE guild_id = %s AND discord_id = %s', (str(discord_id),))
        row = cursor.fetchone()
        if not row:
            return None
        player = dict(row)

        # Get lifetime rank
        cursor.execute('''
            SELECT COUNT(*) + 1 AS rank
            FROM players
            WHERE lifetime_kills > %s
        ''', (player['lifetime_kills'],))
        rank_row = cursor.fetchone()
        player['lifetime_rank'] = rank_row['rank'] if rank_row else '?'

        # Best single match kills
        cursor.execute('''
            SELECT MAX(kills) AS best
            FROM match_history
            WHERE discord_id = %s
        ''', (str(discord_id),))
        best_row = cursor.fetchone()
        player['best_match'] = best_row['best'] if best_row and best_row['best'] else 0

    l_matches = player['lifetime_matches'] or 0
    l_kills   = player['lifetime_kills'] or 0
    w_matches = player['weekly_matches'] or 0
    w_kills   = player['weekly_kills'] or 0

    return {
        'ign':            player['bgmi_ign'],
        'team':           player['team_name'],
        'lifetime_rank':  player['lifetime_rank'],
        'lifetime_kills': l_kills,
        'lifetime_matches': l_matches,
        'lifetime_avg':   round(l_kills / l_matches, 2) if l_matches > 0 else 0.0,
        'weekly_kills':   w_kills,
        'weekly_matches': w_matches,
        'weekly_avg':     round(w_kills / w_matches, 2) if w_matches > 0 else 0.0,
        'best_match':     player['best_match'],
    }

# ══════════════════════════════════════════════════════════
#   NEW: WEEKLY WINNER
# ══════════════════════════════════════════════════════════

def get_weekly_winner(guild_id: str) -> dict | None:
    """Returns the player with highest weekly kills."""
    with DBConnection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute('''
            SELECT discord_id, bgmi_ign, team_name, weekly_kills, weekly_matches
            FROM players
            WHERE weekly_kills > 0
            ORDER BY weekly_kills DESC
            LIMIT 1
        ''')
        row = cursor.fetchone()
    if not row:
        return None
    matches = row['weekly_matches'] or 0
    kills   = row['weekly_kills'] or 0
    return {
        'discord_id': row['discord_id'],
        'ign':     row['bgmi_ign'],
        'team':    row['team_name'],
        'kills':   kills,
        'matches': matches,
        'avg':     round(kills / matches, 2) if matches > 0 else 0.0
    }

# ══════════════════════════════════════════════════════════
#   NEW: DAILY MVP
# ══════════════════════════════════════════════════════════

def get_daily_mvp(guild_id: str, date: str) -> dict | None:
    """Returns player with highest total kills on the given date."""
    with DBConnection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute('''
            SELECT
                p.bgmi_ign,
                p.team_name,
                mh.discord_id,
                SUM(mh.kills)  AS total_kills,
                COUNT(mh.id)   AS matches_today
            FROM match_history mh
            JOIN players p ON p.guild_id = mh.guild_id AND p.discord_id = mh.discord_id\n            WHERE mh.guild_id = %s
            WHERE mh.match_date = %s
            GROUP BY mh.discord_id, p.bgmi_ign, p.team_name
            ORDER BY total_kills DESC, matches_today DESC
            LIMIT 1
        ''', (date,))
        row = cursor.fetchone()
    if not row:
        return None
    return {
        'discord_id': row['discord_id'],
        'ign':     row['bgmi_ign'],
        'team':    row['team_name'],
        'kills':   row['total_kills'],
        'matches': row['matches_today'],
    }

def get_daily_summary(guild_id: str, date: str) -> list:
    """Returns all players' kills for a given date, sorted by kills desc."""
    with DBConnection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute('''
            SELECT
                p.bgmi_ign,
                p.team_name,
                SUM(mh.kills)  AS total_kills,
                COUNT(mh.id)   AS matches_today
            FROM match_history mh
            JOIN players p ON p.guild_id = mh.guild_id AND p.discord_id = mh.discord_id\n            WHERE mh.guild_id = %s
            WHERE mh.match_date = %s
            GROUP BY mh.discord_id, p.bgmi_ign, p.team_name
            ORDER BY total_kills DESC
        ''', (date,))
        rows = cursor.fetchall()
    return [
        {
            'ign':     row['bgmi_ign'],
            'team':    row['team_name'],
            'kills':   row['total_kills'],
            'matches': row['matches_today'],
        }
        for row in rows
    ]

if db_pool:
    init_db()
# ══════════════════════════════════════════════════════════
#   NEW: PLAYING LINEUP
# ══════════════════════════════════════════════════════════

def set_playing_lineup(guild_id: str, team_name: str, discord_ids: list):
    with DBConnection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM playing_lineup WHERE guild_id = %s AND LOWER(team_name) = %s", (guild_id, team_name.lower()))
        for d_id in discord_ids:
            cursor.execute("INSERT INTO playing_lineup (guild_id, team_name, discord_id) VALUES (%s, %s, %s)", (guild_id, team_name, str(d_id)))
        conn.commit()

def get_all_playing_lineups(guild_id: str) -> dict:
    with DBConnection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
        cursor.execute('''
            SELECT pl.team_name, p.discord_id, p.bgmi_ign
            FROM playing_lineup pl
            JOIN players p ON p.guild_id = pl.guild_id AND p.discord_id = pl.discord_id
            WHERE pl.guild_id = %s
            ORDER BY pl.team_name, p.bgmi_ign
        ''', (guild_id,))
        rows = cursor.fetchall()
        lineups = {}
        for row in rows:
            team = row['team_name']
            if team not in lineups:
                lineups[team] = []
            lineups[team].append({'discord_id': row['discord_id'], 'ign': row['bgmi_ign']})
        return lineups
