import logging
import sys
import time

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

    # --- Order Management and Replication Logic ---
    order_manager = OrderManager()
    prod_filter = config.get('DONOTPROCESSPROD', [])

    def show_margins():
        print('---Margins--Available----------Used-----Cash Available-----------------------')
        # Assuming get_margins() returns a dict with 'net', 'utilised.debits', 'available.live_balance'
        # This part will need adjustment based on the actual structure of the margin response from each broker
        # For now, we just print the raw margin data.
        print(f"MASTER ({master_broker.config.get('userid', master_broker.config.get('clientID'))}):")
        print(master_broker.get_margins())
        for name, broker in child_brokers.items():
            print(f"{name}:")
            print(broker.get_margins())
        print('----------------------------------------------------')


    def copy_trade_callback(ws, master_order):
        logging.info(f"Order update received: {master_order}")

        if master_order.get('product') in prod_filter:
            logging.info(f"Product type {master_order.get('product')} is in the filter. Ignoring.")
            return

        status = master_order.get('status')
        master_order_id = master_order.get('order_id')

        if status == 'CANCELLED':
            logging.info(f"Cancelling child orders for master order: {master_order_id}")
            child_orders = order_manager.get_child_orders(master_order_id)
            for name, child_broker in child_brokers.items():
                child_order_id = child_orders.get(name)
                if child_order_id:
                    cancel_data = {
                        'variety': master_order['variety'],
                        'order_id': child_order_id
                    }
                    child_broker.cancel_order(cancel_data)

        elif status in ['OPEN', 'TRIGGER PENDING']:
            if order_manager.is_known_order(master_order_id):
                # This is an update to an existing order
                logging.info(f"Updating child orders for master order: {master_order_id}")
                if order_manager.check_if_update(master_order_id, master_order):
                    child_orders = order_manager.get_child_orders(master_order_id)
                    for name, child_broker in child_brokers.items():
                        child_order_id = child_orders.get(name)
                        if child_order_id:
                            multiplier = child_broker.config.get('multiplier', 1.0)
                            modify_data = {
                                'variety': master_order['variety'],
                                'order_id': child_order_id,
                                'quantity': int(round(int(master_order['quantity']) * float(multiplier), 0)),
                                'price': master_order['price'],
                                'trigger_price': master_order['trigger_price'],
                                'order_type': master_order['order_type'],
                                'validity': master_order['validity'],
                            }
                            child_broker.modify_order(modify_data)
                    order_manager.add_master_order(master_order)
                else:
                    logging.info(f"Order {master_order_id} has not changed. Not updating child orders.")
            else:
                # This is a new order
                logging.info(f"Creating child orders for new master order: {master_order_id}")
                order_manager.add_master_order(master_order)
                for name, child_broker in child_brokers.items():
                    multiplier = child_broker.config.get('multiplier', 1.0)
                    place_data = {
                        'variety': master_order['variety'],
                        'exchange': master_order['exchange'],
                        'tradingsymbol': master_order['tradingsymbol'],
                        'transaction_type': master_order['transaction_type'],
                        'quantity': int(round(int(master_order['quantity']) * float(multiplier), 0)),
                        'product': master_order['product'],
                        'order_type': master_order['order_type'],
                        'price': master_order['price'],
                        'trigger_price': master_order['trigger_price'],
                        'validity': master_order['validity'],
                    }
                    child_order_id = child_broker.place_order(place_data)
                    if child_order_id:
                        order_manager.add_child_order(master_order_id, name, child_order_id)

        show_margins()

    # --- Start Websocket and Run Forever ---
    show_margins()
    master_broker.start_websocket(copy_trade_callback)
    print("\n--- Websocket connected. Listening for order updates... ---")

    try:
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
