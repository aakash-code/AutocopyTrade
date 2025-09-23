from abc import ABC, abstractmethod

class Broker(ABC):
    """
    An abstract base class for all broker implementations.
    """

    def __init__(self, config):
        self.config = config
        self.client = None

    @abstractmethod
    def login(self):
        """
        Logs into the broker and initializes the client.
        """
        pass

    @abstractmethod
    def place_order(self, order_data):
        """
        Places an order.
        """
        pass

    @abstractmethod
    def modify_order(self, order_data):
        """
        Modifies an existing order.
        """
        pass

    @abstractmethod
    def cancel_order(self, order_data):
        """
        Cancels an existing order.
        """
        pass

    @abstractmethod
    def get_margins(self):
        """
        Retrieves account margins.
        """
        pass

    @abstractmethod
    def start_websocket(self, on_order_update_callback):
        """
        Starts the websocket connection for real-time order updates.
        """
        pass
