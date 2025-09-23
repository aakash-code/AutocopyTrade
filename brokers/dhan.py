import logging
import time
from dhanhq import DhanContext, dhanhq, OrderUpdate
from brokers.base import Broker

class DhanBroker(Broker):
    """
    Implementation of the Broker interface for Dhan.
    """

    def __init__(self, config):
        super().__init__(config)
        self.dhan_client = None
        self.order_ws = None

    def login(self):
        """
        Initializes the Dhan client.
        """
        try:
            logging.info(f"Initializing Dhan client for {self.config['clientID']}")
            dhan_context = DhanContext(self.config['clientID'], self.config['accessToken'])
            self.dhan_client = dhanhq(dhan_context)
            # Test the connection by fetching fund limits
            if self.dhan_client.get_fund_limits():
                 print(f"Dhan client for {self.config['clientID']} initialized successfully.")
                 self.client = self.dhan_client
                 return True
            else:
                logging.error(f"Failed to verify Dhan client for {self.config['clientID']}.")
                return False
        except Exception as e:
            logging.error(f"Failed to initialize Dhan client for {self.config['clientID']}: {e}")
            return False

    def place_order(self, order_data):
        """
        Places an order using the Dhan API.

        IMPORTANT NOTE: This implementation currently assumes that the `order_data`
        dictionary is already formatted with Dhan-specific parameters. For example,
        it assumes `order_data['tradingsymbol']` contains a Dhan `security_id`.
        A complete implementation requires a "translation layer" to map parameters
        from a generic format (like Zerodha's) to Dhan's format.
        """
        try:
            # Example of a simple translation for transaction_type
            transaction_type_map = {'BUY': self.dhan_client.BUY, 'SELL': self.dhan_client.SELL}
            translated_transaction_type = transaction_type_map.get(order_data['transaction_type'])

            if not translated_transaction_type:
                logging.error(f"Unknown transaction type: {order_data['transaction_type']}")
                return None

            # This is a placeholder for a real translation layer.
            # A real implementation would need to map exchanges, order types, products, and most importantly, instruments.
            dhan_order_data = {
                'security_id': str(order_data['tradingsymbol']), # This is the biggest assumption.
                'exchange_segment': self.dhan_client.NSE, # This is hardcoded and needs mapping.
                'transaction_type': translated_transaction_type,
                'quantity': order_data['quantity'],
                'order_type': self.dhan_client.MARKET, # This is hardcoded and needs mapping.
                'product_type': self.dhan_client.INTRA, # This is hardcoded and needs mapping.
                'price': order_data.get('price', 0)
            }

            response = self.dhan_client.place_order(**dhan_order_data)

            if response and response.get('status') == 'success':
                order_id = response.get('data', {}).get('orderId')
                logging.info(f"Placed Dhan order for {self.config['clientID']}. Order ID: {order_id}")
                return order_id
            else:
                logging.error(f"Failed to place Dhan order for {self.config['clientID']}: {response}")
                return None
        except Exception as e:
            logging.error(f"Error placing Dhan order for {self.config['clientID']}: {e}")
            return None

    def modify_order(self, order_data):
        """
        Modifies an order using the Dhan API.
        NOTE: This method is a placeholder and is not fully implemented.
        A full implementation would require parameter mapping similar to place_order.
        """
        logging.warning(f"Dhan modify_order is not yet implemented for order: {order_data.get('order_id')}")
        # Example:
        # response = self.dhan_client.modify_order(
        #     order_id=order_data['order_id'],
        #     quantity=order_data['quantity'],
        #     price=order_data['price'],
        #     trigger_price=order_data['trigger_price'],
        #     order_type=... # requires mapping
        # )
        return None

    def cancel_order(self, order_data):
        """
        Cancels an order using the Dhan API.
        """
        try:
            response = self.dhan_client.cancel_order(order_data['order_id'])
            if response and response.get('status') == 'success':
                order_id = response.get('data', {}).get('orderId')
                logging.info(f"Cancelled Dhan order for {self.config['clientID']}. Order ID: {order_id}")
                return order_id
            else:
                logging.error(f"Failed to cancel Dhan order for {self.config['clientID']}: {response}")
        except Exception as e:
            logging.error(f"Error cancelling Dhan order for {self.config['clientID']}: {e}")
            return None


    def get_margins(self):
        """
        Retrieves account margins using get_fund_limits.
        """
        try:
            return self.dhan_client.get_fund_limits()
        except Exception as e:
            logging.error(f"Failed to get Dhan margins for {self.config['clientID']}: {e}")
            return None

    def start_websocket(self, on_order_update_callback):
        """
        Starts the websocket connection for real-time order updates.
        """
        if not self.dhan_client:
            logging.error("Dhan client not initialized. Cannot start websocket.")
            return

        def on_update_wrapper(order_data):
            # The Dhan library provides the data in a 'Data' key.
            if isinstance(order_data, dict) and "Data" in order_data:
                on_order_update_callback(self.order_ws, order_data["Data"])
            else:
                # This is to adapt to the on_order_update signature in main.py which expects (ws, data)
                on_order_update_callback(self.order_ws, order_data)

        dhan_context = DhanContext(self.config['clientID'], self.config['accessToken'])
        self.order_ws = OrderUpdate(dhan_context)
        self.order_ws.on_update = on_update_wrapper

        def connect_loop():
            while True:
                try:
                    logging.info("Connecting to Dhan order websocket...")
                    self.order_ws.connect_to_dhan_websocket_sync()
                except Exception as e:
                    logging.error(f"Dhan WebSocket error: {e}. Reconnecting in 5 seconds...")
                    time.sleep(5)

        import threading
        ws_thread = threading.Thread(target=connect_loop, daemon=True)
        ws_thread.start()
        logging.info("Dhan order websocket thread started.")
