# Copy Trading Application

This is a copy trading application that allows users to copy trades from a master account to one or more slave accounts on Dhan and Angel One.

## Features

-   Connect to Dhan and Angel One accounts.
-   Add, update, and delete user credentials.
-   Monitor trades in real-time.
-   Copy trades from a master account to slave accounts.

## Project Structure

-   `backend/`: Contains the server-side code.
    -   `dhan/`: Code for interacting with the Dhan API.
    -   `angelone/`: Code for interacting with the Angel One API.
    -   `core/`: Core trading logic.
-   `frontend/`: Contains the client-side code.
-   `config/`: Contains configuration files.
-   `requirements.txt`: Lists the Python dependencies.
-   `README.md`: This file.

## Setup

1.  Install the required dependencies: `pip install -r requirements.txt`
2.  Add your API keys and other credentials to the `config/` directory.
3.  Run the backend server: `uvicorn backend.main:app --reload`
4.  Run the frontend application.
