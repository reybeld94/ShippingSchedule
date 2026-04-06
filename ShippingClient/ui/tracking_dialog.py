from __future__ import annotations

from typing import Any
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from core.config import MODERN_FONT
from .utils import apply_scaled_font


class TrackingDetailsDialog(QDialog):
    def __init__(self, tracking_data: dict[str, Any], parent=None):
        super().__init__(parent)
        self.tracking_data = tracking_data or {}
        self.setWindowTitle("FedEx Tracking")
        self.setMinimumSize(760, 480)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel(f"FedEx Tracking · {self.tracking_data.get('trackingNumber') or 'N/A'}")
        apply_scaled_font(header, offset=3, weight=QFont.Weight.DemiBold)
        layout.addWidget(header)

        if not self.tracking_data.get("success"):
            message = self.tracking_data.get("message") or "Tracking data not found"
            error_label = QLabel(message)
            apply_scaled_font(error_label, offset=1)
            layout.addWidget(error_label)
            return

        summary = QLabel(
            "\n".join(
                [
                    f"Status: {self.tracking_data.get('status') or '—'}",
                    f"Description: {self.tracking_data.get('statusDescription') or '—'}",
                    f"Estimated delivery: {self.tracking_data.get('estimatedDelivery') or '—'}",
                    f"Delivered at: {self.tracking_data.get('deliveredAt') or '—'}",
                    f"Service: {self.tracking_data.get('serviceType') or '—'}",
                    f"Destination: {self._format_destination(self.tracking_data.get('destination'))}",
                ]
            )
        )
        summary.setFont(QFont(MODERN_FONT, max(8, summary.font().pointSize())))
        summary.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(summary)

        events = self.tracking_data.get("events") or []
        events_table = QTableWidget(len(events), 3)
        events_table.setHorizontalHeaderLabels(["Timestamp", "Location", "Description"])
        events_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        events_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        events_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        for row, event in enumerate(events):
            events_table.setItem(row, 0, QTableWidgetItem(str(event.get("timestamp") or "—")))
            location = ", ".join(
                [
                    part
                    for part in [
                        event.get("city"),
                        event.get("stateOrProvinceCode"),
                        event.get("countryCode"),
                    ]
                    if part
                ]
            )
            events_table.setItem(row, 1, QTableWidgetItem(location or "—"))
            events_table.setItem(row, 2, QTableWidgetItem(str(event.get("description") or event.get("eventType") or "—")))

        layout.addWidget(events_table)

    @staticmethod
    def _format_destination(destination: Any) -> str:
        if not isinstance(destination, dict):
            return "—"
        return ", ".join(
            [
                part
                for part in [
                    destination.get("city"),
                    destination.get("stateOrProvinceCode"),
                    destination.get("countryCode"),
                ]
                if part
            ]
        ) or "—"
