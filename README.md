# AutocopyTrade - Multi-Broker Edition

This project is a trade replicator that allows trades from a master trading account to be replicated across multiple child accounts. This version has been refactored to support multiple brokers (initially Zerodha and Dhan) and includes a web-based UI for control.

## Features

- **Multi-Broker Support:** Core logic is architected to support different brokers. Comes with a full implementation for Zerodha and a partial implementation for Dhan.
- **Web-Based UI:** A simple web dashboard (`app.py`) allows you to start, stop, and manage the trade replication engine from your browser.
- **Web-Based Account Management:** Add, edit, and delete child accounts directly from the web interface, no more manual `config.json` editing.
- **Secure Credential Management:** A utility script (`manage_credentials.py`) is provided to encrypt your passwords and TOTP secrets.
- **Extensible Architecture:** The new structure (`brokers` package, `main.py` engine, `app.py` UI) is modular and easier to extend than the original script.

## How It Works

The application consists of two main parts:
1.  **Trade Replication Engine (`main.py`):** This is the core script that connects to the master and child broker accounts, listens for order updates on the master account via a websocket, and replicates the trades to the child accounts.
2.  **Web Dashboard (`app.py`):** This is a Flask web server that provides a simple UI to start and stop the replication engine. It runs `main.py` as a background process.

## Setup and Installation

### 1. Install Dependencies

First, install the required Python packages:
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

### 3. Configure Your Accounts (`config.json`)

Create a `config.json` file in the project root. This file contains the credentials for your master and child accounts. Use the template below.

**Important:** You must encrypt your `password` and `TOPTSecret` values before placing them in the config.

### 4. Encrypt Your Credentials

Use the `manage_credentials.py` script to encrypt your password and your Zerodha TOTP secret string.

```bash
# Encrypt your password
python manage_credentials.py --encrypt "YOUR_PASSWORD"

# Encrypt your TOTP secret
python manage_credentials.py --encrypt "YOUR_TOTP_SECRET"
```

The script will output the encrypted value. Copy and paste this value into the `password` and `TOPTSecret` fields in your `config.json`.

### `config.json` Template

```json
{
    "MASTER" :
	{
        "broker"        : "zerodha",
        "userid"        : "YOUR_Z_USERID",
        "password"      : "PASTE_ENCRYPTED_PASSWORD_HERE",
        "APIKey"        : "YOUR_Z_API_KEY",
        "APISecret"     : "YOUR_Z_API_SECRET",
        "loginURL"      : "https://kite.trade/connect/login?api_key=YOUR_Z_API_KEY",
        "TOPTSecret"    : "PASTE_ENCRYPTED_TOTP_SECRET_HERE"
    },
    "CHILD" :
	{
        "Z_CHILD1" :
		{
            "broker"        : "zerodha",
			"userid"        : "YOUR_CHILD_Z_USERID",
            "password"      : "PASTE_ENCRYPTED_PASSWORD_HERE",
            "APIKey"        : "YOUR_CHILD_Z_API_KEY",
            "APISecret"     : "YOUR_CHILD_Z_API_SECRET",
            "loginURL"      : "https://kite.trade/connect/login?api_key=YOUR_CHILD_Z_API_KEY",
            "TOPTSecret"    : "PASTE_ENCRYPTED_TOTP_SECRET_HERE",
            "multiplier"    : 1.0,
			"enabled"       : "Y"
        },
        "DHAN_CHILD1" :
        {
            "broker"        : "dhan",
            "clientID"      : "YOUR_DHAN_CLIENT_ID",
            "accessToken"   : "YOUR_DHAN_ACCESS_TOKEN",
            "multiplier"    : 1.0,
            "enabled"       : "Y"
        }
    },
    "DONOTPROCESSPROD": ["CNC"]
}
```

## How to Run

1.  **Start the Web Dashboard:**
    ```bash
    python app.py
    ```
    This will start a web server, usually at `http://127.0.0.1:5001`.

2.  **Open the Dashboard in Your Browser:**
    Navigate to `http://127.0.0.1:5001` in your web browser.

3.  **Start the Replicator:**
    Click the "Start Replicator" button on the dashboard. This will launch the `main.py` script in the background. The status on the page should update to "Running". Check the `replicator.log` file for detailed logs from the engine.

4.  **Stop the Replicator:**
    Click the "Stop Replicator" button to terminate the background process.

5.  **Manage Accounts:**
    From the main dashboard, click the "Manage Accounts" link. On this page, you can add new child accounts, edit their details, or delete them. Passwords and TOTP secrets will be automatically encrypted when you add or edit an account.

## Current Status & Limitations

- **Web UI:** The UI now includes a functional dashboard for controlling the replicator and a full CRUD (Create, Read, Update, Delete) interface for managing accounts. It does not yet include advanced features like live order tables.
- **Dhan Implementation:** The `DhanBroker` is a partial implementation. It can connect and receive order updates. However, placing and modifying orders will require a "translation layer" to map instrument identifiers and API parameters between Zerodha and Dhan. This is a complex task and is not yet implemented. The code in `brokers/dhan.py` contains detailed comments on the assumptions and the work required.
- **Error Handling:** The error handling is basic. A production-ready system would require more robust error handling and recovery mechanisms.
