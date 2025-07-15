# core/websocket_client.py - Cliente WebSocket separado
import websocket
from PyQt6.QtCore import QThread, pyqtSignal
from .config import get_ws_url

class WebSocketClient(QThread):
    message_received = pyqtSignal(str)
    connection_status = pyqtSignal(bool)
    
    def __init__(self, url: str | None = None):
        super().__init__()
        self.ws = None
        self.running = False
        self.url = url or get_ws_url()
    
    def run(self):
        def on_message(ws, message):
            self.message_received.emit(message)
        
        def on_error(ws, error):
            print(f"WebSocket error: {error}")
            self.connection_status.emit(False)
        
        def on_close(ws, close_status_code, close_msg):
            print("WebSocket connection closed")
            self.connection_status.emit(False)
        
        def on_open(ws):
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
        while self.running:
            try:
                self.ws.run_forever()
            except Exception as e:
                print(f"WebSocket exception: {e}")
                self.connection_status.emit(False)
                if self.running:
                    self.sleep(5)  # Esperar 5 segundos antes de reconectar
    
    def stop(self):
        self.running = False
        if self.ws:
            self.ws.close()
        print("WebSocket client stopped")
