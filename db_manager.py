import sqlite3
from datetime import datetime
import os

DB_FILE = "game_database.db"

def get_db_connection():
    """Returns a connection object to the local database file."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    # This magic line allows fetching rows as dictionaries instead of tuples:
    # e.g., row['name'] instead of row[0]
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema on startup if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Game State Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_state (
            id INTEGER PRIMARY KEY CHECK (id = 1), -- Forces a single row game state
            status TEXT NOT NULL,
            expected_players INTEGER,
            actual_players INTEGER,
            game_channel INTEGER,
            checkin_date TEXT,
            checkin_sent INTEGER DEFAULT 0,
            sas_ident INTEGER,
            submitters_see_hints INTEGER DEFAULT 1,
            reveal_timer_at TEXT DEFAULT NULL
        )
    """)

    # 2. Players (Family) Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            partner TEXT,
            playing INTEGER DEFAULT 0,
            is_agent INTEGER DEFAULT 0,
            gives_to INTEGER DEFAULT None,
            route_draw_time TEXT,
            midpoint_feeling TEXT DEFAULT ""
        )
    """)

    # 3. Tasks / Missions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS missions (
            task_id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            details TEXT NOT NULL,
            submitter INTEGER,
            selected INTEGER DEFAULT 0,
            hold_for INTEGER DEFAULT NULL,
            task_eligible INTEGER DEFAULT 0,
            route_eligible INTEGER DEFAULT 0,
            task_active INTEGER DEFAULT 0,
            route_active INTEGER DEFAULT 0,
            is_complete INTEGER DEFAULT 0,
            pending_for INTEGER,
            selection_for INTEGER
        )
    """)

    # 4. Player-to-Task Junction Table (Since a player can have multiple tasks)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_tasks (
            user_id INTEGER,
            task_id INTEGER,
            PRIMARY KEY (user_id, task_id),
            FOREIGN KEY (user_id) REFERENCES players(user_id) ON DELETE CASCADE,
            FOREIGN KEY (task_id) REFERENCES missions(task_id) ON DELETE CASCADE
        )
    """)

    # 5. Streamlined Unlocked Hints Table (Boolean Matrix Model)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_hints (
            user_id INTEGER,
            task_id INTEGER,
            hint_level INTEGER, -- 0, 1, or 2
            PRIMARY KEY (user_id, task_id, hint_level),
            FOREIGN KEY (user_id) REFERENCES players(user_id) ON DELETE CASCADE,
            FOREIGN KEY (task_id) REFERENCES missions(task_id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()
    print("🗄️ SQLite database successfully initialized.")


def save_player_to_db(user_id: int, p_obj):
    """Saves or updates a standard 'person' object inside the database"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Upsert the primary player data
    cursor.execute("""
        INSERT INTO players (user_id, name, email, partner, playing, is_agent, 
                             gives_to, route_draw_time, midpoint_feeling)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            name=excluded.name,
            email=excluded.email,
            partner=excluded.partner,
            playing=excluded.playing,
            is_agent=excluded.is_agent,
            gives_to=excluded.gives_to,
            route_draw_time=excluded.route_draw_time,
            midpoint_feeling=excluded.midpoint_feeling
    """, (
        user_id, p_obj.name, p_obj.email, getattr(p_obj, 'partner', ''),
        int(p_obj.playing), int(getattr(p_obj, 'is_agent', False)), getattr(p_obj, 'gives_to', None),
        getattr(p_obj, 'route_draw_time', None), getattr(p_obj, 'midpoint_feeling', '')
    ))

    # Sync their tasks junction table
    # Clear out old assignments for this user first
    cursor.execute("DELETE FROM player_tasks WHERE user_id = ?", (user_id,))
    # Re-insert their current roster list
    for t_id in getattr(p_obj, 'tasks', []):
        cursor.execute("INSERT OR IGNORE INTO player_tasks (user_id, task_id) VALUES (?, ?)", (user_id, t_id))

    conn.commit()
    conn.close()


def save_game_to_db(bot):
    """Saves or updates the central singleton game state row in the database"""
    if not bot.game:
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    # Formats date objects to strings safely if they exist
    checkin_str = ""
    reveal_str = ""
    if hasattr(bot.game, 'checkin_date') and bot.game.checkin_date:
        # Handles both datetime objects or strings cleanly
        checkin_str = bot.game.checkin_date.strftime("%Y-%m-%d") if hasattr(bot.game.checkin_date, 'strftime') else str(
            bot.game.checkin_date)
        reveal_str = bot.game.reveal_timer_at.strftime("%Y-%m-%d %H:%M:%S") if getattr(bot.game, 'reveal_timer_at',
                                                                                       None) else None

    # Upsert the absolute state under ID row 1
    cursor.execute("""
        INSERT INTO game_state (id, status, expected_players, actual_players,
                                game_channel, checkin_date, checkin_sent, sas_ident, submitters_see_hints,
                                reveal_timer_at)
        VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            status=excluded.status,
            expected_players=excluded.expected_players,
            actual_players=excluded.actual_players,
            game_channel=excluded.game_channel,
            checkin_date=excluded.checkin_date,
            checkin_sent=excluded.checkin_sent,
            sas_ident=excluded.sas_ident,
            submitters_see_hints=excluded.submitters_see_hints,
            reveal_timer_at=excluded.reveal_timer_at
    """, (
        bot.game.status,
        getattr(bot.game, 'expected_players', 0),
        getattr(bot.game, 'actual_players', 0),
        getattr(bot.game, 'game_channel', 0),
        checkin_str,
        int(getattr(bot.game, 'checkin_sent', False)),
        getattr(bot.game, 'sas_ident', None),
        int(getattr(bot.game.submitters_see_hints, 'submitters_see_hints', True)),
        reveal_str
    ))

    conn.commit()
    conn.close()


def load_game_state(bot):
    """Reconstructs the bot.game object from the database row on boot"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM game_state WHERE id = 1")
    row = cursor.fetchone()

    if row:
        # Import your game class dynamically to instantiate it
        from sas_utils import gameState

        # Instantiate your custom class using the saved database status
        g = gameState(row['status'], row['expected_players'], row['actual_players'],
                      row['game_channel'], route_confirms=False)

        g.checkin_sent = bool(row['checkin_sent'])
        g.sas_ident = row['sas_ident'] if 'sas_ident' in row.keys() else None
        g.submitters_see_hints = bool(row['submitters_see_hints'])
        reveal_raw = row['reveal_timer_at']
        g.reveal_timer_at = datetime.strptime(reveal_raw, "%Y-%m-%d %H:%M:%S") if reveal_raw else None



        # Cleanly convert text date records back into usable Python strings/objects
        g.checkin_date = row['checkin_date'] if row['checkin_date'] else None

        bot.game = g
        print("🎮 Game state object successfully loaded.")
    else:
        bot.game = None
        print("🎮 No active game configuration row found in the database. Making one")

    conn.close()

def load_all_players(bot):
    """Reconstructs the bot.family dictionary completely from the SQL database on boot"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM players")
    player_rows = cursor.fetchall()

    bot.family = {}
    for row in player_rows:
        uid = row['user_id']
        # Re-instantiate your custom class object dynamically!
        from sas_utils import person  # Import inline to avoid loops
        p = person(row['name'], row['email'], row['partner'], bool(row['playing']))

        # Hydrate the extra traits
        p.is_agent = bool(row['is_agent'])
        p.midpoint_feeling = row['midpoint_feeling']
        p.gives_to = bool(row['gives_to'])
        p.tasks = []

        # Pull their associated tasks out of the junction table
        cursor.execute("SELECT task_id FROM player_tasks WHERE user_id = ?", (uid,))
        p.tasks = [t_row['task_id'] for t_row in cursor.fetchall()]

        p.hints = load_player_hints(uid)  # Rebuilds the { task_id: { level: True } } map
        p.submissions = load_player_submissions(uid)
        p.selections = load_player_selections(uid)
        bot.family[uid] = p

    conn.close()


def save_mission_to_db(task_id: int, m_obj):
    """Saves or updates an individual mission configuration entry in the database"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO missions (task_id, title, details, submitter, selected, hold_for, task_eligible, route_eligible, 
                              task_active, route_active, is_complete, pending_for, selection_for)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(task_id) DO UPDATE SET
            title=excluded.title,
            selected=excluded.selected,
            hold_for=excluded.hold_for,
            task_active=excluded.task_active,
            route_active=excluded.route_active,
            is_complete=excluded.is_complete,
            pending_for=excluded.pending_for,
            selection_for=excluded.selection_for
    """, (
        task_id,
        m_obj.title,
        m_obj.details,
        m_obj.submitter,
        int(getattr(m_obj, 'selected', False)),
        getattr(m_obj, 'hold_for', None),
        int(getattr(m_obj, 'task_eligible', False)),
        int(getattr(m_obj, 'route_eligible', False)),
        int(getattr(m_obj, 'task_active', False)),
        int(getattr(m_obj, 'route_active', False)),
        int(getattr(m_obj, 'is_complete', False)),
        getattr(m_obj, 'pending_for', None),
        getattr(m_obj, 'selection_for', None),
    ))

    conn.commit()
    conn.close()


def load_all_missions(bot):
    """Reconstructs the global bot.missions reference dictionary on boot"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM missions")
    rows = cursor.fetchall()

    bot.missions = {}
    for row in rows:
        tid = row['task_id']

        # Import your individual task reference class definition
        from sas_utils import mission

        # Instantiate the object shell
        m = mission(row['title'], row['details'], row['submitter'],
                    bool(row['task_eligible']), bool(row['route_eligible']))
        # m.details =
        # m.submitter =
        m.selected = bool(row['selected'])
        m.hold_for = row['hold_for'] if row['hold_for'] is None else int(row['hold_for'])
        # m.task_eligible =
        # m.route_eligible =
        m.task_active = bool(row['task_active'])
        m.route_active = bool(row['route_active'])
        m.is_complete = bool(row['is_complete'])
        m.pending_confirm = row['pending_for'] if row['pending_for'] is None else int(row['pending_for'])
        m.selection_for = row['selection_for'] if row['selection_for'] is None else int(row['selection_for'])

        bot.missions[tid] = m

    conn.close()
    print(f"📋 Loaded {len(bot.missions)} mission records into central memory reference dictionary.")


def delete_mission_from_db(task_id: int):
    """Deletes a mission row permanently from the database file"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # This single command deletes the mission row.
    # Because of 'ON DELETE CASCADE' on your player_tasks junction table,
    # SQLite will automatically clean up any active player assignments too!
    cursor.execute("DELETE FROM missions WHERE task_id = ?", (task_id,))

    conn.commit()
    conn.close()

def get_all_pending_tasks() -> list:
    """Returns a flat list of all task_ids where pending_confirm is True"""
    print("Ho")
    conn = get_db_connection()
    cursor = conn.cursor()
    print("Hp")
    # Query for rows where the integer flag matches True (1)
    cursor.execute("""
        SELECT task_id 
        FROM missions 
        WHERE pending_for is not NULL
    """)

    rows = cursor.fetchall()
    conn.close()
    print("Hey")
    # Extract the integers out of the Row objects into a flat list
    # e.g., [4, 12, 19]
    return [row['task_id'] for row in rows]



def get_all_submitted_tasks(user_id: int) -> list:
    """Returns a flat list of all task_ids where pending_confirm is True"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Query for rows where the integer flag matches True (1)
    cursor.execute(f"""
        SELECT task_id 
        FROM missions 
        WHERE submitter = ?
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()

    # Extract the integers out of the Row objects into a flat list
    # e.g., [4, 12, 19]
    return [row['task_id'] for row in rows]

def get_all_selections_tasks(user_id: int) -> list:
    """Returns a flat list of all task_ids where pending_confirm is True"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Query for rows where the integer flag matches True (1)
    cursor.execute(f"""
        SELECT task_id 
        FROM missions 
        WHERE selection_for = ?
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()

    # Extract the integers out of the Row objects into a flat list
    # e.g., [4, 12, 19]
    return [row['task_id'] for row in rows]

def get_all_held_tasks(user_id: int) -> list:
    """Returns a flat list of all task_ids where pending_confirm is True"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Query for rows where the integer flag matches True (1)
        cursor.execute("""
            SELECT task_id 
            FROM missions 
            WHERE hold_for = ? 
                AND (is_complete = 0 OR is_complete = '0' OR is_complete IS NULL)
        """, (user_id,))
        rows = cursor.fetchall()
        # Extract the integers out of the Row objects into a flat list
        # e.g., [4, 12, 19]
        print([row[0] for row in rows])
        return [row[0] for row in rows]
    finally:
        cursor.close()
        conn.close()



def save_player_hints_to_db(user_id: int, hints_dict: dict):
    """
    Saves a player's unlocked hint flags to the database.
    hints_dict shape: { task_id: { 0: True/Data, 1: True/Data } }
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Clear old flags to keep the grid synced
    cursor.execute("DELETE FROM player_hints WHERE user_id = ?", (user_id,))

    # Log each unlocked level as a lean row entry
    for task_id, levels in hints_dict.items():
        for hint_level in levels.keys():
            cursor.execute("""
                INSERT INTO player_hints (user_id, task_id, hint_level)
                VALUES (?, ?, ?)
            """, (user_id, int(task_id), int(hint_level)))

    conn.commit()

    conn.close()


def load_player_submissions(user_id: int) -> dict:
    """
    Reconstructs the active nested dictionary structure for a player's memory object.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT task_id FROM missions WHERE submitter = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    return [int(r['task_id']) for r in rows]

def load_player_selections(user_id: int) -> dict:
    """
    Reconstructs the active nested dictionary structure for a player's memory object.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT task_id FROM missions WHERE selection_for = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    return [int(r['task_id']) for r in rows]


def load_player_hints(user_id: int) -> dict:
    """
    Reconstructs the active nested dictionary structure for a player's memory object.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT task_id, hint_level FROM player_hints WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    reconstructed_hints = {}
    for row in rows:
        t_id = row['task_id']
        lvl = row['hint_level']

        if t_id not in reconstructed_hints:
            reconstructed_hints[t_id] = {}

        # Set the flag to True or a placeholder value so your original code
        # knows this specific tier index is unlocked and available!
        reconstructed_hints[t_id][lvl] = True

    return reconstructed_hints


def hydrate_bot_memory(bot):
    """Coordinates a complete sequential memory assembly from the SQLite cache file"""
    # 1. Structural schema verification check
    init_db()

    # 2. Run sequential loaders across all distinct data matrices
    load_game_state(bot)
    load_all_missions(bot)
    load_all_players(bot)  # The original function we wrote together earlier

def clear_all_database_data():
    """Wipes all rows from every table cleanly without deleting the database file structure."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Disable foreign key constraints temporarily so things delete smoothly
    cursor.execute("PRAGMA foreign_keys = OFF;")

    # Clear the data out of every table
    cursor.execute("DELETE FROM player_hints;")
    cursor.execute("DELETE FROM player_tasks;")
    cursor.execute("DELETE FROM players;")
    cursor.execute("DELETE FROM missions;")
    cursor.execute("DELETE FROM game_state;")

    # Re-enable foreign key protections
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. COMMIT THE DELETIONS FIRST! This closes the open transaction block.
    conn.commit()

    # 2. THE FIX: Set autocommit mode temporarily so VACUUM can run on its own
    old_isolation = conn.isolation_level
    conn.isolation_level = None  # Turns on autocommit mode

    try:
        # Optimize and shrink the database file size back down to zero safely
        cursor.execute("VACUUM;")
    finally:
        # Restore original connection settings
        conn.isolation_level = old_isolation

    conn.close()