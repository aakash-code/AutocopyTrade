import os
import sys
import dotenv
from cryptography.fernet import Fernet

# Load environment variables from .env file
dotenv.load_dotenv()

# Get the encryption key from environment variables
mysecret = dotenv.get('key')
if not mysecret:
    print('Environment variable "key" not found. Please create a .env file with a key. Exiting.')
    sys.exit()

# It's better practice to ensure the key is in bytes
# The key must be url-safe base64-encoded
# Fernet.generate_key() can be used to create one
try:
    mysecret = mysecret.encode()
    f = Fernet(mysecret)
except ValueError as e:
    print(f"Invalid encryption key: {e}. The key must be a URL-safe base64-encoded 32-byte key.")
    sys.exit()


def decrypt_value(encrypted_value: str) -> str:
    """
    Decrypts an encrypted string value using the secret key from the environment.
    """
    try:
        encrypted_bytes = encrypted_value.encode()
        decrypted_bytes = f.decrypt(encrypted_bytes)
        return decrypted_bytes.decode()
    except Exception as e:
        print(f"Error decrypting value: {e}")
        # Depending on the desired behavior, you might want to exit or return an empty string
        return ""

def encrypt_value(value: str) -> str:
    """
    Encrypts a string value using the secret key from the environment.
    """
    try:
        value_bytes = value.encode()
        encrypted_bytes = f.encrypt(value_bytes)
        return encrypted_bytes.decode()
    except Exception as e:
        print(f"Error encrypting value: {e}")
        return ""
