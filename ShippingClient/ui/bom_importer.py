"""BOM Importer module.

Top-level module with two sub-tabs:
  - Packing List   (placeholder, ready for implementation)
  - Solid Works    (SolidWorks BOM → Mie Trak SANDBOX importer)

The Solid Works sub-tab is hardwired to the ``GunderlinSandbox`` database
so we never target production.
"""

from __future__ import annotations

import os
import textwrap
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from PyQt6.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.mie_trak_bom_client import (
    SANDBOX_DATABASE,
    BomImportItem,
    BomImportResult,
    ItemMatch,
    extract_bom_from_slddrw,
    get_sandbox_work_orders_by_sales_order,
    import_bom_to_work_order,
    match_items_in_sandbox,
    parse_bom_csv,
    search_sandbox_sales_orders,
)

from .style_tokens import (
    COLOR_BG_SUBTLE,
    COLOR_BORDER,
    COLOR_DANGER,
    COLOR_PRIMARY,
    COLOR_PRIMARY_SUBTLE_BG,
    COLOR_PRIMARY_SUBTLE_BORDER,
    COLOR_PRIMARY_SUBTLE_TEXT,
    COLOR_SUCCESS,
    COLOR_SURFACE,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_WARNING,
    RADIUS_LG,
    RADIUS_MD,
    SPACE_4,
    SPACE_8,
    SPACE_12,
    SPACE_16,
)
from .utils import apply_scaled_font, get_base_font_size


COLOR_SANDBOX_BG = "#FFFBEB"
COLOR_SANDBOX_BORDER = "#F59E0B"
COLOR_SANDBOX_TEXT = "#92400E"
COLOR_MATCH_OK_BG = "#ECFDF5"
COLOR_MATCH_OK_TEXT = "#166534"
COLOR_MATCH_BAD_BG = "#FEF2F2"
COLOR_MATCH_BAD_TEXT = "#B91C1C"


def _placeholder_page(icon: str, title: str, subtitle: str) -> QWidget:
    """Return a centered placeholder page for a tab that is not yet implemented."""
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(SPACE_16, SPACE_16, SPACE_16, SPACE_16)
    layout.addStretch(1)

    card = QFrame()
    card.setStyleSheet(
        f"""
        QFrame {{
            background: {COLOR_SURFACE};
            border: 1px solid {COLOR_BORDER};
            border-radius: {RADIUS_MD}px;
            padding: 0px;
        }}
        """
    )
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(SPACE_16 * 2, SPACE_16 * 2, SPACE_16 * 2, SPACE_16 * 2)
    card_layout.setSpacing(SPACE_12)
    card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    icon_label = QLabel(icon)
    apply_scaled_font(icon_label, offset=24)
    icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    card_layout.addWidget(icon_label)

    title_label = QLabel(title)
    apply_scaled_font(title_label, offset=6, weight=QFont.Weight.DemiBold)
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
    card_layout.addWidget(title_label)

    subtitle_label = QLabel(subtitle)
    apply_scaled_font(subtitle_label, offset=0)
    subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    subtitle_label.setWordWrap(True)
    subtitle_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
    card_layout.addWidget(subtitle_label)

    center_row = QHBoxLayout()
    center_row.addStretch(1)
    center_row.addWidget(card)
    center_row.addStretch(1)
    layout.addLayout(center_row)
    layout.addStretch(1)
    return page


class PackingListTab(QWidget):
    """Packing List sub-tab — ready for implementation."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(
            _placeholder_page(
                icon="📦",
                title="Packing List",
                subtitle=(
                    "Import and manage packing list BOMs here.\n"
                    "This tab is ready for its implementation."
                ),
            )
        )


# ════════════════════════════════════════════════════════════════════════════
# Background workers — keep the GUI responsive during SW extraction + DB ops
# ════════════════════════════════════════════════════════════════════════════


class _SwExtractWorker(QObject):
    finished = pyqtSignal(list, str)      # (rows, source_path)
    failed = pyqtSignal(str)

    def __init__(self, path: str):
        super().__init__()
        self._path = path

    def run(self):
        try:
            path = self._path
            ext = os.path.splitext(path)[1].lower()
            if ext == ".csv":
                _, rows = parse_bom_csv(path)
            elif ext == ".slddrw":
                _, rows, _ = extract_bom_from_slddrw(path, visible=True)
            else:
                raise RuntimeError(
                    f"Unsupported extension: {ext}. Use .slddrw or .csv (exported BOM)."
                )
            self.finished.emit(rows, path)
        except Exception as exc:  # noqa: BLE001 - surface error to UI
            self.failed.emit(str(exc))


class _MatchWorker(QObject):
    finished = pyqtSignal(dict)   # {part_number: ItemMatch}
    failed = pyqtSignal(str)

    def __init__(self, part_numbers: List[str]):
        super().__init__()
        self._part_numbers = list(part_numbers)

    def run(self):
        try:
            matches = match_items_in_sandbox(self._part_numbers)
            self.finished.emit(matches)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class _SalesOrderSearchWorker(QObject):
    finished = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, term: str):
        super().__init__()
        self._term = term

    def run(self):
        try:
            rows = search_sandbox_sales_orders(self._term)
            self.finished.emit(rows)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class _WorkOrderLoadWorker(QObject):
    finished = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, sales_order_pk: str):
        super().__init__()
        self._sales_order_pk = sales_order_pk

    def run(self):
        try:
            rows = get_sandbox_work_orders_by_sales_order(self._sales_order_pk)
            self.finished.emit(rows)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class _ImportWorker(QObject):
    finished = pyqtSignal(object)    # BomImportResult
    failed = pyqtSignal(str)

    def __init__(self, work_order_pk: int, items: List[BomImportItem], *, dry_run: bool):
        super().__init__()
        self._work_order_pk = work_order_pk
        self._items = items
        self._dry_run = dry_run

    def run(self):
        try:
            result = import_bom_to_work_order(
                self._work_order_pk, self._items, dry_run=self._dry_run
            )
            self.finished.emit(result)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


# ════════════════════════════════════════════════════════════════════════════
# Solid Works → Mie Trak Sandbox importer tab
# ════════════════════════════════════════════════════════════════════════════


class SolidWorksTab(QWidget):
    """SolidWorks BOM → Mie Trak SANDBOX importer.

    Flow:
      1. Load a .SLDDRW (runs SolidWorks via COM) or a pre-exported .CSV.
      2. SW rows show in the left grid.
      3. ``Match against Mie Trak`` looks up every part number in
         ``GunderlinSandbox.Item``. Matched rows go green; unmatched red.
      4. Operator searches a Sales Order, picks a Work Order from it.
      5. ``Import to sandbox WO`` becomes enabled only when every row is
         green AND a Work Order is selected. It runs the safe procedure
         documented in /BOM/Conversacion ... .pdf (transaction-wrapped
         INSERT/UPDATE + ``usp_AssignWorkOrderAssembly`` +
         ``usp_CalculateWorkOrder``).

    Sandbox guarantee: ``core.mie_trak_bom_client`` is hardcoded to
    ``GunderlinSandbox`` and refuses to connect to any other DB.
    """

    BOM_COLUMNS = ["Item", "Part Number", "Qty", "Description", "Match", "Item PK", "Mie Trak Description"]

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._bom_rows: List[dict] = []
        self._matches: Dict[str, ItemMatch] = {}
        self._sales_orders: List[dict] = []
        self._selected_sales_order_pk: Optional[str] = None
        self._work_orders: List[dict] = []
        self._selected_work_order_pk: Optional[int] = None
        self._threads: List[QThread] = []
        self._build_ui()

    # ────────────────────────────────────────────────────────────────────────
    # UI
    # ────────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACE_12, SPACE_12, SPACE_12, SPACE_12)
        outer.setSpacing(SPACE_12)

        outer.addWidget(self._build_toolbar())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(6)
        splitter.addWidget(self._build_bom_panel())
        splitter.addWidget(self._build_target_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([900, 520])
        outer.addWidget(splitter, 1)

        outer.addWidget(self._build_log_panel())

    def _build_toolbar(self) -> QWidget:
        toolbar = QFrame()
        row = QHBoxLayout(toolbar)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(SPACE_8)

        self._select_btn = QPushButton("Load file (.SLDDRW / .CSV)")
        self._select_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._select_btn.setStyleSheet(self._primary_button_style())
        self._select_btn.clicked.connect(self._on_select_file)
        row.addWidget(self._select_btn)

        self._match_btn = QPushButton("Match against Mie Trak Sandbox")
        self._match_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._match_btn.setStyleSheet(self._secondary_button_style())
        self._match_btn.clicked.connect(self._on_match)
        self._match_btn.setEnabled(False)
        row.addWidget(self._match_btn)

        row.addStretch(1)

        self._file_label = QLabel("No file loaded")
        apply_scaled_font(self._file_label, offset=-1)
        self._file_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        row.addWidget(self._file_label)
        return toolbar

    def _build_bom_panel(self) -> QWidget:
        wrapper = QFrame()
        wrapper.setStyleSheet(
            f"QFrame {{ background: {COLOR_SURFACE}; border: 1px solid {COLOR_BORDER}; "
            f"border-radius: {RADIUS_MD}px; }}"
        )
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(SPACE_12, SPACE_12, SPACE_12, SPACE_12)
        layout.setSpacing(SPACE_8)

        header = QHBoxLayout()
        title = QLabel("SolidWorks BOM ↔ Mie Trak Match")
        apply_scaled_font(title, offset=2, weight=QFont.Weight.DemiBold)
        header.addWidget(title)
        self._bom_summary_label = QLabel("0 lines")
        apply_scaled_font(self._bom_summary_label, offset=-1)
        self._bom_summary_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        header.addStretch(1)
        header.addWidget(self._bom_summary_label)
        layout.addLayout(header)

        self._bom_table = QTableWidget()
        self._bom_table.setColumnCount(len(self.BOM_COLUMNS))
        self._bom_table.setHorizontalHeaderLabels(self.BOM_COLUMNS)
        self._bom_table.verticalHeader().setVisible(False)
        self._bom_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._bom_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._bom_table.setAlternatingRowColors(True)
        self._bom_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._bom_table.horizontalHeader().setStretchLastSection(True)
        self._bom_table.setStyleSheet(self._table_style())
        layout.addWidget(self._bom_table, 1)
        return wrapper

    def _build_target_panel(self) -> QWidget:
        wrapper = QFrame()
        wrapper.setStyleSheet(
            f"QFrame {{ background: {COLOR_SURFACE}; border: 1px solid {COLOR_BORDER}; "
            f"border-radius: {RADIUS_MD}px; }}"
        )
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(SPACE_12, SPACE_12, SPACE_12, SPACE_12)
        layout.setSpacing(SPACE_8)

        title = QLabel("Target Sales Order / Work Order")
        apply_scaled_font(title, offset=2, weight=QFont.Weight.DemiBold)
        layout.addWidget(title)

        search_row = QHBoxLayout()
        search_label = QLabel("Job Number:")
        apply_scaled_font(search_label, offset=-1)
        search_row.addWidget(search_label)
        self._so_search = QLineEdit()
        self._so_search.setPlaceholderText("Search sales order (ID or number)…")
        self._so_search.returnPressed.connect(self._on_search_sales_orders)
        search_row.addWidget(self._so_search, 1)
        self._so_search_btn = QPushButton("Search")
        self._so_search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._so_search_btn.setStyleSheet(self._secondary_button_style())
        self._so_search_btn.clicked.connect(self._on_search_sales_orders)
        search_row.addWidget(self._so_search_btn)
        layout.addLayout(search_row)

        self._so_combo = QComboBox()
        self._so_combo.setPlaceholderText("Select a Sales Order")
        self._so_combo.currentIndexChanged.connect(self._on_so_changed)
        layout.addWidget(self._so_combo)

        wo_label = QLabel("Work Order:")
        apply_scaled_font(wo_label, offset=-1)
        layout.addWidget(wo_label)

        self._wo_combo = QComboBox()
        self._wo_combo.setPlaceholderText("Select a Work Order from the SO")
        self._wo_combo.currentIndexChanged.connect(self._on_wo_changed)
        layout.addWidget(self._wo_combo)

        self._wo_detail_label = QLabel("No Work Order selected.")
        apply_scaled_font(self._wo_detail_label, offset=-1)
        self._wo_detail_label.setWordWrap(True)
        self._wo_detail_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        layout.addWidget(self._wo_detail_label)

        layout.addStretch(1)

        self._readiness_label = QLabel("Status: load a file to begin.")
        apply_scaled_font(self._readiness_label, offset=-1, weight=QFont.Weight.DemiBold)
        self._readiness_label.setWordWrap(True)
        layout.addWidget(self._readiness_label)

        btn_row = QHBoxLayout()
        self._dry_run_btn = QPushButton("Dry-run (no commit)")
        self._dry_run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._dry_run_btn.setStyleSheet(self._secondary_button_style())
        self._dry_run_btn.clicked.connect(lambda: self._on_import(dry_run=True))
        self._dry_run_btn.setEnabled(False)
        btn_row.addWidget(self._dry_run_btn)

        self._import_btn = QPushButton("Import to Sandbox WO")
        self._import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._import_btn.setStyleSheet(self._danger_button_style())
        self._import_btn.clicked.connect(lambda: self._on_import(dry_run=False))
        self._import_btn.setEnabled(False)
        btn_row.addWidget(self._import_btn)
        layout.addLayout(btn_row)

        return wrapper

    def _build_log_panel(self) -> QWidget:
        wrapper = QFrame()
        wrapper.setStyleSheet(
            f"QFrame {{ background: {COLOR_SURFACE}; border: 1px solid {COLOR_BORDER}; "
            f"border-radius: {RADIUS_MD}px; }}"
        )
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(SPACE_12, SPACE_8, SPACE_12, SPACE_8)
        layout.setSpacing(SPACE_4)

        title_row = QHBoxLayout()
        title = QLabel("Operations log")
        apply_scaled_font(title, offset=0, weight=QFont.Weight.DemiBold)
        title_row.addWidget(title)
        title_row.addStretch(1)
        layout.addLayout(title_row)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(2000)
        self._log.setFixedHeight(140)
        self._log.setStyleSheet(
            f"QPlainTextEdit {{ background: {COLOR_BG_SUBTLE}; border: 1px solid {COLOR_BORDER}; "
            f"font-family: Consolas, 'Courier New', monospace; font-size: 12px; }}"
        )
        layout.addWidget(self._log)
        return wrapper

    # ────────────────────────────────────────────────────────────────────────
    # Stylesheet helpers
    # ────────────────────────────────────────────────────────────────────────
    def _primary_button_style(self) -> str:
        return f"""
            QPushButton {{
                background: {COLOR_PRIMARY};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: #1D4ED8; }}
            QPushButton:disabled {{ background: #94A3B8; }}
        """

    def _secondary_button_style(self) -> str:
        return f"""
            QPushButton {{
                background: white;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: 6px;
                padding: 7px 14px;
                font-weight: 500;
            }}
            QPushButton:hover {{ background: {COLOR_BG_SUBTLE}; }}
            QPushButton:disabled {{ color: #94A3B8; }}
        """

    def _danger_button_style(self) -> str:
        return f"""
            QPushButton {{
                background: {COLOR_SUCCESS};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 700;
            }}
            QPushButton:hover {{ background: #166534; }}
            QPushButton:disabled {{ background: #94A3B8; }}
        """

    def _table_style(self) -> str:
        return f"""
            QTableWidget {{ background: {COLOR_SURFACE}; gridline-color: {COLOR_BORDER}; }}
            QHeaderView::section {{
                background: {COLOR_BG_SUBTLE};
                padding: 6px 8px;
                border: none;
                border-right: 1px solid {COLOR_BORDER};
                border-bottom: 1px solid {COLOR_BORDER};
                font-weight: 600;
            }}
        """

    # ────────────────────────────────────────────────────────────────────────
    # Action: load file (SLDDRW or CSV)
    # ────────────────────────────────────────────────────────────────────────
    def _on_select_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select SolidWorks or CSV BOM file",
            "",
            "SolidWorks Drawing (*.slddrw);;CSV BOM (*.csv);;All files (*.*)",
        )
        if not path:
            return
        self._file_label.setText(f"Loading: {os.path.basename(path)}…")
        self._select_btn.setEnabled(False)
        self._log_line(f"Loading file: {path}")
        worker = _SwExtractWorker(path)
        self._start_worker(
            worker,
            on_finished=self._on_bom_loaded,
            on_failed=self._on_bom_load_failed,
        )

    def _on_bom_loaded(self, rows: list, path: str):
        self._select_btn.setEnabled(True)
        self._bom_rows = list(rows or [])
        self._matches = {}
        self._file_label.setText(f"Loaded: {os.path.basename(path)} · {len(self._bom_rows)} lines")
        self._log_line(f"BOM extracted ({len(self._bom_rows)} lines) from {path}")
        self._populate_bom_table()
        self._match_btn.setEnabled(len(self._bom_rows) > 0)
        self._refresh_readiness()

    def _on_bom_load_failed(self, message: str):
        self._select_btn.setEnabled(True)
        self._file_label.setText("Error loading file")
        self._log_line(f"ERROR loading file: {message}")
        QMessageBox.critical(self, "Extraction error", message)

    # ────────────────────────────────────────────────────────────────────────
    # Action: match against Mie Trak sandbox
    # ────────────────────────────────────────────────────────────────────────
    def _on_match(self):
        part_numbers = [str(r.get("part_number") or "").strip() for r in self._bom_rows]
        part_numbers = [p for p in part_numbers if p]
        if not part_numbers:
            return
        self._match_btn.setEnabled(False)
        self._log_line(
            f"Searching {len(set(part_numbers))} unique part numbers in {SANDBOX_DATABASE}.Item…"
        )
        worker = _MatchWorker(part_numbers)
        self._start_worker(worker, self._on_match_finished, self._on_match_failed)

    def _on_match_finished(self, matches: dict):
        self._match_btn.setEnabled(True)
        self._matches = dict(matches or {})
        found = sum(1 for m in self._matches.values() if m.found)
        total = len(self._matches)
        self._log_line(f"Match complete: {found}/{total} items found in {SANDBOX_DATABASE}.")
        self._populate_bom_table()
        self._refresh_readiness()

    def _on_match_failed(self, message: str):
        self._match_btn.setEnabled(True)
        self._log_line(f"ERROR during match: {message}")
        QMessageBox.critical(self, "Match error", message)

    # ────────────────────────────────────────────────────────────────────────
    # Action: sales order / work order pickers
    # ────────────────────────────────────────────────────────────────────────
    def _on_search_sales_orders(self):
        term = self._so_search.text().strip()
        if not term:
            return
        self._so_search_btn.setEnabled(False)
        self._log_line(f"Searching sales orders for '{term}' in {SANDBOX_DATABASE}…")
        worker = _SalesOrderSearchWorker(term)
        self._start_worker(worker, self._on_so_search_finished, self._on_so_search_failed)

    def _on_so_search_finished(self, rows: list):
        self._so_search_btn.setEnabled(True)
        self._sales_orders = list(rows or [])
        self._so_combo.blockSignals(True)
        try:
            self._so_combo.clear()
            for so in self._sales_orders:
                label = f"{so.get('sales_order_pk')} · {so.get('sales_order_number')}"
                self._so_combo.addItem(label, so.get("sales_order_pk"))
        finally:
            self._so_combo.blockSignals(False)
        self._log_line(f"Found {len(self._sales_orders)} sales orders.")
        if self._sales_orders:
            self._so_combo.setCurrentIndex(0)
            self._on_so_changed(0)
        else:
            self._selected_sales_order_pk = None
            self._work_orders = []
            self._wo_combo.clear()
            self._refresh_readiness()

    def _on_so_search_failed(self, message: str):
        self._so_search_btn.setEnabled(True)
        self._log_line(f"ERROR searching sales orders: {message}")
        QMessageBox.critical(self, "Error searching Sales Orders", message)

    def _on_so_changed(self, index: int):
        if index < 0 or index >= len(self._sales_orders):
            self._selected_sales_order_pk = None
            return
        so_pk = self._sales_orders[index].get("sales_order_pk")
        self._selected_sales_order_pk = so_pk
        self._log_line(f"Sales Order selected: {so_pk}. Loading work orders…")
        worker = _WorkOrderLoadWorker(so_pk)
        self._start_worker(worker, self._on_wo_load_finished, self._on_wo_load_failed)

    def _on_wo_load_finished(self, rows: list):
        self._work_orders = list(rows or [])
        self._wo_combo.blockSignals(True)
        try:
            self._wo_combo.clear()
            for wo in self._work_orders:
                label = f"WO {wo.get('work_order_number')} (PK {wo.get('work_order_pk')}) · {wo.get('part_number')}"
                self._wo_combo.addItem(label, wo.get("work_order_pk"))
        finally:
            self._wo_combo.blockSignals(False)
        self._log_line(f"Found {len(self._work_orders)} work orders for the SO.")
        if self._work_orders:
            self._wo_combo.setCurrentIndex(0)
            self._on_wo_changed(0)
        else:
            self._selected_work_order_pk = None
            self._wo_detail_label.setText("No work orders for that Sales Order.")
            self._refresh_readiness()

    def _on_wo_load_failed(self, message: str):
        self._log_line(f"ERROR loading work orders: {message}")
        QMessageBox.critical(self, "Error loading Work Orders", message)

    def _on_wo_changed(self, index: int):
        if index < 0 or index >= len(self._work_orders):
            self._selected_work_order_pk = None
            self._wo_detail_label.setText("No Work Order selected.")
            self._refresh_readiness()
            return
        wo = self._work_orders[index]
        try:
            self._selected_work_order_pk = int(wo.get("work_order_pk"))
        except (TypeError, ValueError):
            self._selected_work_order_pk = None
        self._wo_detail_label.setText(
            f"WO {wo.get('work_order_number')}  ·  PK {wo.get('work_order_pk')}\n"
            f"Part: {wo.get('part_number')}\n"
            f"{wo.get('description') or ''}\n"
            f"Due: {wo.get('due_date') or '-'}"
        )
        self._refresh_readiness()

    # ────────────────────────────────────────────────────────────────────────
    # Action: import to sandbox
    # ────────────────────────────────────────────────────────────────────────
    def _build_import_items(self) -> List[BomImportItem]:
        items: List[BomImportItem] = []
        for row in self._bom_rows:
            pn = str(row.get("part_number") or "").strip()
            if not pn:
                continue
            m = self._matches.get(pn)
            if not m or not m.found or not m.item_pk:
                return []  # incomplete match — refuse
            qty = row.get("qty")
            try:
                qty_f = float(qty) if qty is not None else 0.0
            except (TypeError, ValueError):
                qty_f = 0.0
            if qty_f <= 0:
                return []
            items.append(BomImportItem(
                part_number=pn,
                item_pk=int(m.item_pk),
                quantity=qty_f,
                description=str(row.get("description") or ""),
            ))
        return items

    def _on_import(self, *, dry_run: bool):
        if self._selected_work_order_pk is None:
            QMessageBox.warning(self, "Missing target", "Select a Work Order first.")
            return
        items = self._build_import_items()
        if not items:
            QMessageBox.warning(
                self,
                "Incomplete BOM",
                "All items must have a green Mie Trak match before importing.",
            )
            return

        mode_label = "DRY-RUN (no commit)" if dry_run else "REAL IMPORT (commit)"
        confirm = QMessageBox.question(
            self,
            f"Confirm {mode_label}",
            (
                f"About to {mode_label} {len(items)} BOM lines to Work Order PK "
                f"{self._selected_work_order_pk}, in database {SANDBOX_DATABASE}.\n\n"
                f"Confirm?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self._import_btn.setEnabled(False)
        self._dry_run_btn.setEnabled(False)
        self._log_line(
            f"Starting {mode_label} of {len(items)} items to WO PK {self._selected_work_order_pk}…"
        )
        worker = _ImportWorker(self._selected_work_order_pk, items, dry_run=dry_run)
        self._start_worker(worker, self._on_import_finished, self._on_import_failed)

    def _on_import_finished(self, result: BomImportResult):
        self._refresh_readiness()
        if result.error:
            self._log_line(f"ERROR: {result.error}")
            QMessageBox.critical(self, "Import error", result.error)
            return

        verb = "COMMIT" if result.committed else "ROLLBACK (dry-run)"
        self._log_line(
            f"{verb} OK · WO PK {result.work_order_pk} · Release PK {result.work_order_release_fk} "
            f"· Router {result.router_fk} · DB={result.database}"
        )
        for line in result.lines:
            self._log_line(
                f"  · {line.action} ItemFK={line.item_pk} ({line.part_number}) "
                f"qty={line.quantity_required} {line.detail}"
            )
        self._log_line("Sandbox housekeeping executed: usp_AssignWorkOrderAssembly + usp_CalculateWorkOrder.")

        QMessageBox.information(
            self,
            "Import finished",
            f"{verb}.\n\n{len(result.lines)} lines processed in {result.database}.",
        )

    def _on_import_failed(self, message: str):
        self._refresh_readiness()
        self._log_line(f"ERROR import thread: {message}")
        QMessageBox.critical(self, "Import error", message)

    # ────────────────────────────────────────────────────────────────────────
    # Populating BOM table
    # ────────────────────────────────────────────────────────────────────────
    def _populate_bom_table(self):
        self._bom_table.setRowCount(len(self._bom_rows))
        green = 0
        red = 0
        for r, row in enumerate(self._bom_rows):
            pn = str(row.get("part_number") or "").strip()
            match = self._matches.get(pn) if self._matches else None
            is_green = bool(match and match.found)

            cells = [
                str(row.get("item_no") or ""),
                pn,
                str(row.get("qty") if row.get("qty") is not None else ""),
                str(row.get("description") or ""),
                "✅ FOUND" if is_green else ("❌ NOT FOUND" if self._matches else "—"),
                str(match.item_pk) if (match and match.item_pk) else "",
                (match.description if match else "") or "",
            ]
            for c, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if c == 4:
                    if self._matches:
                        if is_green:
                            item.setBackground(QColor(COLOR_MATCH_OK_BG))
                            item.setForeground(QColor(COLOR_MATCH_OK_TEXT))
                            green += 1
                        else:
                            item.setBackground(QColor(COLOR_MATCH_BAD_BG))
                            item.setForeground(QColor(COLOR_MATCH_BAD_TEXT))
                            red += 1
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._bom_table.setItem(r, c, item)

        summary = f"{len(self._bom_rows)} lines"
        if self._matches:
            summary += f"  ·  ✅ {green}  ·  ❌ {red}"
        self._bom_summary_label.setText(summary)

    def _refresh_readiness(self):
        rows = len(self._bom_rows)
        if rows == 0:
            self._readiness_label.setText("Status: load a file to begin.")
            self._readiness_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
            self._dry_run_btn.setEnabled(False)
            self._import_btn.setEnabled(False)
            return

        if not self._matches:
            self._readiness_label.setText("Status: run 'Match against Mie Trak Sandbox'.")
            self._readiness_label.setStyleSheet(f"color: {COLOR_WARNING};")
            self._dry_run_btn.setEnabled(False)
            self._import_btn.setEnabled(False)
            return

        red = sum(1 for r in self._bom_rows if not (self._matches.get(str(r.get("part_number") or "").strip()) and self._matches[str(r.get("part_number") or "").strip()].found))
        if red > 0:
            self._readiness_label.setText(
                f"Status: {red} line(s) without a Mie Trak match — cannot import."
            )
            self._readiness_label.setStyleSheet(f"color: {COLOR_DANGER};")
            self._dry_run_btn.setEnabled(False)
            self._import_btn.setEnabled(False)
            return

        if self._selected_work_order_pk is None:
            self._readiness_label.setText(
                "Status: all items match ✅. Select a Work Order to continue."
            )
            self._readiness_label.setStyleSheet(f"color: {COLOR_WARNING};")
            self._dry_run_btn.setEnabled(False)
            self._import_btn.setEnabled(False)
            return

        self._readiness_label.setText(
            f"Status: ready to import {rows} lines → WO PK {self._selected_work_order_pk} in {SANDBOX_DATABASE}."
        )
        self._readiness_label.setStyleSheet(f"color: {COLOR_SUCCESS};")
        self._dry_run_btn.setEnabled(True)
        self._import_btn.setEnabled(True)

    # ────────────────────────────────────────────────────────────────────────
    # Log helpers + thread plumbing
    # ────────────────────────────────────────────────────────────────────────
    def _log_line(self, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self._log.appendPlainText(f"[{ts}] {message}")

    def _start_worker(
        self,
        worker: QObject,
        on_finished: Callable[..., None],
        on_failed: Callable[[str], None],
    ):
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(on_finished)
        worker.failed.connect(on_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda t=thread: self._threads.remove(t) if t in self._threads else None)
        self._threads.append(thread)
        thread.start()


class BomImporterWidget(QWidget):
    """Top-level BOM Importer page — contains Packing List and Solid Works sub-tabs."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE_16, SPACE_12, SPACE_16, SPACE_16)
        layout.setSpacing(SPACE_12)

        # ── Header ────────────────────────────────────────────────────────────
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(SPACE_8)

        title = QLabel("BOM Importer")
        apply_scaled_font(title, offset=4, weight=QFont.Weight.DemiBold)
        header_row.addWidget(title)
        header_row.addStretch(1)
        layout.addLayout(header_row)

        # ── Sub-tabs (pill style — matches Sills / Shipping sub-tabs) ─────────
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("bomImporterSubTabs")
        sub_tab_font_size = max(8, get_base_font_size() + 1)
        self.tab_widget.setStyleSheet(
            textwrap.dedent(
                f"""
                QTabWidget#bomImporterSubTabs::pane {{
                    border: none;
                    background: {COLOR_SURFACE};
                    margin-top: 10px;
                    border-radius: {RADIUS_LG}px;
                }}
                QTabWidget#bomImporterSubTabs QTabBar::tab {{
                    background: transparent;
                    color: {COLOR_TEXT_SECONDARY};
                    padding: 7px 16px;
                    border-radius: {RADIUS_MD}px;
                    margin-right: 4px;
                    font-size: {sub_tab_font_size}px;
                    min-width: 88px;
                }}
                QTabWidget#bomImporterSubTabs QTabBar::tab:hover:!selected {{
                    background: {COLOR_BG_SUBTLE};
                    color: {COLOR_TEXT_PRIMARY};
                }}
                QTabWidget#bomImporterSubTabs QTabBar::tab:selected {{
                    background: {COLOR_PRIMARY_SUBTLE_BG};
                    color: {COLOR_PRIMARY_SUBTLE_TEXT};
                    border: 1px solid {COLOR_PRIMARY_SUBTLE_BORDER};
                    font-weight: 700;
                }}
                """
            )
        )

        self.packing_list_tab = PackingListTab()
        self.solid_works_tab = SolidWorksTab()

        self.tab_widget.addTab(self.packing_list_tab, "Packing List")
        self.tab_widget.addTab(self.solid_works_tab, "Solid Works")

        layout.addWidget(self.tab_widget, 1)
