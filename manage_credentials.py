import argparse
from utils import encrypt_value, mysecret
from cryptography.fernet import Fernet

def main():
    """
    A command-line tool to encrypt credentials for config.json.
    """
    if not mysecret:
        print("Could not find the encryption key in the .env file.")
        print("Please run `python manage_credentials.py --generate-key` to create one.")
        return

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

    if args.encrypt:
        value_to_encrypt = args.encrypt
        encrypted_value = encrypt_value(value_to_encrypt)
        if encrypted_value:
            print("\n--- Encrypted Value ---")
            print(encrypted_value)
            print("\nCopy this value into your config.json file.")
        else:
            print("Encryption failed. Please check the error messages above.")
    else:
        print("No value provided to encrypt. Use the --encrypt flag.")
        print("Example: python manage_credentials.py --encrypt \"your_password\"")


if __name__ == '__main__':
    main()
