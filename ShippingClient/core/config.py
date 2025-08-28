# core/config.py - Configuraciones centralizadas
import os
import sys
from .settings_manager import SettingsManager

DEFAULT_SERVER_URL = "http://localhost:8000"
DEFAULT_WS_URL = "ws://localhost:8000/ws"


def get_server_url() -> str:
    """Return server URL from settings or default."""
    return SettingsManager().get_server_url()


def get_ws_url() -> str:
    """Return WebSocket URL from settings or default."""
    return SettingsManager().get_ws_url()

# Configuraciones de UI
WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 900
DIALOG_WIDTH = 700
DIALOG_HEIGHT = 600
LOGIN_WIDTH = 480
LOGIN_HEIGHT = 380

# Timeouts
REQUEST_TIMEOUT = 10
CONNECTION_RETRY_INTERVAL = 5000  # 5 segundos

# Estilos
# Fuente principal para la interfaz. Se puede cambiar para ajustar el estilo
# de toda la aplicación.
MODERN_FONT = "Helvetica Neue"
FONT_SIZE = 10

# Recursos
# Directorio base considerando ejecución congelada con PyInstaller
BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def resource_path(relative_path: str) -> str:
    """Obtener ruta absoluta a un recurso empaquetado."""
    return os.path.join(BASE_DIR, relative_path)


# Ruta al logo en formato PNG para usos dentro de la UI (QPixmap)
LOGO_PATH = resource_path("assets/images/logo.png")

# Ruta al icono en formato ICO para iconos de ventana/aplicación
ICON_PATH = resource_path("icon.ico")
