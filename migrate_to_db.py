import json
import database
from utils import read_config

def migrate():
    """
    Migrates data from config.json to the SQLite database.
    This is a one-time operation.
    """
    print("Starting migration from config.json to trader.db...")

    # 1. Initialize the database
    database.init_db()

    # 2. Read the old config file
    config = read_config()
    if not config:
        print("config.json not found or is empty. Nothing to migrate.")
        return

    # 3. Migrate accounts
    print("Migrating accounts...")
    accounts_migrated = 0

    # Get all accounts from the new structure
    all_accounts = config.get('ACCOUNTS', {})
    master_account_name = config.get('MASTER_ACCOUNT_NAME')

    for name, account_details in all_accounts.items():
        is_master = (name == master_account_name)

        # The database function expects the config part of the account
        # We need to separate the keys that are columns in the db from the json blob
        db_columns = ['broker', 'enabled']
        config_blob = {k: v for k, v in account_details.items() if k not in db_columns}

        success = database.add_account(
            name=name,
            broker=account_details['broker'],
            config_dict=config_blob,
            is_master=is_master,
            enabled=True if account_details.get('enabled', 'Y') == 'Y' else False
        )
        if success:
            accounts_migrated += 1
            print(f"  - Migrated account: {name}")

    print(f"Migrated {accounts_migrated} accounts.")

    # 4. Migrate settings
    print("Migrating settings...")
    donotprocessprod = config.get('DONOTPROCESSPROD', [])
    database.set_setting('DONOTPROCESSPROD', donotprocessprod)
    print("  - Migrated DONOTPROCESSPROD setting.")

    print("\nMigration complete!")
    print("You can now remove the config.json file if you wish, as it is no longer used.")

if __name__ == '__main__':
    migrate()
