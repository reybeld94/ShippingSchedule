from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Iterable, Optional, Set, Tuple

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialogButtonBox,
    QMenu,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)


class SelectAllCheckBox(QCheckBox):
    """Tri-state checkbox that only toggles between checked and unchecked."""

    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(label, parent)
        self.setTristate(True)

    def nextCheckState(self) -> None:  # noqa: D401
        """Toggle directly between checked and unchecked states."""

        current = self.checkState()
        if current == Qt.CheckState.Checked:
            self.setCheckState(Qt.CheckState.Unchecked)
        else:
            self.setCheckState(Qt.CheckState.Checked)


class DateFilterPopup(QMenu):
    """Hierarchical date filter shown inline as a drop-down menu."""

    def __init__(
        self,
        parent=None,
        *,
        available_dates: Iterable[date],
        has_blank: bool,
        selected_dates: Optional[Set[date]] = None,
        include_blank: bool = True,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("DateFilterPopup")

        self._dates = sorted(set(available_dates))
        self._has_blank = has_blank
        self._initial_selection = None if selected_dates is None else set(selected_dates)
        self._initial_blank = include_blank
        self._accepted = False

        container = QWidget(self)
        container.setMinimumWidth(280)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.select_all_checkbox = SelectAllCheckBox("Select All", container)
        layout.addWidget(self.select_all_checkbox)

        self.tree = QTreeWidget(container)
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(True)
        self.tree.setUniformRowHeights(True)
        layout.addWidget(self.tree)

        if self._has_blank:
            self.blank_checkbox = QCheckBox("Blanks", container)
            layout.addWidget(self.blank_checkbox)
        else:
            self.blank_checkbox = None

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=container,
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self._reject)
        layout.addWidget(buttons)

        action = QWidgetAction(self)
        action.setDefaultWidget(container)
        self.addAction(action)

        self._populate_tree()
        self._connect_signals()
        self._restore_initial_state()

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------
    def _populate_tree(self) -> None:
        if not self._dates:
            return

        dates_by_year: dict[int, dict[int, list[date]]] = defaultdict(lambda: defaultdict(list))
        for dt in self._dates:
            dates_by_year[dt.year][dt.month].append(dt)

        for year in sorted(dates_by_year.keys(), reverse=True):
            year_item = QTreeWidgetItem(self.tree)
            year_item.setText(0, str(year))
            year_item.setFlags(
                (year_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                & ~Qt.ItemFlag.ItemIsAutoTristate
            )

            for month in sorted(dates_by_year[year].keys(), reverse=True):
                month_item = QTreeWidgetItem(year_item)
                month_item.setText(0, date(year, month, 1).strftime("%B"))
                month_item.setFlags(
                    (month_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    & ~Qt.ItemFlag.ItemIsAutoTristate
                )

                for dt in sorted(dates_by_year[year][month], reverse=True):
                    day_item = QTreeWidgetItem(month_item)
                    day_item.setText(0, dt.strftime("%b %d, %Y"))
                    day_item.setFlags(
                        (day_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                        & ~Qt.ItemFlag.ItemIsAutoTristate
                    )
                    day_item.setData(0, Qt.ItemDataRole.UserRole, dt)

    def _connect_signals(self) -> None:
        self.tree.itemChanged.connect(self._on_tree_item_changed)
        self.select_all_checkbox.stateChanged.connect(self._on_select_all_state_changed)
        if self.blank_checkbox is not None:
            self.blank_checkbox.stateChanged.connect(lambda _: self._update_select_all_state())

    def _restore_initial_state(self) -> None:
        if self.blank_checkbox is not None:
            self.blank_checkbox.setChecked(self._initial_blank)

        default_state = Qt.CheckState.Checked if self._initial_selection is None else None

        for i in range(self.tree.topLevelItemCount()):
            year_item = self.tree.topLevelItem(i)
            self._apply_initial_state(year_item, default_state)

        self._update_parent_states()
        self._update_select_all_state()

    def _apply_initial_state(self, item: QTreeWidgetItem, default_state: Optional[Qt.CheckState]) -> None:
        if item.childCount() == 0:
            dt = item.data(0, Qt.ItemDataRole.UserRole)
            if dt is None:
                return
            if default_state is not None:
                item.setCheckState(0, default_state)
            else:
                state = Qt.CheckState.Checked if dt in self._initial_selection else Qt.CheckState.Unchecked
                item.setCheckState(0, state)
            return

        for idx in range(item.childCount()):
            self._apply_initial_state(item.child(idx), default_state)

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------
    def _on_tree_item_changed(self, item: QTreeWidgetItem, column: int) -> None:  # noqa: ARG002
        if item.childCount() > 0:
            state = item.checkState(0)
            for idx in range(item.childCount()):
                child = item.child(idx)
                child.setCheckState(0, state)
        else:
            self._update_parent_states(item)
        self._update_select_all_state()

    def _on_select_all_state_changed(self, state: int) -> None:
        if state == int(Qt.CheckState.PartiallyChecked):
            return
        qt_state = Qt.CheckState(state)
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            item.setCheckState(0, qt_state)
        if self.blank_checkbox is not None:
            self.blank_checkbox.setChecked(qt_state == Qt.CheckState.Checked)
        self._update_select_all_state()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _update_parent_states(self, start_item: Optional[QTreeWidgetItem] = None) -> None:
        if start_item is None:
            for i in range(self.tree.topLevelItemCount()):
                self._update_parent_states(self.tree.topLevelItem(i))
            return

        for child_index in range(start_item.childCount()):
            self._update_parent_states(start_item.child(child_index))

        if start_item.childCount() == 0:
            return

        checked = 0
        unchecked = 0
        for idx in range(start_item.childCount()):
            child_state = start_item.child(idx).checkState(0)
            if child_state == Qt.CheckState.Checked:
                checked += 1
            elif child_state == Qt.CheckState.Unchecked:
                unchecked += 1

        if checked == start_item.childCount():
            start_item.setCheckState(0, Qt.CheckState.Checked)
        elif unchecked == start_item.childCount():
            start_item.setCheckState(0, Qt.CheckState.Unchecked)
        else:
            start_item.setCheckState(0, Qt.CheckState.PartiallyChecked)

    def _update_select_all_state(self) -> None:
        total_days = 0
        checked_days = 0
        for i in range(self.tree.topLevelItemCount()):
            total, checked = self._count_day_states(self.tree.topLevelItem(i))
            total_days += total
            checked_days += checked

        blanks_checked = True if self.blank_checkbox is None else self.blank_checkbox.isChecked()

        if total_days == 0:
            state = Qt.CheckState.Checked if blanks_checked else Qt.CheckState.Unchecked
        else:
            if checked_days == 0 and not blanks_checked:
                state = Qt.CheckState.Unchecked
            elif checked_days == total_days and blanks_checked:
                state = Qt.CheckState.Checked
            elif checked_days == 0 and blanks_checked:
                state = Qt.CheckState.PartiallyChecked
            elif checked_days == total_days and not blanks_checked:
                state = Qt.CheckState.PartiallyChecked
            else:
                state = Qt.CheckState.PartiallyChecked

        self.select_all_checkbox.blockSignals(True)
        self.select_all_checkbox.setCheckState(state)
        self.select_all_checkbox.blockSignals(False)

    def _count_day_states(self, item: QTreeWidgetItem) -> tuple[int, int]:
        if item.childCount() == 0:
            return (1, 1) if item.checkState(0) == Qt.CheckState.Checked else (1, 0)

        total = 0
        checked = 0
        for idx in range(item.childCount()):
            sub_total, sub_checked = self._count_day_states(item.child(idx))
            total += sub_total
            checked += sub_checked
        return total, checked

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_filter_result(self) -> tuple[Optional[Set[date]], bool]:
        selected_dates: Set[date] = set()
        for i in range(self.tree.topLevelItemCount()):
            self._collect_checked_dates(self.tree.topLevelItem(i), selected_dates)

        blanks_selected = True if self.blank_checkbox is None else self.blank_checkbox.isChecked()
        if len(selected_dates) == len(self._dates) and (blanks_selected or not self._has_blank):
            return None, blanks_selected
        return selected_dates, blanks_selected

    def _collect_checked_dates(self, item: QTreeWidgetItem, result: Set[date]) -> None:
        if item.childCount() == 0:
            if item.checkState(0) == Qt.CheckState.Checked:
                dt = item.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(dt, date):
                    result.add(dt)
            return

        for idx in range(item.childCount()):
            self._collect_checked_dates(item.child(idx), result)

    def exec_at(self, global_pos: QPoint) -> Optional[Tuple[Optional[Set[date]], bool]]:
        """Show the popup at the requested position and return the selection."""

        self._accepted = False
        # Block until the menu is hidden
        self.exec(global_pos)
        if self._accepted:
            return self.get_filter_result()
        return None

    def _accept(self) -> None:
        self._accepted = True
        self.close()

    def _reject(self) -> None:
        self._accepted = False
        self.close()
