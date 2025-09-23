import argparse
from cryptography.fernet import Fernet
# We only import the functions we need inside main, after parsing args
# to avoid initialization errors.

def main():
    """
    A command-line tool to encrypt credentials for config.json.
    """
    parser = argparse.ArgumentParser(description="Encrypt credentials for the trade replicator.")
    parser.add_argument('--encrypt', type=str, help='The value to encrypt (e.g., your password or TOTP secret).')
    parser.add_argument('--generate-key', action='store_true', help='Generate a new encryption key and save it to a .env file.')

    args = parser.parse_args()

    if args.generate_key:
        key = Fernet.generate_key()
        with open('.env', 'w') as f:
            f.write(f"key={key.decode()}\n")
        print("A new encryption key has been generated and saved to .env")
        print("Please do not share this key and keep the .env file secure.")
        return

    # If we are not generating a key, we now need the encryption utilities
    from utils import encrypt_value, f as fernet_instance

    if args.encrypt:
        if not fernet_instance:
             print("Encryption service is not initialized. Please ensure a valid key is in your .env file.")
             return

        value_to_encrypt = args.encrypt
        encrypted_value = encrypt_value(value_to_encrypt)
        if encrypted_value:
            print("\n--- Encrypted Value ---")
            print(encrypted_value)
            print("\nCopy this value into your config.json file.")
        else:
            print("Encryption failed. Please check the error messages above.")
    else:
        print("No action specified. Use --generate-key or --encrypt.")
        print("Example: python manage_credentials.py --encrypt \"your_password\"")


if __name__ == '__main__':
    main()
