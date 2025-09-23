import logging
import time
import asyncio
import websockets
import json
from dhanhq import dhanhq

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
            self.dhan_client = dhanhq(self.config['clientID'], self.config['accessToken'])
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
        This is a custom implementation to adapt the v2.0.2 OrderSocket logic.
        """
        if not self.dhan_client:
            logging.error("Dhan client not initialized. Cannot start websocket.")
            return

        class CustomOrderSocket:
            def __init__(self, client_id, access_token, callback):
                self.client_id = client_id
                self.access_token = access_token
                self.order_feed_wss = "wss://api-order-update.dhan.co"
                self.on_update = callback
                self.ws = None

            async def connect_order_update(self):
                async with websockets.connect(self.order_feed_wss) as websocket:
                    self.ws = websocket
                    auth_message = {
                        "LoginReq": {"MsgCode": 42, "ClientId": str(self.client_id), "Token": str(self.access_token)},
                        "UserType": "SELF"
                    }
                    await websocket.send(json.dumps(auth_message))
                    async for message in websocket:
                        data = json.loads(message)
                        if data.get('Type') == 'order_alert' and 'Data' in data:
                            self.on_update(self.ws, data['Data'])

            def connect_to_dhan_websocket_sync(self):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.connect_order_update())
                finally:
                    loop.close()

        self.order_ws = CustomOrderSocket(self.config['clientID'], self.config['accessToken'], on_order_update_callback)

        import threading
        ws_thread = threading.Thread(target=self.order_ws.connect_to_dhan_websocket_sync, daemon=True)
        ws_thread.start()
        logging.info("Dhan order websocket thread started.")
