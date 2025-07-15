from PyQt6.QtCore import QSettings


class SettingsManager:
    """Simple wrapper around QSettings for storing user preferences."""

    def __init__(self):
        # Organization and application names define where the settings are stored
        self._settings = QSettings("ShippingSchedule", "Client")

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
