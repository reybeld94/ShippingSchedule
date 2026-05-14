# core/websocket_client.py - Cliente WebSocket separado
import websocket
from PyQt6.QtCore import QThread, pyqtSignal
from .config import get_ws_url
from .websocket_url import normalize_websocket_url

class WebSocketClient(QThread):
    message_received = pyqtSignal(str)
    connection_status = pyqtSignal(bool)
    
    def __init__(self, url: str | None = None):
        super().__init__()
        self.ws = None
        self.running = False
        self.url = normalize_websocket_url(url or get_ws_url())
    
    def run(self):
        def on_message(ws, message):
            self.message_received.emit(message)
        
        def on_error(ws, error):
            print(f"WebSocket error: {error}")
            self.connection_status.emit(False)
        
        def on_close(ws, close_status_code, close_msg):
            print("WebSocket connection closed")
            self.connection_status.emit(False)
        
        reconnect_delay = {"seconds": 1}

        def on_open(ws):
            reconnect_delay["seconds"] = 1
            print("WebSocket connection opened")
            self.connection_status.emit(True)
        
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        self.running = True
        # Reconnect with backoff whenever run_forever returns. A rejected
        # handshake returns immediately, so sleeping here prevents log spam.
        while self.running:
            try:
                self.ws.run_forever(ping_interval=30, ping_timeout=10)
            except Exception as e:
                print(f"WebSocket fatal exception: {e}")
                self.connection_status.emit(False)

            if self.running:
                delay = min(reconnect_delay["seconds"], 30)
                self.sleep(delay)
                reconnect_delay["seconds"] = delay + 2
    
    def stop(self):
        self.running = False
        if self.ws:
            self.ws.close()
        print("WebSocket client stopped")
