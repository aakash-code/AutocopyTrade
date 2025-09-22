import json
from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
import pyotp
from logzero import logger

class AngeloneClient:
    def __init__(self, config_path='../../config/config.json'):
        with open(config_path, 'r') as f:
            config = json.load(f)

        self.api_key = config['angelone']['api_key']
        self.client_code = config['angelone']['client_code']
        self.password = config['angelone']['password']
        self.totp_secret = config['angelone']['totp_secret']

        self.smartApi = SmartConnect(self.api_key)
        self.session = self.generate_session()
        if self.session:
            self.jwt_token = self.session['jwtToken']
            self.refresh_token = self.session['refreshToken']
            self.feed_token = self.session['feedToken']

    def generate_session(self):
        try:
            totp = pyotp.TOTP(self.totp_secret).now()
        except Exception as e:
            logger.error("Invalid Token: The provided token is not valid.")
            raise e

        data = self.smartApi.generateSession(self.client_code, self.password, totp)

        if data['status'] == False:
            logger.error(data)
            return None
        else:
            return data['data']

    def place_order(self, order_params):
        return self.smartApi.placeOrder(order_params)

    def get_order_book(self):
        return self.smartApi.orderBook()

    def get_trade_book(self):
        return self.smartApi.tradeBook()

    def connect_to_websocket(self, correlation_id, mode, token_list, on_data):
        sws = SmartWebSocketV2(self.jwt_token, self.api_key, self.client_code, self.feed_token)

        def on_open(wsapp):
            logger.info("on open")
            sws.subscribe(correlation_id, mode, token_list)

        def on_error(wsapp, error):
            logger.error(error)

        def on_close(wsapp):
            logger.info("Close")

        sws.on_open = on_open
        sws.on_data = on_data
        sws.on_error = on_error
        sws.on_close = on_close

        sws.connect()
