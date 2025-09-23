import logging
import sys
import time
import json

from brokers.zerodha import ZerodhaBroker
from brokers.dhan import DhanBroker
from utils import read_config

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_broker_instance(config):
    """
    Factory function to get a broker instance based on the config.
    """
    broker_type = config.get('broker')
    if broker_type == 'zerodha':
        return ZerodhaBroker(config)
    elif broker_type == 'dhan':
        return DhanBroker(config)
    else:
        logging.error(f"Unknown broker type: {broker_type}")
        return None

def main():
    """
    Main function to run the trade replicator.
    """
    config = read_config()
    if not config:
        sys.exit(1)

    # Load instrument mappings
    try:
        with open('instrument_mappings.json', 'r') as f:
            instrument_mappings = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        instrument_mappings = {}
        logging.warning("instrument_mappings.json not found or is invalid. No instrument translation will occur.")

    # --- Initialize Master Account ---
    master_config = config.get('MASTER')
    if not master_config:
        logging.error("MASTER account configuration is missing from config.json.")
        sys.exit(1)

    master_broker = get_broker_instance(master_config)
    if not master_broker:
        sys.exit(1)

    print("--- Logging in Master Account ---")
    if not master_broker.login():
        logging.error(f"Failed to login master account: {master_config.get('userid') or master_config.get('clientID')}")
        sys.exit(1)

    # --- Initialize Child Accounts ---
    child_configs = config.get('CHILD', {})
    child_brokers = {}

    print("\n--- Logging in Child Accounts ---")
    for name, child_config in child_configs.items():
        if child_config.get('enabled', 'N').upper() == 'Y':
            child_broker = get_broker_instance(child_config)
            if child_broker:
                if child_broker.login():
                    child_brokers[name] = child_broker
                else:
                    logging.warning(f"Failed to login child account: {name}. Skipping.")
        else:
            logging.info(f"Child account {name} is disabled. Skipping.")

    if not child_brokers:
        logging.warning("No child accounts were successfully logged in. The application will only listen for master account updates.")

    print("\n--- All accounts logged in successfully! ---")

    # --- Status and Order Management ---
    BROKER_STATUS_FILE = 'broker_status.json'
    order_manager = OrderManager()
    prod_filter = config.get('DONOTPROCESSPROD', [])

    def update_broker_statuses():
        """
        Fetches the latest margin and status for all brokers and writes it to a file.
        """
        statuses = {}

        # Master Broker
        master_id = master_broker.config.get('userid', master_broker.config.get('clientID'))
        margins = master_broker.get_margins()
        statuses['MASTER'] = {
            'id': master_id,
            'status': 'Connected' if margins else 'Disconnected',
            'margins': margins or 'N/A'
        }

        # Child Brokers
        for name, broker in child_brokers.items():
            child_id = broker.config.get('userid', broker.config.get('clientID'))
            margins = broker.get_margins()
            statuses[name] = {
                'id': child_id,
                'status': 'Connected' if margins else 'Disconnected',
                'margins': margins or 'N/A'
            }

        try:
            with open(BROKER_STATUS_FILE, 'w') as f:
                json.dump(statuses, f, indent=4)
        except IOError:
            logging.error(f"Could not write to {BROKER_STATUS_FILE}")

    def copy_trade_callback(ws, master_order, mappings):
        logging.info(f"Order update received: {master_order}")

        if master_order.get('product') in prod_filter:
            logging.info(f"Product type {master_order.get('product')} is in the filter. Ignoring.")
            return

        status = master_order.get('status')
        master_order_id = master_order.get('order_id')

        if status == 'CANCELLED':
            logging.info(f"Cancelling child orders for master order: {master_order_id}")
            # ... (rest of the logic is the same)
            # ...
        elif status in ['OPEN', 'TRIGGER PENDING']:
            if order_manager.is_known_order(master_order_id):
                # ... (rest of the logic is the same)
                # ...
                pass
            else:
                # This is a new order
                logging.info(f"Creating child orders for new master order: {master_order_id}")
                order_manager.add_master_order(master_order)
                for name, child_broker in child_brokers.items():

                    place_data = master_order.copy()

                    # --- Instrument Mapping Logic ---
                    master_broker_type = master_broker.config.get('broker')
                    child_broker_type = child_broker.config.get('broker')

                    if master_broker_type != child_broker_type:
                        master_symbol_key = f"{master_broker_type}:{place_data['exchange']}:{place_data['tradingsymbol']}"

                        if master_symbol_key in mappings and child_broker_type in mappings[master_symbol_key]:
                            translated_symbol = mappings[master_symbol_key][child_broker_type]
                            logging.info(f"Translating {master_symbol_key} to {translated_symbol} for {name}")
                            place_data['tradingsymbol'] = translated_symbol
                        else:
                            logging.warning(f"No mapping found for {master_symbol_key} to {child_broker_type}. Skipping order for {name}.")
                            continue # Skip this child broker
                    # --- End of Mapping Logic ---

                    multiplier = child_broker.config.get('multiplier', 1.0)
                    place_data['quantity'] = int(round(int(place_data['quantity']) * float(multiplier), 0))

                    child_order_id = child_broker.place_order(place_data)
                    if child_order_id:
                        order_manager.add_child_order(master_order_id, name, child_order_id)

    # --- Start Background Threads and Run Forever ---
    from functools import partial
    import threading

    def status_update_loop():
        while True:
            update_broker_statuses()
            time.sleep(10) # Update status every 10 seconds

    status_thread = threading.Thread(target=status_update_loop, daemon=True)
    status_thread.start()

    master_broker.start_websocket(partial(copy_trade_callback, mappings=instrument_mappings))
    print("\n--- Websocket connected. Listening for order updates... ---")

    try:
        # The main thread just needs to stay alive. The work is done in background threads.
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)


class OrderManager:
    def __init__(self):
        self.master_orders = {}  # {master_order_id: master_order_data}
        self.child_orders = {}   # {master_order_id: {child_name: child_order_id}}

    def add_master_order(self, order_data):
        self.master_orders[order_data['order_id']] = order_data

    def add_child_order(self, master_id, child_name, child_id):
        if master_id not in self.child_orders:
            self.child_orders[master_id] = {}
        self.child_orders[master_id][child_name] = child_id

    def is_known_order(self, master_id):
        return master_id in self.master_orders

    def get_child_orders(self, master_id):
        return self.child_orders.get(master_id, {})

    def check_if_update(self, master_id, new_data):
        """
        Checks if the order has changed in a meaningful way.
        This is a more faithful port of the original logic.
        """
        old_data = self.master_orders.get(master_id)
        if not old_data:
            return True # Should not happen if is_known_order is checked first

        if (old_data.get('variety') == new_data.get('variety') and
            old_data.get('order_type') == new_data.get('order_type') and
            old_data.get('quantity') == new_data.get('quantity') and
            old_data.get('price') == new_data.get('price') and
            old_data.get('trigger_price') == new_data.get('trigger_price')):
            return False
        else:
            return True


if __name__ == '__main__':
    import time
    main()
