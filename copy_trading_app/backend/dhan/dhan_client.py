import json
from dhanhq import DhanContext, dhanhq, MarketFeed, OrderUpdate
import time

class DhanClient:
    def __init__(self, config_path='../../config/config.json'):
        with open(config_path, 'r') as f:
            config = json.load(f)

        self.client_id = config['dhan']['client_id']
        self.access_token = config['dhan']['access_token']
        self.dhan_context = DhanContext(self.client_id, self.access_token)
        self.dhan = dhanhq(self.dhan_context)

    def place_order(self, security_id, exchange_segment, transaction_type, quantity, order_type, product_type, price=0):
        """
        Places an order on Dhan.
        """
        return self.dhan.place_order(
            security_id=security_id,
            exchange_segment=exchange_segment,
            transaction_type=transaction_type,
            quantity=quantity,
            order_type=order_type,
            product_type=product_type,
            price=price
        )

    def get_order_list(self):
        """
        Retrieves the order book.
        """
        return self.dhan.get_order_list()

    def get_order_by_id(self, order_id):
        """
        Retrieves a specific order by its ID.
        """
        return self.dhan.get_order_by_id(order_id)

    def get_trade_book(self):
        """
        Retrieves the trade book.
        """
        return self.dhan.get_trade_book()

    def connect_market_feed(self, instruments, on_message):
        """
        Connects to the market feed WebSocket.
        """
        market_feed = MarketFeed(self.dhan_context, instruments)
        market_feed.on_message = on_message
        market_feed.run_forever()

    def connect_order_update(self, on_update):
        """
        Connects to the order update WebSocket.
        """
        order_client = OrderUpdate(self.dhan_context)
        order_client.on_update = on_update

        while True:
            try:
                order_client.connect_to_dhan_websocket_sync()
            except Exception as e:
                print(f"Error connecting to Dhan WebSocket: {e}. Reconnecting in 5 seconds...")
                time.sleep(5)
