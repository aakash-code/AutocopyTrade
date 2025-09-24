# AutocopyTrade - Multi-Broker Edition

This project is a trade replicator that allows trades from a master trading account to be replicated across multiple child accounts. This version has been refactored to support multiple brokers, a database backend, and a full web-based UI for control.

## Features

- **Database Backend:** All account and settings configuration is stored in a robust SQLite database, not a JSON file.
- **Multi-Broker Support:** Core logic is architected to support different brokers (Zerodha, Dhan).
- **Stable, Selenium-Free Login:** The Zerodha login process uses direct web requests, making it fast and reliable.
- **Full Web UI:** A comprehensive web dashboard (`app.py`) allows you to manage all aspects of the application:
    - Start/Stop the replication engine.
    - View live status of all broker connections.
    - Manage all your accounts (Add, Edit, Delete, Set Master, Enable/Disable).
    - Map instruments between different brokers.
    - Manage global application settings.
    - View a historical log of all trades.

## How It Works

The application consists of two main parts:
1.  **Trade Replication Engine (`main.py`):** This is the core script that reads its configuration from the database, programmatically logs into the accounts, listens for order updates on the master account's websocket, and replicates the trades to the child accounts.
2.  **Web Dashboard (`app.py`):** This is a Flask web server that provides the UI to control the engine and manage all settings in the database.

## Setup and Installation

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Create Encryption Key
The application requires an encryption key to secure your credentials. This key is stored in a `.env` file.
Run the following command to generate the key and the file:
```bash
python manage_credentials.py --generate-key
```
This will create a `.env` file in the project root. **Keep this file secure and do not share it.**

### 3. Initialize the Database
The first time you run the application, it will automatically create a `trader.db` file, which will store all your data. You can also run this command manually to create it:
```bash
python database.py
```

### 4. (Optional) Migrate from `config.json`
If you have an existing `config.json` from a previous version, you can migrate your accounts and settings into the new database by running:
```bash
python migrate_to_db.py
```

### 5. Add Accounts via the Web UI
There is no need to manually edit any configuration files. All account management is now done through the web interface.

## How to Run

1.  **Start the Web Dashboard:**
    ```bash
    python app.py
    ```
    This will start a web server, usually at `http://127.0.0.1:5001`.

2.  **Open the Dashboard and Add Accounts:**
    Navigate to `http://127.0.0.1:5001` in your browser. Go to the "Manage Accounts" page to add your master and child accounts. Remember to use the `manage_credentials.py` script to encrypt your passwords and TOTP secrets before entering them into the web form.

3.  **Start the Replicator:**
    From the main dashboard, click the "Start Replicator" button. This will launch the `main.py` script in the background. Check the `replicator.log` file for detailed logs.

## Current Status & Limitations
- **Dhan Implementation:** The `DhanBroker` is a partial implementation. It can connect and receive order updates. However, placing and modifying orders will require a "translation layer" to map instrument identifiers and API parameters between Zerodha and Dhan. The Instrument Mapping UI is the first step towards building this.
- **Error Handling:** The error handling is basic. A production-ready system would require more robust error handling and recovery mechanisms.
