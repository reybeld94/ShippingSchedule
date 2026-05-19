"""Centralized message-box helpers with consistent Fluent styling.

Replaces the half-dozen ``show_professional_error`` / ``show_error`` /
``QMessageBox.question`` implementations scattered across the UI.

Usage::

    from ui.dialogs import show_error, show_info, show_warning, ask_confirm

    show_error(self, "Could not save shipment", detail=str(exc))

    if ask_confirm(self, "Delete this user?", title="Confirm delete"):
        ...
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import QMessageBox, QWidget

from .style_tokens import (
    COLOR_BG_SUBTLE,
    COLOR_BORDER,
    COLOR_BORDER_STRONG,
    COLOR_DANGER,
    COLOR_DANGER_HOVER,
    COLOR_DANGER_PRESSED,
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_PRIMARY_PRESSED,
    COLOR_SURFACE,
    COLOR_TEXT_DISABLED,
    COLOR_TEXT_ON_ACCENT,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    RADIUS_MD,
)


def _build_stylesheet(*, destructive: bool = False) -> str:
    """Return the QSS applied to every helper-rendered message box.

    When ``destructive`` is True the primary button uses the danger palette so
    confirmation dialogs telegraph the consequence.
    """
    accent_bg = COLOR_DANGER if destructive else COLOR_PRIMARY
    accent_hover = COLOR_DANGER_HOVER if destructive else COLOR_PRIMARY_HOVER
    accent_pressed = COLOR_DANGER_PRESSED if destructive else COLOR_PRIMARY_PRESSED

    return f"""
        QMessageBox {{
            background-color: {COLOR_SURFACE};
        }}
        QMessageBox QLabel {{
            color: {COLOR_TEXT_PRIMARY};
            padding: 4px 8px 12px 8px;
        }}
        QMessageBox QPushButton {{
            background-color: {COLOR_SURFACE};
            color: {COLOR_TEXT_PRIMARY};
            border: 1px solid {COLOR_BORDER_STRONG};
            border-radius: {RADIUS_MD}px;
            padding: 6px 18px;
            min-width: 88px;
            font-weight: 600;
        }}
        QMessageBox QPushButton:hover {{
            background-color: {COLOR_BG_SUBTLE};
            border-color: {COLOR_BORDER_STRONG};
        }}
        QMessageBox QPushButton:pressed {{
            background-color: {COLOR_BG_SUBTLE};
            border-color: {COLOR_TEXT_SECONDARY};
        }}
        QMessageBox QPushButton:default {{
            background-color: {accent_bg};
            color: {COLOR_TEXT_ON_ACCENT};
            border-color: {accent_bg};
        }}
        QMessageBox QPushButton:default:hover {{
            background-color: {accent_hover};
            border-color: {accent_hover};
        }}
        QMessageBox QPushButton:default:pressed {{
            background-color: {accent_pressed};
            border-color: {accent_pressed};
        }}
        QMessageBox QPushButton:disabled {{
            background-color: {COLOR_BG_SUBTLE};
            color: {COLOR_TEXT_DISABLED};
            border-color: {COLOR_BORDER};
        }}
    """


def _show(
    parent: Optional[QWidget],
    *,
    icon: QMessageBox.Icon,
    title: str,
    text: str,
    detail: Optional[str] = None,
    destructive: bool = False,
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Ok,
    default_button: Optional[QMessageBox.StandardButton] = None,
) -> QMessageBox.StandardButton:
    """Shared implementation: build a styled message box and return the result."""
    msg = QMessageBox(parent)
    msg.setIcon(icon)
    msg.setWindowTitle(title)
    msg.setText(text)
    if detail:
        msg.setInformativeText(detail)
    msg.setStandardButtons(buttons)
    if default_button is not None:
        msg.setDefaultButton(default_button)
    msg.setStyleSheet(_build_stylesheet(destructive=destructive))
    return QMessageBox.StandardButton(msg.exec())


def show_info(
    parent: Optional[QWidget],
    text: str,
    *,
    title: str = "Information",
    detail: Optional[str] = None,
) -> None:
    """Informational message with a single OK button."""
    _show(
        parent,
        icon=QMessageBox.Icon.Information,
        title=title,
        text=text,
        detail=detail,
    )


def show_warning(
    parent: Optional[QWidget],
    text: str,
    *,
    title: str = "Warning",
    detail: Optional[str] = None,
) -> None:
    """Non-blocking warning with a single OK button."""
    _show(
        parent,
        icon=QMessageBox.Icon.Warning,
        title=title,
        text=text,
        detail=detail,
    )


def show_error(
    parent: Optional[QWidget],
    text: str,
    *,
    title: str = "Error",
    detail: Optional[str] = None,
) -> None:
    """Error dialog with a single OK button."""
    _show(
        parent,
        icon=QMessageBox.Icon.Critical,
        title=title,
        text=text,
        detail=detail,
    )


def ask_confirm(
    parent: Optional[QWidget],
    text: str,
    *,
    title: str = "Confirm",
    detail: Optional[str] = None,
    destructive: bool = False,
    default_no: bool = True,
) -> bool:
    """Yes/No confirmation. Returns True when the user accepts.

    Set ``destructive=True`` for delete-style prompts so the accept button is
    rendered in the danger palette. ``default_no=True`` (the default) keeps
    accidental Enter presses from confirming irreversible actions.
    """
    default = (
        QMessageBox.StandardButton.No if default_no else QMessageBox.StandardButton.Yes
    )
    result = _show(
        parent,
        icon=QMessageBox.Icon.Question,
        title=title,
        text=text,
        detail=detail,
        destructive=destructive,
        buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        default_button=default,
    )
    return result == QMessageBox.StandardButton.Yes
