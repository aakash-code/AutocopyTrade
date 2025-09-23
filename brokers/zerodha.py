import time
import logging
import traceback
from urllib import parse
from kiteconnect import KiteConnect, KiteTicker
from selenium import webdriver
from selenium.webdriver.common.by import By
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
        Automates the Zerodha login process to get a request token.
        """
        logging.info(f"Getting request token for: {self.config['userid']}")
        options = webdriver.ChromeOptions()
        options.add_argument('--headless') # Run in headless mode
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        options.add_argument(f"--user-data-dir=/tmp/chrome_profile_{self.config['userid']}")

        try:
            # Assumes chromedriver is in the system's PATH
            driver = webdriver.Chrome(options=options)
            driver.delete_all_cookies()
            driver.implicitly_wait(4)

            login_url = self.config['loginURL'].replace('<apikey>', self.config['APIKey'])
            driver.get(login_url)

            # Enter credentials
            driver.find_element(by=By.ID, value='userid').send_keys(self.config['userid'])
            driver.find_element(by=By.ID, value='password').send_keys(decrypt_value(self.config['password']))
            driver.find_element(by=By.XPATH, value='//button[@type="submit"]').click()

            time.sleep(2) # Wait for 2FA page to load

            # Enter TOTP
            totp_secret = decrypt_value(self.config['TOPTSecret'])
            token = otp.get_totp(totp_secret)
            driver.find_element(by=By.XPATH, value='//input[@type="text"]').send_keys(token)
            driver.find_element(by=By.XPATH, value='//button[@type="submit"]').click()

            time.sleep(4) # Wait for redirect

            # Extract request token from the redirect URL
            url = driver.current_url
            request_token = parse.parse_qs(parse.urlparse(url).query)['request_token'][0]

            logging.info(f"Successfully logged in and got request token for: {self.config['userid']}")
            print(f"{self.config['userid']} successfully logged in.")
            return request_token

        except Exception as e:
            logging.error(f"Failed to get request token for {self.config['userid']}: {e}")
            traceback.print_exc()
            return None
        finally:
            if 'driver' in locals():
                driver.quit()

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
