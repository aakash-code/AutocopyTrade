import sqlite3
import json

DATABASE_NAME = 'trader.db'

def get_db_connection():
    """Establishes a connection to the database."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database and creates tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create accounts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            name TEXT PRIMARY KEY,
            broker TEXT NOT NULL,
            config_json TEXT NOT NULL,
            is_master BOOLEAN NOT NULL DEFAULT 0,
            enabled BOOLEAN NOT NULL DEFAULT 1
        )
    ''')

    # Create settings table (key-value store)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')

    # Check if default settings exist
    cursor.execute("SELECT value FROM settings WHERE key = 'DONOTPROCESSPROD'")
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?)",
                       ('DONOTPROCESSPROD', json.dumps(['CNC'])))

    conn.commit()
    conn.close()
    print("Database initialized successfully.")

# --- Account Functions ---

def add_account(name, broker, config_dict, is_master=False, enabled=True):
    """Adds a new account to the database."""
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO accounts (name, broker, config_json, is_master, enabled) VALUES (?, ?, ?, ?, ?)",
            (name, broker, json.dumps(config_dict), is_master, enabled)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        print(f"Error: Account with name '{name}' already exists.")
        return False
    finally:
        conn.close()
    return True

def get_all_accounts():
    """Retrieves all accounts from the database."""
    conn = get_db_connection()
    accounts_cursor = conn.execute("SELECT * FROM accounts").fetchall()
    conn.close()

    accounts = {}
    for row in accounts_cursor:
        account_name = row['name']
        accounts[account_name] = {
            'broker': row['broker'],
            'is_master': row['is_master'],
            'enabled': row['enabled']
        }
        # Unpack the config JSON into the main dict
        accounts[account_name].update(json.loads(row['config_json']))

    return accounts

def get_master_account():
    """Retrieves the master account from the database."""
    conn = get_db_connection()
    master_row = conn.execute("SELECT * FROM accounts WHERE is_master = 1").fetchone()
    conn.close()
    if master_row:
        account = dict(master_row)
        account.update(json.loads(account['config_json']))
        return account
    return None

def set_master_account(name):
    """Sets a given account as the master."""
    conn = get_db_connection()
    try:
        # First, ensure no other account is master
        conn.execute("UPDATE accounts SET is_master = 0")
        # Then, set the new master
        conn.execute("UPDATE accounts SET is_master = 1 WHERE name = ?", (name,))
        conn.commit()
    except Exception as e:
        print(f"Error setting master account: {e}")
        return False
    finally:
        conn.close()
    return True

def delete_account(name):
    """Deletes an account from the database."""
    conn = get_db_connection()
    conn.execute("DELETE FROM accounts WHERE name = ?", (name,))
    conn.commit()
    conn.close()

def update_account_enabled(name, enabled):
    """Updates the enabled status of an account."""
    conn = get_db_connection()
    conn.execute("UPDATE accounts SET enabled = ? WHERE name = ?", (enabled, name))
    conn.commit()
    conn.close()

def update_account(name, config_dict, enabled):
    """Updates the config and enabled status for an account."""
    conn = get_db_connection()
    conn.execute(
        "UPDATE accounts SET config_json = ?, enabled = ? WHERE name = ?",
        (json.dumps(config_dict), enabled, name)
    )
    conn.commit()
    conn.close()

# --- Settings Functions ---

def get_setting(key):
    """Retrieves a setting value from the database."""
    conn = get_db_connection()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return json.loads(row['value']) if row else None

def set_setting(key, value):
    """Sets a setting value in the database."""
    conn = get_db_connection()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, json.dumps(value)))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
