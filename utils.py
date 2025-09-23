import os
import sys
import dotenv
from cryptography.fernet import Fernet

# Load environment variables from .env file
dotenv.load_dotenv()

# --- Fernet Encryption Setup ---
# Initialize f as None. It will be created only if a valid key is found.
f = None
mysecret = os.getenv('key')

if mysecret:
    try:
        f = Fernet(mysecret.encode())
    except Exception as e:
        print(f"Warning: Could not initialize encryption with key from .env file. Error: {e}")
        f = None
else:
    # This is not an error, it just means a key needs to be generated.
    print("No encryption key found in .env file. You can generate one with `manage_credentials.py --generate-key`.")


def decrypt_value(encrypted_value: str) -> str:
    """
    Decrypts an encrypted string value using the secret key from the environment.
    """
    if not f:
        print("Cannot decrypt: Encryption service not initialized.")
        return ""
    if not encrypted_value:
        return ""

    try:
        encrypted_bytes = encrypted_value.encode()
        decrypted_bytes = f.decrypt(encrypted_bytes)
        return decrypted_bytes.decode()
    except Exception as e:
        print(f"Error decrypting value: {e}")
        return ""

import json

CONFIG_FILE = 'config.json'

def read_config():
    """
    Reads the configuration from config.json.
    """
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {CONFIG_FILE} not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode {CONFIG_FILE}. Please check its format.")
        return None

def write_config(config_data):
    """
    Writes the configuration data to config.json.
    """
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=4)
        return True
    except IOError as e:
        print(f"Error writing to {CONFIG_FILE}: {e}")
        return False

def encrypt_value(value: str) -> str:
    """
    Encrypts a string value using the secret key from the environment.
    """
    if not f:
        print("Cannot encrypt: Encryption service not initialized. Please generate a key first.")
        return ""
    if not value:
        return ""

    try:
        value_bytes = value.encode()
        encrypted_bytes = f.encrypt(value_bytes)
        return encrypted_bytes.decode()
    except Exception as e:
        print(f"Error encrypting value: {e}")
        return ""
