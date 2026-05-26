"""Interactive purchasing dashboard for sills.

Master-detail layout inside the existing "Sills Dashboard" sub-tab:

- Top: KPI cards (dies short, LATE lines, qty to order in 30d, qty on PO in transit).
- Filters: status, search, schedule horizon.
- Left: list of dies (one row per die number) with at-a-glance status badges.
- Right: detail panel for the selected die — inventory by length, demand
  timeline (which WOs need it and when), open POs with ETA, and proposed
  purchasing actions pulled from the shortage report.

Data comes from Mie Trak directly via `core.mie_trak_client`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from PyQt6.QtCore import QObject, Qt, QThread, QSignalBlocker, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.mie_trak_client import (
    DEFAULT_MIE_TRAK_DATABASE,
    DEFAULT_MIE_TRAK_SERVER,
    get_sills_inventory_by_part,
    get_sills_open_purchase_orders,
    get_sills_shortage_view,
)

from .style_tokens import (
    COLOR_BG_SUBTLE,
    COLOR_BORDER,
    COLOR_DANGER,
    COLOR_PRIMARY,
    COLOR_SURFACE,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    RADIUS_MD,
    SPACE_8,
    SPACE_12,
    SPACE_16,
)
from .utils import apply_scaled_font


COLOR_LATE_BG = "#FEF2F2"
COLOR_LATE_TEXT = "#B91C1C"
COLOR_WARN_BG = "#FFFBEB"
COLOR_WARN_TEXT = "#92400E"
COLOR_OK_BG = "#ECFDF5"
COLOR_OK_TEXT = "#166534"
COLOR_INFO_TEXT = "#1D4ED8"


class _SillsDataWorker(QObject):
    finished = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, server: str, database: str):
        super().__init__()
        self._server = server
        self._database = database

    def run(self):
        try:
            shortage = get_sills_shortage_view(server=self._server, database=self._database)
            pos = get_sills_open_purchase_orders(server=self._server, database=self._database)
            inventory = get_sills_inventory_by_part(server=self._server, database=self._database)
            self.finished.emit({
                "shortage": shortage,
                "pos": pos,
                "inventory": inventory,
            })
        except Exception as exc:  # noqa: BLE001 - surface DB error to user
            self.failed.emit(str(exc))


@dataclass
class DieAggregate:
    die: str
    material: str
    total_short: int = 0
    late_lines: int = 0
    short_lines: int = 0
    ok_lines: int = 0
    qty_on_hand: int = 0
    qty_on_po: int = 0
    next_wanted: Optional[date] = None
    pos: List[dict] = field(default_factory=list)
    shortage_rows: List[dict] = field(default_factory=list)
    inventory_rows: List[dict] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.die}-{self.material}" if self.material else self.die

    @property
    def worst_status(self) -> str:
        if self.late_lines > 0:
            return "LATE"
        if self.short_lines > 0:
            return "SHORT"
        return "OK"


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_date(value: Any) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(value[:len(fmt) + 6], fmt).date()
            except ValueError:
                continue
    return None


def _fmt_date(value: Any) -> str:
    d = _safe_date(value)
    return d.strftime("%m/%d/%Y") if d else ""


def _is_late_proposal(proposal: str) -> bool:
    return "LATE" in (proposal or "").upper()


def _die_key(row: dict) -> str:
    die = str(row.get("Die") or "").strip() or "?"
    mat = str(row.get("Material") or "").strip()
    return f"{die}-{mat}" if mat else die


def _aggregate(data: dict) -> Dict[str, DieAggregate]:
    aggregates: Dict[str, DieAggregate] = {}

    for row in data.get("inventory", []) or []:
        key = _die_key(row)
        if key not in aggregates:
            aggregates[key] = DieAggregate(
                die=str(row.get("Die") or "").strip() or "?",
                material=str(row.get("Material") or "").strip(),
            )
        agg = aggregates[key]
        agg.inventory_rows.append(row)
        agg.qty_on_hand += _safe_int(row.get("QuantityOnHand"))

    for row in data.get("pos", []) or []:
        key = _die_key(row)
        if key not in aggregates:
            aggregates[key] = DieAggregate(
                die=str(row.get("Die") or "").strip() or "?",
                material=str(row.get("Material") or "").strip(),
            )
        agg = aggregates[key]
        agg.pos.append(row)
        agg.qty_on_po += _safe_int(row.get("QtyIncoming"))

    for row in data.get("shortage", []) or []:
        key = _die_key(row)
        if key not in aggregates:
            aggregates[key] = DieAggregate(
                die=str(row.get("Die") or "").strip() or "?",
                material=str(row.get("Material") or "").strip(),
            )
        agg = aggregates[key]
        agg.shortage_rows.append(row)
        wanted = _safe_date(row.get("WantedDate"))
        if wanted and (agg.next_wanted is None or wanted < agg.next_wanted):
            agg.next_wanted = wanted

    for agg in aggregates.values():
        _simulate_supply_allocation(agg)

    return aggregates


def _simulate_supply_allocation(agg: DieAggregate) -> None:
    """Allocate cross-length stock + POs to demand and flag weld options.

    Longer pieces can be cut down to satisfy shorter demand (auto-applied).
    Shorter pieces are *not* auto-applied — they are surfaced as WELD
    suggestions because welding is a user-driven decision.

    Mutates each shortage row in-place adding:
      AllocCovered, AllocShort, AllocFromExact, AllocFromLonger,
      CoverageNotes, WeldCandidates (list of {length, qty, label}),
      AllocStatus ('OK' | 'SHORT' | 'LATE'), AllocProposal.

    Also recomputes agg.short_lines, agg.late_lines, agg.total_short
    from the post-allocation values.
    """
    today = date.today()

    supply: List[dict] = []
    for inv in agg.inventory_rows:
        qty = _safe_int(inv.get("QuantityOnHand"))
        length = _safe_int(inv.get("Length"))
        if qty <= 0 or length <= 0:
            continue
        supply.append({
            "length": length,
            "qty": qty,
            "available_date": today,
            "label": "Stock",
        })
    for po in agg.pos:
        qty = _safe_int(po.get("QtyIncoming"))
        length = _safe_int(po.get("Length"))
        if qty <= 0 or length <= 0:
            continue
        eta = _safe_date(po.get("ETA")) or today
        supply.append({
            "length": length,
            "qty": qty,
            "available_date": eta,
            "label": f"PO {po.get('PurchaseOrderNumber')}",
        })

    # Earliest wanted_date first; ties broken by length desc so the longest
    # demand grabs the longest stock before a shorter demand on the same day
    # can over-cut from it.
    demand_rows = sorted(
        agg.shortage_rows,
        key=lambda r: (
            _safe_date(r.get("WantedDate")) or date.max,
            -_safe_int(r.get("NeededLength")),
        ),
    )

    new_short_total = 0
    new_short_lines = 0
    new_late_lines = 0

    for row in demand_rows:
        need = _safe_int(row.get("QtyNeeded"))
        needed_length = _safe_int(row.get("NeededLength"))
        wanted = _safe_date(row.get("WantedDate"))
        remaining = need
        notes: List[str] = []
        from_longer = 0
        from_exact = 0

        # Use max(wanted, today) so that stock which physically exists right
        # now is always eligible — even for demand whose WantedDate is in the
        # past.  For POs the ETA must still be <= this cutoff, meaning only
        # POs that have already arrived (ETA <= today) are eligible for
        # past-dated demand.
        effective_cutoff = max(wanted, today) if wanted is not None else today
        eligible = [
            s for s in supply
            if s["qty"] > 0
            and s["length"] >= needed_length
            and s["available_date"] <= effective_cutoff
        ]
        # Smallest valid length first so longer pieces stay available for
        # later/longer demand that genuinely needs them.
        eligible.sort(key=lambda s: (s["length"], s["available_date"]))

        for s in eligible:
            if remaining <= 0:
                break
            take = min(remaining, s["qty"])
            s["qty"] -= take
            remaining -= take
            if s["length"] == needed_length:
                from_exact += take
            else:
                from_longer += take
            notes.append(f'{take} from {s["length"]}" {s["label"]}')

        weld_candidates: List[dict] = []
        if remaining > 0:
            for s in supply:
                if s["qty"] > 0 and 0 < s["length"] < needed_length:
                    weld_candidates.append({
                        "length": s["length"],
                        "qty": s["qty"],
                        "label": s["label"],
                    })
            # Prefer longer shorter-than-needed first (less welding required).
            weld_candidates.sort(key=lambda w: (-w["length"], w["label"]))

        row["AllocCovered"] = need - remaining
        row["AllocShort"] = remaining
        row["AllocFromExact"] = from_exact
        row["AllocFromLonger"] = from_longer
        row["CoverageNotes"] = "; ".join(notes)
        row["WeldCandidates"] = weld_candidates

        if remaining <= 0:
            row["AllocStatus"] = "OK"
            row["AllocProposal"] = (
                f"Covered: {from_exact} exact + {from_longer} cut from longer"
                if from_longer else ""
            )
        else:
            order_by = _safe_date(row.get("OrderByDate"))
            is_late = order_by is not None and order_by < today
            row["AllocStatus"] = "LATE" if is_late else "SHORT"
            weld_note = ""
            if weld_candidates:
                top = weld_candidates[0]
                gap = needed_length - top["length"]
                weld_note = (
                    f'  · WELD option: {top["qty"]}× {top["length"]}" avail '
                    f'(weld ~{gap}")'
                )
            if is_late:
                row["AllocProposal"] = f"LATE — Order {remaining} ASAP{weld_note}"
            elif order_by:
                row["AllocProposal"] = (
                    f"Order {remaining} by {order_by.strftime('%m/%d/%Y')}{weld_note}"
                )
            else:
                row["AllocProposal"] = f"Order {remaining}{weld_note}"
            new_short_total += remaining
            new_short_lines += 1
            if is_late:
                new_late_lines += 1

    agg.total_short = new_short_total
    agg.short_lines = new_short_lines
    agg.late_lines = new_late_lines
    agg.ok_lines = len(agg.shortage_rows) - new_short_lines


def _make_kpi_card(title: str, *, accent: str = COLOR_PRIMARY) -> tuple[QFrame, QLabel, QLabel]:
    card = QFrame()
    card.setStyleSheet(
        f"""
        QFrame {{
            background: {COLOR_SURFACE};
            border: 1px solid {COLOR_BORDER};
            border-radius: {RADIUS_MD}px;
        }}
        """
    )
    layout = QVBoxLayout(card)
    layout.setContentsMargins(SPACE_16, SPACE_12, SPACE_16, SPACE_16)
    layout.setSpacing(SPACE_8 // 2)

    title_label = QLabel(title)
    apply_scaled_font(title_label, offset=0, weight=QFont.Weight.Medium)
    title_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")

    value_label = QLabel("—")
    apply_scaled_font(value_label, offset=8, weight=QFont.Weight.Bold)
    value_label.setStyleSheet(f"color: {accent};")

    sub_label = QLabel("")
    apply_scaled_font(sub_label, offset=-1)
    sub_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")

    layout.addWidget(title_label)
    layout.addWidget(value_label)
    layout.addWidget(sub_label)
    return card, value_label, sub_label


def _status_item(text: str, status: str) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    if status == "LATE":
        item.setBackground(QColor(COLOR_LATE_BG))
        item.setForeground(QColor(COLOR_LATE_TEXT))
    elif status == "SHORT":
        item.setBackground(QColor(COLOR_WARN_BG))
        item.setForeground(QColor(COLOR_WARN_TEXT))
    elif status == "OK":
        item.setBackground(QColor(COLOR_OK_BG))
        item.setForeground(QColor(COLOR_OK_TEXT))
    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    font = item.font()
    font.setBold(True)
    item.setFont(font)
    return item


class SillsDashboardWidget(QWidget):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        server_provider: Callable[[], str] | None = None,
        database_provider: Callable[[], str] | None = None,
    ):
        super().__init__(parent)
        self._server_provider = server_provider or (lambda: DEFAULT_MIE_TRAK_SERVER)
        self._database_provider = database_provider or (lambda: DEFAULT_MIE_TRAK_DATABASE)
        self._aggregates: Dict[str, DieAggregate] = {}
        self._selected_die: Optional[str] = None
        self._thread: Optional[QThread] = None
        self._worker: Optional[_SillsDataWorker] = None
        self._last_loaded: Optional[datetime] = None
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(SPACE_12)

        outer.addLayout(self._build_header())
        outer.addLayout(self._build_kpi_row())
        outer.addLayout(self._build_filter_row())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(6)
        splitter.addWidget(self._build_die_list())
        splitter.addWidget(self._build_detail_panel())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([320, 900])
        outer.addWidget(splitter, 1)

    def _build_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(SPACE_12)

        title = QLabel("Sills Purchasing Dashboard")
        apply_scaled_font(title, offset=4, weight=QFont.Weight.DemiBold)
        row.addWidget(title)

        self._status_label = QLabel("")
        apply_scaled_font(self._status_label, offset=-1)
        self._status_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        row.addWidget(self._status_label)

        row.addStretch(1)

        self._refresh_btn = QPushButton("Refresh from Mie Trak")
        self._refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_btn.setStyleSheet(
            f"""
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
        )
        self._refresh_btn.clicked.connect(self.reload)
        row.addWidget(self._refresh_btn)
        return row

    def _build_kpi_row(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(SPACE_12)
        grid.setVerticalSpacing(SPACE_12)

        self._kpi_cards: Dict[str, tuple[QLabel, QLabel]] = {}
        kpis = [
            ("dies_short", "Dies with shortage", COLOR_DANGER),
            ("late_lines", "LATE lines (Order ASAP)", COLOR_LATE_TEXT),
            ("qty_30d", "Qty to order (next 30d)", COLOR_WARN_TEXT),
            ("qty_on_po", "Qty on PO in-transit", COLOR_INFO_TEXT),
        ]
        for index, (kpi_id, label, accent) in enumerate(kpis):
            card, value, sub = _make_kpi_card(label, accent=accent)
            grid.addWidget(card, 0, index)
            self._kpi_cards[kpi_id] = (value, sub)
        for c in range(len(kpis)):
            grid.setColumnStretch(c, 1)
        return grid

    def _build_filter_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(SPACE_8)

        search_label = QLabel("Search die / part / job:")
        apply_scaled_font(search_label, offset=-1)
        row.addWidget(search_label)
        self._search = QLineEdit()
        self._search.setPlaceholderText("e.g. 11535, 11535-BR-072, or 43090")
        self._search.setFixedWidth(260)
        self._search.textChanged.connect(self._apply_filters)
        row.addWidget(self._search)

        status_label = QLabel("Status:")
        apply_scaled_font(status_label, offset=-1)
        row.addWidget(status_label)
        self._status_filter = QComboBox()
        self._status_filter.addItems(["All", "Only LATE", "Short or LATE", "OK only"])
        self._status_filter.currentIndexChanged.connect(self._apply_filters)
        row.addWidget(self._status_filter)

        horizon_label = QLabel("Horizon:")
        apply_scaled_font(horizon_label, offset=-1)
        row.addWidget(horizon_label)
        self._horizon = QComboBox()
        self._horizon.addItems(["All", "Next 30 days", "Next 90 days", "Next 6 months"])
        self._horizon.currentIndexChanged.connect(self._refresh_views)
        row.addWidget(self._horizon)

        row.addStretch(1)
        return row

    def _build_die_list(self) -> QWidget:
        wrapper = QFrame()
        wrapper.setStyleSheet(
            f"QFrame {{ background: {COLOR_SURFACE}; border: 1px solid {COLOR_BORDER}; "
            f"border-radius: {RADIUS_MD}px; }}"
        )
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(SPACE_12, SPACE_12, SPACE_12, SPACE_12)
        layout.setSpacing(SPACE_8)

        header = QLabel("Dies")
        apply_scaled_font(header, offset=2, weight=QFont.Weight.DemiBold)
        layout.addWidget(header)

        self._die_table = QTableWidget()
        self._die_table.setColumnCount(6)
        self._die_table.setHorizontalHeaderLabels(["Die", "Material", "Status", "Short", "On Hand", "On PO"])
        self._die_table.verticalHeader().setVisible(False)
        self._die_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._die_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._die_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._die_table.setAlternatingRowColors(True)
        self._die_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._die_table.horizontalHeader().setStretchLastSection(True)
        self._die_table.setStyleSheet(
            f"""
            QTableWidget {{ background: {COLOR_SURFACE}; border: none; gridline-color: {COLOR_BORDER}; }}
            QTableWidget::item:selected {{ background: #DBEAFE; color: {COLOR_TEXT_PRIMARY}; }}
            """
        )
        self._die_table.itemSelectionChanged.connect(self._on_die_selected)
        layout.addWidget(self._die_table, 1)
        return wrapper

    def _build_detail_panel(self) -> QWidget:
        wrapper = QFrame()
        wrapper.setStyleSheet(
            f"QFrame {{ background: {COLOR_SURFACE}; border: 1px solid {COLOR_BORDER}; "
            f"border-radius: {RADIUS_MD}px; }}"
        )
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(SPACE_16, SPACE_12, SPACE_16, SPACE_12)
        layout.setSpacing(SPACE_8)

        self._detail_title = QLabel("Select a die from the left")
        apply_scaled_font(self._detail_title, offset=3, weight=QFont.Weight.DemiBold)
        layout.addWidget(self._detail_title)

        self._detail_subtitle = QLabel("")
        apply_scaled_font(self._detail_subtitle, offset=-1)
        self._detail_subtitle.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        layout.addWidget(self._detail_subtitle)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack, 1)

        empty = QLabel("\n\nNo die selected.\n\nRefresh and pick a row on the left to drill in.")
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        self._stack.addWidget(empty)

        detail_page = QWidget()
        detail_layout = QVBoxLayout(detail_page)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(SPACE_8)
        self._detail_tabs = QTabWidget()
        self._detail_tabs.setStyleSheet(
            f"""
            QTabBar::tab {{
                padding: 8px 14px;
                background: {COLOR_BG_SUBTLE};
                border: 1px solid {COLOR_BORDER};
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{ background: {COLOR_SURFACE}; color: {COLOR_PRIMARY}; }}
            QTabWidget::pane {{ border: 1px solid {COLOR_BORDER}; border-radius: 6px; }}
            """
        )
        self._inventory_table = self._make_table([
            "Part Number", "Length", "Material", "On Hand", "Lead Time (d)"
        ])
        self._demand_table = self._make_table([
            "Wanted Date", "Work Order", "Part Number", "Length",
            "Qty Needed", "Covered", "Short", "Status", "Coverage / Action",
        ])
        self._demand_table.setWordWrap(True)
        self._po_table = self._make_table([
            "PO #", "Created", "ETA", "Vendor", "Part Number", "Length",
            "Qty Ordered", "Received", "Incoming",
        ])
        self._actions_table = self._make_table([
            "Order By", "Part Number", "Length", "Qty to Order", "Wanted Date",
            "Work Order", "Status", "WELD Option",
        ])

        self._detail_tabs.addTab(self._actions_table, "Suggested Actions")
        self._detail_tabs.addTab(self._demand_table, "Demand")
        self._detail_tabs.addTab(self._po_table, "Open POs")
        self._detail_tabs.addTab(self._inventory_table, "Inventory by Length")
        detail_layout.addWidget(self._detail_tabs)
        self._stack.addWidget(detail_page)
        self._stack.setCurrentIndex(0)

        return wrapper

    def _make_table(self, columns: List[str]) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        table.setStyleSheet(
            f"""
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
        )
        return table

    def reload(self):
        if self._thread is not None:
            return
        self._refresh_btn.setEnabled(False)
        self._status_label.setText("Loading from Mie Trak…")
        try:
            server = self._server_provider() or DEFAULT_MIE_TRAK_SERVER
            database = self._database_provider() or DEFAULT_MIE_TRAK_DATABASE
        except Exception:
            server = DEFAULT_MIE_TRAK_SERVER
            database = DEFAULT_MIE_TRAK_DATABASE

        thread = QThread(self)
        worker = _SillsDataWorker(server=server, database=database)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_data_loaded)
        worker.failed.connect(self._on_data_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._clear_thread)
        self._thread = thread
        self._worker = worker
        thread.start()

    def _clear_thread(self):
        self._thread = None
        self._worker = None
        self._refresh_btn.setEnabled(True)

    def _on_data_failed(self, message: str):
        self._status_label.setText(f"Failed to load: {message}")
        self._status_label.setStyleSheet(f"color: {COLOR_DANGER};")

    def _on_data_loaded(self, payload: dict):
        self._aggregates = _aggregate(payload)
        self._last_loaded = datetime.now()
        self._status_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")
        self._status_label.setText(
            f"Loaded {len(self._aggregates)} die+material profiles · {self._last_loaded.strftime('%m/%d %H:%M')}"
        )
        self._refresh_views()

    def _refresh_views(self):
        self._populate_kpis()
        self._populate_die_table()

    def _horizon_cutoff(self) -> Optional[date]:
        idx = self._horizon.currentIndex()
        if idx == 1:
            return date.today() + timedelta(days=30)
        if idx == 2:
            return date.today() + timedelta(days=90)
        if idx == 3:
            return date.today() + timedelta(days=183)
        return None

    def _populate_kpis(self):
        dies_short = sum(1 for a in self._aggregates.values() if a.short_lines > 0)
        late_lines = sum(a.late_lines for a in self._aggregates.values())
        qty_on_po = sum(a.qty_on_po for a in self._aggregates.values())

        qty_30d = 0
        order_horizon = date.today() + timedelta(days=30)
        for agg in self._aggregates.values():
            for row in agg.shortage_rows:
                if _safe_int(row.get("AllocShort")) <= 0:
                    continue
                order_by = _safe_date(row.get("OrderByDate"))
                if order_by and order_by <= order_horizon:
                    qty_30d += _safe_int(row.get("AllocShort"))

        self._kpi_cards["dies_short"][0].setText(str(dies_short))
        self._kpi_cards["dies_short"][1].setText(f"of {len(self._aggregates)} die+material profiles")
        self._kpi_cards["late_lines"][0].setText(str(late_lines))
        self._kpi_cards["late_lines"][1].setText("order ASAP — past lead time")
        self._kpi_cards["qty_30d"][0].setText(str(qty_30d))
        self._kpi_cards["qty_30d"][1].setText("units needing PO within 30d")
        self._kpi_cards["qty_on_po"][0].setText(str(qty_on_po))
        self._kpi_cards["qty_on_po"][1].setText(
            f"across {sum(len(a.pos) for a in self._aggregates.values())} open lines"
        )

    def _apply_filters(self):
        self._populate_die_table()

    def _passes_filter(self, agg: DieAggregate) -> bool:
        text = self._search.text().strip().lower()
        if text:
            haystacks = [agg.die.lower(), agg.material.lower(), agg.key.lower()]
            haystacks.extend(str(r.get("PartNumber") or "").lower() for r in agg.shortage_rows)
            haystacks.extend(str(r.get("PartNumber") or "").lower() for r in agg.inventory_rows)
            haystacks.extend(str(r.get("WorkOrder") or "").lower() for r in agg.shortage_rows)
            if not any(text in h for h in haystacks):
                return False
        status_idx = self._status_filter.currentIndex()
        if status_idx == 1 and agg.late_lines == 0:
            return False
        if status_idx == 2 and agg.short_lines == 0:
            return False
        if status_idx == 3 and agg.short_lines > 0:
            return False
        return True

    def _populate_die_table(self):
        rows = [agg for agg in self._aggregates.values() if self._passes_filter(agg)]
        rows.sort(key=lambda a: (-a.late_lines, -a.short_lines, a.die, a.material))

        # Block selection signals while rebuilding rows; otherwise setRowCount
        # and the auto-select emit transient "no items selected" events that
        # would clear _selected_die and the detail panel before we can choose
        # the right row.
        blocker = QSignalBlocker(self._die_table)
        try:
            self._die_table.setRowCount(len(rows))
            for r, agg in enumerate(rows):
                die_item = QTableWidgetItem(agg.die)
                font = die_item.font()
                font.setBold(True)
                die_item.setFont(font)
                die_item.setData(Qt.ItemDataRole.UserRole, agg.key)
                self._die_table.setItem(r, 0, die_item)
                self._die_table.setItem(r, 1, QTableWidgetItem(agg.material))
                self._die_table.setItem(r, 2, _status_item(agg.worst_status, agg.worst_status))
                self._die_table.setItem(r, 3, QTableWidgetItem(str(agg.total_short)))
                self._die_table.setItem(r, 4, QTableWidgetItem(str(agg.qty_on_hand)))
                self._die_table.setItem(r, 5, QTableWidgetItem(str(agg.qty_on_po)))

            target_row = -1
            if self._selected_die:
                for r in range(self._die_table.rowCount()):
                    if self._die_table.item(r, 0).data(Qt.ItemDataRole.UserRole) == self._selected_die:
                        target_row = r
                        break
            if target_row < 0 and rows:
                target_row = 0
            if target_row >= 0:
                self._die_table.selectRow(target_row)
        finally:
            del blocker

        # Drive the detail panel directly instead of depending on the signal
        # we just blocked.
        if rows and target_row >= 0:
            key = self._die_table.item(target_row, 0).data(Qt.ItemDataRole.UserRole)
            self._selected_die = key
            self._populate_detail(self._aggregates.get(key))
        else:
            self._selected_die = None
            self._stack.setCurrentIndex(0)

    def _on_die_selected(self):
        row = self._die_table.currentRow()
        if row < 0 or row >= self._die_table.rowCount():
            if self._die_table.rowCount() == 0:
                self._selected_die = None
                self._stack.setCurrentIndex(0)
            return
        item = self._die_table.item(row, 0)
        if item is None:
            return
        key = item.data(Qt.ItemDataRole.UserRole)
        if not key:
            return
        self._selected_die = key
        self._populate_detail(self._aggregates.get(key))

    def _populate_detail(self, agg: Optional[DieAggregate]):
        if agg is None:
            self._stack.setCurrentIndex(0)
            return
        self._stack.setCurrentIndex(1)
        self._detail_title.setText(f"Die # {agg.die}  ·  {agg.material}")
        bits = [
            f"{agg.short_lines} short line(s)",
            f"{agg.late_lines} LATE",
            f"on hand: {agg.qty_on_hand}",
            f"on PO: {agg.qty_on_po}",
        ]
        if agg.next_wanted:
            bits.append(f"next wanted: {agg.next_wanted.strftime('%m/%d/%Y')}")
        self._detail_subtitle.setText(" · ".join(bits))

        self._populate_inventory(agg)
        self._populate_demand(agg)
        self._populate_pos(agg)
        self._populate_actions(agg)

    def _populate_inventory(self, agg: DieAggregate):
        rows = sorted(agg.inventory_rows, key=lambda r: (_safe_int(r.get("Length")), str(r.get("PartNumber") or "")))
        self._inventory_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            on_hand = _safe_int(row.get("QuantityOnHand"))
            self._inventory_table.setItem(r, 0, QTableWidgetItem(str(row.get("PartNumber") or "")))
            self._inventory_table.setItem(r, 1, QTableWidgetItem(str(row.get("Length") or "")))
            self._inventory_table.setItem(r, 2, QTableWidgetItem(str(row.get("Material") or "")))
            on_hand_item = QTableWidgetItem(str(on_hand))
            if on_hand <= 0:
                on_hand_item.setForeground(QColor(COLOR_LATE_TEXT))
            self._inventory_table.setItem(r, 3, on_hand_item)
            self._inventory_table.setItem(r, 4, QTableWidgetItem(str(row.get("LeadTime") or "")))

    def _populate_demand(self, agg: DieAggregate):
        cutoff = self._horizon_cutoff()
        rows = list(agg.shortage_rows)
        if cutoff:
            rows = [r for r in rows if (_safe_date(r.get("WantedDate")) or date.max) <= cutoff]
        rows.sort(key=lambda r: (_safe_date(r.get("WantedDate")) or date.max, str(r.get("PartNumber") or "")))
        self._demand_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            tag = str(row.get("AllocStatus") or "OK").upper()
            self._demand_table.setItem(r, 0, QTableWidgetItem(_fmt_date(row.get("WantedDate"))))
            self._demand_table.setItem(r, 1, QTableWidgetItem(str(row.get("WorkOrder") or "")))
            self._demand_table.setItem(r, 2, QTableWidgetItem(str(row.get("PartNumber") or "")))
            self._demand_table.setItem(r, 3, QTableWidgetItem(str(row.get("NeededLength") or "")))
            self._demand_table.setItem(r, 4, QTableWidgetItem(str(_safe_int(row.get("QtyNeeded")))))
            self._demand_table.setItem(r, 5, QTableWidgetItem(str(_safe_int(row.get("AllocCovered")))))
            self._demand_table.setItem(r, 6, QTableWidgetItem(str(_safe_int(row.get("AllocShort")))))
            self._demand_table.setItem(r, 7, _status_item(tag, tag))
            note_bits = []
            coverage_notes = str(row.get("CoverageNotes") or "")
            if coverage_notes:
                note_bits.append(coverage_notes)
            proposal = str(row.get("AllocProposal") or "")
            if proposal:
                note_bits.append(proposal)
            self._demand_table.setItem(r, 8, QTableWidgetItem(" · ".join(note_bits)))
        self._demand_table.resizeRowsToContents()

    def _populate_pos(self, agg: DieAggregate):
        rows = sorted(agg.pos, key=lambda r: (_safe_date(r.get("ETA")) or date.max))
        self._po_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            self._po_table.setItem(r, 0, QTableWidgetItem(str(row.get("PurchaseOrderNumber") or "")))
            self._po_table.setItem(r, 1, QTableWidgetItem(_fmt_date(row.get("CreateDate"))))
            self._po_table.setItem(r, 2, QTableWidgetItem(_fmt_date(row.get("ETA"))))
            self._po_table.setItem(r, 3, QTableWidgetItem(str(row.get("VendorName") or "")))
            self._po_table.setItem(r, 4, QTableWidgetItem(str(row.get("PartNumber") or "")))
            self._po_table.setItem(r, 5, QTableWidgetItem(str(row.get("Length") or "")))
            self._po_table.setItem(r, 6, QTableWidgetItem(str(_safe_int(row.get("Quantity")))))
            self._po_table.setItem(r, 7, QTableWidgetItem(str(_safe_int(row.get("QuantityReceived")))))
            self._po_table.setItem(r, 8, QTableWidgetItem(str(_safe_int(row.get("QtyIncoming")))))

    def _populate_actions(self, agg: DieAggregate):
        actionable = [r for r in agg.shortage_rows if _safe_int(r.get("AllocShort")) > 0]
        actionable.sort(key=lambda r: (_safe_date(r.get("OrderByDate")) or date.max))
        self._actions_table.setRowCount(len(actionable))
        for r, row in enumerate(actionable):
            tag = str(row.get("AllocStatus") or "SHORT").upper()
            weld = row.get("WeldCandidates") or []
            if weld:
                top = weld[0]
                gap = _safe_int(row.get("NeededLength")) - _safe_int(top.get("length"))
                weld_text = (
                    f'{top.get("qty")}× {top.get("length")}" '
                    f'({top.get("label")}) — weld ~{gap}"'
                )
            else:
                weld_text = ""
            self._actions_table.setItem(r, 0, QTableWidgetItem(_fmt_date(row.get("OrderByDate"))))
            self._actions_table.setItem(r, 1, QTableWidgetItem(str(row.get("PartNumber") or "")))
            self._actions_table.setItem(r, 2, QTableWidgetItem(str(row.get("NeededLength") or "")))
            self._actions_table.setItem(r, 3, QTableWidgetItem(str(_safe_int(row.get("AllocShort")))))
            self._actions_table.setItem(r, 4, QTableWidgetItem(_fmt_date(row.get("WantedDate"))))
            self._actions_table.setItem(r, 5, QTableWidgetItem(str(row.get("WorkOrder") or "")))
            self._actions_table.setItem(r, 6, _status_item(tag, tag))
            self._actions_table.setItem(r, 7, QTableWidgetItem(weld_text))
