"""Global Fluent-inspired QSS for the Schedule client.

Apply with::

    from ui.theme import apply_fluent_theme
    apply_fluent_theme(app)

The stylesheet sets a sensible default for every common Qt widget so that
individual screens don't need to reinvent typography, spacing or colours.
Per-widget ``setStyleSheet`` calls still win when they need to override
something, but those should be the exception, not the rule.
"""
from __future__ import annotations

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

from .style_tokens import (
    COLOR_BG_APP,
    COLOR_BG_SUBTLE,
    COLOR_BORDER,
    COLOR_BORDER_STRONG,
    COLOR_DANGER,
    COLOR_DIVIDER,
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_PRIMARY_PRESSED,
    COLOR_PRIMARY_SUBTLE_BG,
    COLOR_SELECTION_BG,
    COLOR_SELECTION_TEXT,
    COLOR_SURFACE,
    COLOR_SURFACE_ALT,
    COLOR_TEXT_DISABLED,
    COLOR_TEXT_ON_ACCENT,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_TERTIARY,
    CONTROL_HEIGHT,
    FONT_FAMILY_FALLBACK,
    FONT_FAMILY_PRIMARY,
    FONT_SIZE_BODY,
    RADIUS_LG,
    RADIUS_MD,
    RADIUS_SM,
)


# Order matters: pick the first installed Segoe UI Variable family.
PREFERRED_FONT_FAMILIES = (
    "Segoe UI Variable Text",
    "Segoe UI Variable",
    "Segoe UI",
    "Inter",
    "Helvetica Neue",
    "Arial",
)


def _resolve_font_family() -> str:
    """Pick the best available Fluent-style font installed on the system."""
    available = set(QFontDatabase.families())
    for family in PREFERRED_FONT_FAMILIES:
        if family in available:
            return family
    return next(iter(available), "Sans Serif")


def build_fluent_qss(base_font_size: int = FONT_SIZE_BODY) -> str:
    """Return the global Fluent stylesheet, scaled to ``base_font_size`` (px)."""
    font_family_stack = f"'{FONT_FAMILY_PRIMARY}', {FONT_FAMILY_FALLBACK}"

    return f"""
    /* ============================================================
       Base — typography and window canvas
       ============================================================ */
    QWidget {{
        font-family: {font_family_stack};
        font-size: {base_font_size}px;
        color: {COLOR_TEXT_PRIMARY};
    }}
    QMainWindow, QDialog {{
        background-color: {COLOR_BG_APP};
    }}
    QToolTip {{
        background-color: {COLOR_SURFACE};
        color: {COLOR_TEXT_PRIMARY};
        border: 1px solid {COLOR_BORDER_STRONG};
        border-radius: {RADIUS_SM}px;
        padding: 6px 10px;
        font-size: {base_font_size - 1}px;
    }}

    /* ============================================================
       Push buttons — default look (ModernButton overrides as needed)
       ============================================================ */
    QPushButton {{
        background-color: {COLOR_SURFACE};
        color: {COLOR_TEXT_PRIMARY};
        border: 1px solid {COLOR_BORDER_STRONG};
        border-radius: {RADIUS_MD}px;
        padding: 6px 14px;
        min-height: 28px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {COLOR_BG_SUBTLE};
        border-color: {COLOR_BORDER_STRONG};
    }}
    QPushButton:pressed {{
        background-color: {COLOR_SURFACE_ALT};
    }}
    QPushButton:disabled {{
        background-color: {COLOR_BG_SUBTLE};
        color: {COLOR_TEXT_DISABLED};
        border-color: {COLOR_BORDER};
    }}
    QPushButton:focus {{
        outline: none;
        border-color: {COLOR_PRIMARY};
    }}

    /* ============================================================
       Inputs — QLineEdit, QPlainTextEdit, QTextEdit
       ============================================================ */
    QLineEdit, QPlainTextEdit, QTextEdit {{
        background-color: {COLOR_SURFACE};
        color: {COLOR_TEXT_PRIMARY};
        border: 1px solid {COLOR_BORDER_STRONG};
        border-radius: {RADIUS_MD}px;
        padding: 6px 10px;
        selection-background-color: {COLOR_SELECTION_BG};
        selection-color: {COLOR_SELECTION_TEXT};
    }}
    QLineEdit:hover, QPlainTextEdit:hover, QTextEdit:hover {{
        border-color: {COLOR_TEXT_TERTIARY};
    }}
    QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
        border-color: {COLOR_PRIMARY};
    }}
    QLineEdit:disabled, QPlainTextEdit:disabled, QTextEdit:disabled {{
        background-color: {COLOR_BG_SUBTLE};
        color: {COLOR_TEXT_DISABLED};
    }}

    /* ============================================================
       ComboBox + DateEdit + SpinBox — Fluent combo
       ============================================================ */
    QComboBox, QDateEdit, QTimeEdit, QDateTimeEdit, QSpinBox, QDoubleSpinBox {{
        background-color: {COLOR_SURFACE};
        color: {COLOR_TEXT_PRIMARY};
        border: 1px solid {COLOR_BORDER_STRONG};
        border-radius: {RADIUS_MD}px;
        padding: 5px 10px;
        min-height: 24px;
        selection-background-color: {COLOR_SELECTION_BG};
        selection-color: {COLOR_SELECTION_TEXT};
    }}
    QComboBox:hover, QDateEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
        border-color: {COLOR_TEXT_TERTIARY};
    }}
    QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {COLOR_PRIMARY};
    }}
    QComboBox:disabled, QDateEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
        background-color: {COLOR_BG_SUBTLE};
        color: {COLOR_TEXT_DISABLED};
    }}
    QComboBox::drop-down, QDateEdit::drop-down {{
        border: none;
        width: 22px;
        background: transparent;
    }}
    QComboBox::down-arrow, QDateEdit::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {COLOR_TEXT_SECONDARY};
        margin-right: 8px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {COLOR_SURFACE};
        border: 1px solid {COLOR_BORDER_STRONG};
        border-radius: {RADIUS_MD}px;
        padding: 4px;
        selection-background-color: {COLOR_PRIMARY_SUBTLE_BG};
        selection-color: {COLOR_TEXT_PRIMARY};
        outline: none;
    }}
    QComboBox QAbstractItemView::item {{
        padding: 6px 10px;
        border-radius: {RADIUS_SM}px;
        margin: 1px 2px;
    }}

    /* ============================================================
       Labels
       ============================================================ */
    QLabel {{
        background: transparent;
        color: {COLOR_TEXT_PRIMARY};
    }}
    QLabel:disabled {{
        color: {COLOR_TEXT_DISABLED};
    }}

    /* ============================================================
       Tab widgets — Fluent underline tabs
       ============================================================ */
    QTabWidget::pane {{
        border: none;
        background: transparent;
        top: -1px;
    }}
    QTabBar {{
        background: transparent;
        qproperty-drawBase: 0;
    }}
    QTabBar::tab {{
        background: transparent;
        color: {COLOR_TEXT_SECONDARY};
        padding: 9px 16px;
        margin: 0 2px;
        border: none;
        border-bottom: 2px solid transparent;
        font-weight: 600;
        min-width: 80px;
    }}
    QTabBar::tab:hover {{
        color: {COLOR_TEXT_PRIMARY};
        background: {COLOR_BG_SUBTLE};
    }}
    QTabBar::tab:selected {{
        color: {COLOR_PRIMARY};
        border-bottom: 2px solid {COLOR_PRIMARY};
        background: transparent;
    }}
    QTabBar::tab:disabled {{
        color: {COLOR_TEXT_DISABLED};
    }}

    /* ============================================================
       Tables — Fluent flat, hairline gridlines
       ============================================================ */
    QTableView, QTableWidget {{
        background-color: {COLOR_SURFACE};
        alternate-background-color: {COLOR_BG_SUBTLE};
        color: {COLOR_TEXT_PRIMARY};
        gridline-color: {COLOR_DIVIDER};
        border: 1px solid {COLOR_BORDER};
        border-radius: {RADIUS_LG}px;
        selection-background-color: {COLOR_SELECTION_BG};
        selection-color: {COLOR_SELECTION_TEXT};
        outline: none;
    }}
    QTableView::item, QTableWidget::item {{
        padding: 8px 12px;
        border: none;
    }}
    QTableView::item:selected, QTableWidget::item:selected {{
        background: {COLOR_SELECTION_BG};
        color: {COLOR_SELECTION_TEXT};
    }}
    QTableView::item:hover:!selected, QTableWidget::item:hover:!selected {{
        background: {COLOR_PRIMARY_SUBTLE_BG};
    }}
    QHeaderView {{
        background-color: {COLOR_SURFACE};
        border: none;
    }}
    QHeaderView::section {{
        background-color: {COLOR_SURFACE};
        color: {COLOR_TEXT_SECONDARY};
        padding: 9px 12px;
        border: none;
        border-bottom: 1px solid {COLOR_BORDER};
        border-right: 1px solid {COLOR_DIVIDER};
        font-weight: 600;
    }}
    QHeaderView::section:hover {{
        background-color: {COLOR_BG_SUBTLE};
        color: {COLOR_TEXT_PRIMARY};
    }}
    QHeaderView::section:first {{
        border-top-left-radius: {RADIUS_LG}px;
    }}
    QHeaderView::section:last {{
        border-top-right-radius: {RADIUS_LG}px;
        border-right: none;
    }}
    QTableCornerButton::section {{
        background: {COLOR_SURFACE};
        border: none;
        border-bottom: 1px solid {COLOR_BORDER};
    }}

    /* ============================================================
       Calendar widget — QDateEdit calendar popup
       The global QTableView / QHeaderView / QWidget rules above leak
       into the internal calendar grid and weekday header, which is
       why day numbers go invisible past the first row. We must
       explicitly RESET those rules here, not just add new ones.
       ============================================================ */
    QCalendarWidget {{
        background-color: {COLOR_SURFACE};
    }}
    QCalendarWidget QWidget {{
        alternate-background-color: {COLOR_BG_SUBTLE};
    }}
    /* Navigation bar (month/year header) */
    QCalendarWidget QWidget#qt_calendar_navigationbar {{
        background-color: {COLOR_BG_SUBTLE};
        border-bottom: 1px solid {COLOR_BORDER};
    }}
    QCalendarWidget QToolButton {{
        color: {COLOR_TEXT_PRIMARY};
        background-color: transparent;
        border: 1px solid transparent;
        border-radius: {RADIUS_SM}px;
        padding: 4px 8px;
        margin: 2px;
        font-weight: 600;
    }}
    QCalendarWidget QToolButton:hover {{
        background-color: {COLOR_SURFACE};
        border-color: {COLOR_BORDER};
    }}
    QCalendarWidget QToolButton:pressed {{
        background-color: {COLOR_BORDER};
    }}
    QCalendarWidget QToolButton::menu-indicator {{
        image: none;
    }}
    QCalendarWidget QMenu {{
        background-color: {COLOR_SURFACE};
        color: {COLOR_TEXT_PRIMARY};
        border: 1px solid {COLOR_BORDER_STRONG};
    }}
    QCalendarWidget QSpinBox {{
        background-color: {COLOR_SURFACE};
        color: {COLOR_TEXT_PRIMARY};
        border: 1px solid {COLOR_BORDER_STRONG};
        border-radius: {RADIUS_SM}px;
        padding: 2px 6px;
    }}
    /* Day grid — restore Qt's defaults that our table rules pushed out.
       padding:0 on items is required so day numbers stay centred and
       readable; the global QTableView::item rule sets 8px which makes
       the cells too tall and pushes text out of the visible area. */
    QCalendarWidget QAbstractItemView {{
        background-color: {COLOR_SURFACE};
        alternate-background-color: {COLOR_SURFACE};
        color: {COLOR_TEXT_PRIMARY};
        selection-background-color: {COLOR_PRIMARY};
        selection-color: {COLOR_TEXT_ON_ACCENT};
        outline: none;
        gridline-color: transparent;
        show-decoration-selected: 1;
    }}
    QCalendarWidget QAbstractItemView::item {{
        padding: 0px;
        border: none;
        background: transparent;
        color: {COLOR_TEXT_PRIMARY};
    }}
    QCalendarWidget QAbstractItemView::item:hover {{
        background: {COLOR_PRIMARY_SUBTLE_BG};
        color: {COLOR_TEXT_PRIMARY};
    }}
    QCalendarWidget QAbstractItemView::item:selected {{
        background: {COLOR_PRIMARY};
        color: {COLOR_TEXT_ON_ACCENT};
    }}
    /* Days from neighbouring months — keep visible but muted */
    QCalendarWidget QAbstractItemView::item:disabled,
    QCalendarWidget QAbstractItemView:disabled {{
        color: {COLOR_TEXT_DISABLED};
    }}
    /* Weekday header (Sun, Mon, …) — global QHeaderView::section rules
       give it 9px padding and a right border that breaks the layout. */
    QCalendarWidget QHeaderView {{
        background-color: {COLOR_SURFACE};
    }}
    QCalendarWidget QHeaderView::section {{
        background-color: {COLOR_SURFACE};
        color: {COLOR_TEXT_SECONDARY};
        padding: 4px 0;
        border: none;
        border-bottom: 1px solid {COLOR_BORDER};
        font-weight: 600;
    }}
    QCalendarWidget QHeaderView::section:hover {{
        background-color: {COLOR_SURFACE};
    }}

    /* ============================================================
       Menus — Fluent flyout
       ============================================================ */
    QMenuBar {{
        background-color: {COLOR_SURFACE};
        color: {COLOR_TEXT_PRIMARY};
        border-bottom: 1px solid {COLOR_BORDER};
    }}
    QMenuBar::item {{
        padding: 6px 12px;
        background: transparent;
        border-radius: {RADIUS_SM}px;
    }}
    QMenuBar::item:selected {{
        background: {COLOR_BG_SUBTLE};
    }}
    QMenu {{
        background-color: {COLOR_SURFACE};
        border: 1px solid {COLOR_BORDER_STRONG};
        border-radius: {RADIUS_MD}px;
        padding: 4px;
        color: {COLOR_TEXT_PRIMARY};
    }}
    QMenu::item {{
        padding: 7px 18px 7px 28px;
        border-radius: {RADIUS_SM}px;
        margin: 1px 2px;
    }}
    QMenu::item:selected {{
        background-color: {COLOR_PRIMARY_SUBTLE_BG};
        color: {COLOR_TEXT_PRIMARY};
    }}
    QMenu::item:disabled {{
        color: {COLOR_TEXT_DISABLED};
    }}
    QMenu::separator {{
        height: 1px;
        background: {COLOR_DIVIDER};
        margin: 4px 6px;
    }}

    /* ============================================================
       Checkboxes / radios
       ============================================================ */
    QCheckBox, QRadioButton {{
        spacing: 8px;
        color: {COLOR_TEXT_PRIMARY};
        background: transparent;
    }}
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {COLOR_BORDER_STRONG};
        background: {COLOR_SURFACE};
    }}
    QCheckBox::indicator {{
        border-radius: 3px;
    }}
    QRadioButton::indicator {{
        border-radius: 8px;
    }}
    QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
        border-color: {COLOR_PRIMARY};
    }}
    QCheckBox::indicator:checked {{
        background: {COLOR_PRIMARY};
        border-color: {COLOR_PRIMARY};
        image: none;
    }}
    QRadioButton::indicator:checked {{
        background: {COLOR_SURFACE};
        border: 5px solid {COLOR_PRIMARY};
    }}
    QCheckBox:disabled, QRadioButton:disabled {{
        color: {COLOR_TEXT_DISABLED};
    }}

    /* ============================================================
       Group boxes
       ============================================================ */
    QGroupBox {{
        background-color: {COLOR_SURFACE};
        border: 1px solid {COLOR_BORDER};
        border-radius: {RADIUS_LG}px;
        margin-top: 14px;
        padding: 12px;
        font-weight: 600;
        color: {COLOR_TEXT_PRIMARY};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 8px;
        left: 10px;
        background: transparent;
        color: {COLOR_TEXT_SECONDARY};
    }}

    /* ============================================================
       Scroll bars — slim Fluent style
       ============================================================ */
    QScrollBar:vertical {{
        background: transparent;
        width: 12px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: #C8C8C8;
        min-height: 32px;
        border-radius: 6px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: #A6A6A6;
    }}
    QScrollBar::handle:vertical:pressed {{
        background: #8A8A8A;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 12px;
        margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: #C8C8C8;
        min-width: 32px;
        border-radius: 6px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: #A6A6A6;
    }}
    QScrollBar::handle:horizontal:pressed {{
        background: #8A8A8A;
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        height: 0;
        width: 0;
        background: transparent;
        border: none;
    }}
    QScrollBar::add-page, QScrollBar::sub-page {{
        background: transparent;
    }}

    /* ============================================================
       Status bar — Fluent slim
       ============================================================ */
    QStatusBar {{
        background-color: {COLOR_SURFACE};
        border-top: 1px solid {COLOR_BORDER};
        color: {COLOR_TEXT_SECONDARY};
        padding: 4px 12px;
    }}
    QStatusBar::item {{
        border: none;
    }}

    /* ============================================================
       Progress bar
       ============================================================ */
    QProgressBar {{
        background-color: {COLOR_BG_SUBTLE};
        border: 1px solid {COLOR_BORDER};
        border-radius: {RADIUS_SM}px;
        text-align: center;
        color: {COLOR_TEXT_SECONDARY};
        height: 6px;
    }}
    QProgressBar::chunk {{
        background-color: {COLOR_PRIMARY};
        border-radius: {RADIUS_SM}px;
    }}

    /* ============================================================
       Splitter
       ============================================================ */
    QSplitter::handle {{
        background-color: {COLOR_BORDER};
    }}
    QSplitter::handle:horizontal {{
        width: 1px;
    }}
    QSplitter::handle:vertical {{
        height: 1px;
    }}

    /* ============================================================
       Tool buttons + dialog button box
       ============================================================ */
    QToolButton {{
        background-color: transparent;
        color: {COLOR_TEXT_PRIMARY};
        border: 1px solid transparent;
        border-radius: {RADIUS_SM}px;
        padding: 5px 8px;
    }}
    QToolButton:hover {{
        background-color: {COLOR_BG_SUBTLE};
        border-color: {COLOR_BORDER};
    }}
    QToolButton:pressed {{
        background-color: {COLOR_SURFACE_ALT};
    }}
    QDialogButtonBox QPushButton {{
        min-width: 96px;
    }}

    /* ============================================================
       Message boxes — Fluent dialog
       ============================================================ */
    QMessageBox {{
        background-color: {COLOR_SURFACE};
    }}
    QMessageBox QLabel {{
        color: {COLOR_TEXT_PRIMARY};
    }}
    """


def apply_fluent_theme(
    app: QApplication,
    *,
    point_size: int | None = None,
    qss_px_size: int | None = None,
) -> str:
    """Install the Fluent theme on ``app`` and return the resolved font family.

    ``point_size`` controls ``QApplication.font()`` (points, used by widgets
    that don't explicitly set their font). ``qss_px_size`` controls the body
    font size in the global stylesheet (pixels). When omitted, the px size is
    derived from the point size at the conventional 1 pt = 1.333 px ratio.
    """
    family = _resolve_font_family()
    pt = point_size if point_size and point_size > 0 else 9
    px = qss_px_size if qss_px_size and qss_px_size > 0 else max(11, int(round(pt * 1.333)))

    font = QFont(family, pt)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(font)

    app.setStyleSheet(build_fluent_qss(px))
    return family
