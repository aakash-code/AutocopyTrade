import pandas as pd
from utils import read_config
from brokers.zerodha import ZerodhaBroker
from brokers.dhan import DhanBroker

def fetch_and_save_instruments():
    """
    Connects to each broker and downloads the latest instrument lists.
    """
    config = read_config()
    if not config:
        print("Could not read config.json. Aborting.")
        return

    # --- Fetch for Zerodha ---
    print("Fetching instruments for Zerodha...")
    zerodha_config = config.get('MASTER')
    if zerodha_config and zerodha_config.get('broker') == 'zerodha':
        zerodha_broker = ZerodhaBroker(zerodha_config)
        if zerodha_broker.login():
            try:
                instruments = zerodha_broker.client.instruments()
                df = pd.DataFrame(instruments)
                df.to_csv('zerodha_instruments.csv', index=False)
                print("Successfully saved zerodha_instruments.csv")
            except Exception as e:
                print(f"Could not fetch Zerodha instruments: {e}")
        else:
            print("Could not log in to Zerodha master account.")
    else:
        print("No Zerodha master account found in config.json.")

    # --- Fetch for Dhan ---
    print("\nFetching instruments for Dhan...")
    dhan_config = None
    for account_name, account_details in config.get('CHILD', {}).items():
        if account_details.get('broker') == 'dhan':
            dhan_config = account_details
            break # Use the first Dhan account found

    if dhan_config:
        dhan_broker = DhanBroker(dhan_config)
        if dhan_broker.login():
            try:
                # The dhanhq library returns a list of dictionaries directly
                instruments = dhan_broker.client.fetch_security_list()
                df = pd.DataFrame(instruments)
                df.to_csv('dhan_instruments.csv', index=False)
                print("Successfully saved dhan_instruments.csv")
            except Exception as e:
                print(f"Could not fetch Dhan instruments: {e}")
        else:
            print("Could not log in to a Dhan child account.")
    else:
        print("No enabled Dhan child account found in config.json.")


if __name__ == '__main__':
    fetch_and_save_instruments()
