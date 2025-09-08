import json
from PyQt6.QtCore import QSettings


class SettingsManager:
    """Simple wrapper around QSettings for storing user preferences."""

    def __init__(self):
        # Organization and application names define where the settings are stored
        self._settings = QSettings("ShippingSchedule", "Client")

    def get_server_url(self) -> str:
        """Return stored server URL or default."""
        return self._settings.value("server_url", "http://localhost:8000")

    def set_server_url(self, url: str):
        self._settings.setValue("server_url", url)

    def get_ws_url(self) -> str:
        """Return stored websocket URL or default."""
        return self._settings.value("ws_url", "ws://localhost:8000/ws")

    def set_ws_url(self, url: str):
        self._settings.setValue("ws_url", url)

    def save_cell_colors(self, table_name: str, colors: dict[tuple[int, int], str]):
        """DEPRECATED: persist colors by (row, column) for legacy support."""
        serialized = {f"{r},{c}": color for (r, c), color in colors.items()}
        self._settings.setValue(f"{table_name}_cell_colors", json.dumps(serialized))

    def load_cell_colors(self, table_name: str) -> dict[tuple[int, int], str]:
        """DEPRECATED: retrieve colors stored by (row, column)."""
        data = self._settings.value(f"{table_name}_cell_colors", "{}")
        try:
            raw = json.loads(data)
        except Exception:
            return {}
        result: dict[tuple[int, int], str] = {}
        for key, color in raw.items():
            try:
                r_str, c_str = key.split(",")
                result[(int(r_str), int(c_str))] = color
            except Exception:
                continue
        return result

    def save_shipment_colors(self, table_name: str, colors: dict[tuple[int, str], str]):
        """Persist background colors for shipment cells by (shipment_id, field_name)."""
        serialized = {f"{sid},{field}": color for (sid, field), color in colors.items()}
        self._settings.setValue(f"{table_name}_shipment_colors", json.dumps(serialized))

    def load_shipment_colors(self, table_name: str) -> dict[tuple[int, str], str]:
        """Retrieve stored background colors for shipment cells."""
        data = self._settings.value(f"{table_name}_shipment_colors", "{}")
        try:
            raw = json.loads(data)
        except Exception:
            return {}
        result: dict[tuple[int, str], str] = {}
        for key, color in raw.items():
            try:
                sid_str, field = key.split(",", 1)
                result[(int(sid_str), field)] = color
            except Exception:
                continue
        return result

    def save_column_widths(self, table_name: str, widths: list[int]):
        """Persist column widths for a table."""
        self._settings.beginGroup(table_name)
        for i, width in enumerate(widths):
            self._settings.setValue(f"col_{i}_width", width)
        self._settings.endGroup()

    def load_column_widths(self, table_name: str, column_count: int) -> list[int | None]:
        """Retrieve stored widths. Returns list with None for missing values."""
        widths: list[int | None] = []
        self._settings.beginGroup(table_name)
        for i in range(column_count):
            value = self._settings.value(f"col_{i}_width")
            try:
                widths.append(int(value)) if value is not None else widths.append(None)
            except (TypeError, ValueError):
                widths.append(None)
        self._settings.endGroup()
        return widths

    def get_last_username(self) -> str:
        """Return the last used username or empty string."""
        return self._settings.value("last_username", "")
    def should_remember_credentials(self) -> bool:
        """Return True if credentials should be remembered."""
        return self._settings.value("remember_credentials", False, bool)

    def save_credentials(self, username: str, remember: bool):
        """Persist last used username when requested, otherwise clear stored data."""
        if remember:
            self._settings.setValue("last_username", username)
            self._settings.setValue("remember_credentials", True)
        else:
            self._settings.remove("last_username")
            self._settings.remove("last_password")
            self._settings.setValue("remember_credentials", False)
