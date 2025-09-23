import time
import logging
import traceback
from urllib import parse
import requests
from kiteconnect import KiteConnect, KiteTicker
import onetimepass as otp

from brokers.base import Broker
from utils import decrypt_value


class ZerodhaBroker(Broker):
    """
    Implementation of the Broker interface for Zerodha.
    """

    def __init__(self, config):
        super().__init__(config)
        self.kite = None
        self.kws = None

    def _get_request_token(self):
        """
        Gets the request token by making HTTP requests instead of using selenium.
        """
        logging.info(f"Getting request token for: {self.config['userid']}")
        try:
            session = requests.Session()

            # 1. Initial login request to get cookies and request_id
            login_payload = {
                "user_id": self.config['userid'],
                "password": decrypt_value(self.config['password']),
            }
            login_response = session.post("https://kite.zerodha.com/api/login", data=login_payload)
            login_response.raise_for_status()
            request_id = login_response.json()["data"]["request_id"]

            # 2. 2FA request with TOTP
            totp_secret = decrypt_value(self.config['TOPTSecret'])
            token = otp.get_totp(totp_secret)
            twofa_payload = {
                "user_id": self.config['userid'],
                "request_id": request_id,
                "twofa_value": token,
                "twofa_type": "totp",
                "skip_session": True,
            }
            twofa_response = session.post("https://kite.zerodha.com/api/twofa", data=twofa_payload)
            twofa_response.raise_for_status()

            # 3. Final GET request to the login URL to get the request_token
            # The request_token is now in the cookies of the session
            final_url = self.config['loginURL'].replace('<apikey>', self.config['APIKey'])
            final_response = session.get(final_url, allow_redirects=True)
            final_response.raise_for_status()

            # The request_token is in the query parameters of the final redirected URL
            request_token = parse.parse_qs(parse.urlparse(final_response.url).query)['request_token'][0]

            logging.info(f"Successfully got request token for: {self.config['userid']}")
            print(f"{self.config['userid']} successfully logged in.")
            return request_token

        except Exception as e:
            logging.error(f"Failed to get request token for {self.config['userid']}: {e}")
            traceback.print_exc()
            return None

    def login(self):
        """
        Logs into Zerodha and initializes the KiteConnect client.
        """
        self.kite = KiteConnect(api_key=self.config['APIKey'])
        request_token = self._get_request_token()
        if not request_token:
            print(f"Could not get request token for {self.config['userid']}. Aborting login.")
            return False

        try:
            data = self.kite.generate_session(request_token=request_token, api_secret=self.config['APISecret'])
            self.kite.set_access_token(data["access_token"])
            print(f"KiteConnect session established for {self.config['userid']}")
            self.client = self.kite # Set the client object
            return True
        except Exception as e:
            logging.error(f"Connection Error for {self.config['userid']}: {e}")
            print(f"Connection error for user id: {self.config['userid']}. Exiting program!!!")
            return False

    def place_order(self, order_data):
        """
        Places an order using the KiteConnect client.
        """
        try:
            order_id = self.kite.place_order(**order_data)
            logging.info(f"Placed order for {self.config['userid']}. Order ID: {order_id}")
            return order_id
        except Exception as e:
            logging.error(f"Failed to place order for {self.config['userid']}: {e}")
            return None

    def modify_order(self, order_data):
        """
        Modifies an order using the KiteConnect client.
        """
        try:
            order_id = self.kite.modify_order(**order_data)
            logging.info(f"Modified order for {self.config['userid']}. Order ID: {order_id}")
            return order_id
        except Exception as e:
            logging.error(f"Failed to modify order for {self.config['userid']}: {e}")
            return None

    def cancel_order(self, order_data):
        """
        Cancels an order using the KiteConnect client.
        """
        try:
            order_id = self.kite.cancel_order(**order_data)
            logging.info(f"Cancelled order for {self.config['userid']}. Order ID: {order_id}")
            return order_id
        except Exception as e:
            logging.error(f"Failed to cancel order for {self.config['userid']}: {e}")
            return None

    def get_margins(self):
        """
        Retrieves account margins.
        """
        try:
            margins = self.kite.margins()
            return margins
        except Exception as e:
            logging.error(f"Failed to get margins for {self.config['userid']}: {e}")
            return None

    def start_websocket(self, on_order_update_callback):
        """
        Starts the websocket connection for real-time order updates.
        """
        if not self.kite or not self.kite.access_token:
            logging.error("Kite client not initialized or logged in. Cannot start websocket.")
            return

        self.kws = KiteTicker(self.config['APIKey'], self.kite.access_token)

        def on_ticks(ws, ticks):
            # We don't need to process ticks for this application
            pass

        def on_connect(ws, response):
            logging.info("WebSocket successfully connected.")
            # Subscribe to all orders
            ws.subscribe([]) # Empty list subscribes to all order updates
            ws.set_mode(ws.MODE_FULL, [])
            logging.info("Subscribed to all order updates in FULL mode.")

        def on_close(ws, code, reason):
            logging.warning(f"WebSocket connection closed: {code} - {reason}")

        def on_error(ws, code, reason):
            logging.error(f"WebSocket connection error: {code} - {reason}")

        def on_reconnect(ws, attempts_count):
            logging.info(f"Reconnecting websocket: {attempts_count}")

        def on_noreconnect(ws):
            logging.error("Failed to reconnect websocket after maximum retries.")

        # Assign callbacks
        self.kws.on_ticks = on_ticks
        self.kws.on_connect = on_connect
        self.kws.on_close = on_close
        self.kws.on_error = on_error
        self.kws.on_reconnect = on_reconnect
        self.kws.on_noreconnect = on_noreconnect
        self.kws.on_order_update = on_order_update_callback

        logging.info("Connecting to websocket...")
        self.kws.connect(threaded=True)
