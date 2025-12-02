from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QHBoxLayout,
    QMessageBox,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

import requests

from .widgets import ModernButton, ModernLineEdit, ModernComboBox, ProfessionalCard
from core.config import get_server_url, REQUEST_TIMEOUT, MODERN_FONT
from .utils import apply_scaled_font, get_base_font_size


class UserFormDialog(QDialog):
    """Dialogo para crear o editar usuarios"""

    def __init__(self, token, user=None):
        super().__init__()
        self.token = token
        self.user = user or {}
        self.setWindowTitle("Edit User" if user else "Create User")
        self.setMinimumSize(400, 300)
        self.setup_ui()
        if user:
            self.populate(user)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        card = ProfessionalCard("User")
        form_layout = QVBoxLayout()

        self.username_edit = ModernLineEdit("Username")
        self.email_edit = ModernLineEdit("Email")
        self.password_edit = ModernLineEdit("Password")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.role_combo = ModernComboBox()
        self.role_combo.addItems(["read", "write", "admin"])

        form_layout.addWidget(self._create_form_label("Username"))
        form_layout.addWidget(self.username_edit)
        form_layout.addWidget(self._create_form_label("Email"))
        form_layout.addWidget(self.email_edit)
        form_layout.addWidget(self._create_form_label("Password"))
        form_layout.addWidget(self.password_edit)
        form_layout.addWidget(self._create_form_label("Role"))
        form_layout.addWidget(self.role_combo)
        card.add_layout(form_layout)

        button_layout = QHBoxLayout()
        save_btn = ModernButton("Save", "primary")
        cancel_btn = ModernButton("Cancel", "secondary")
        save_btn.clicked.connect(self.save)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)

        layout.addWidget(card)
        layout.addLayout(button_layout)

    def _create_form_label(self, text: str) -> QLabel:
        """Create a consistently styled form label."""
        label = QLabel(text)
        apply_scaled_font(label, offset=1, weight=QFont.Weight.Medium)
        label.setStyleSheet("color: #374151;")
        return label

    def populate(self, user):
        self.username_edit.setText(user.get("username", ""))
        self.email_edit.setText(user.get("email", ""))
        self.role_combo.setCurrentText(user.get("role", "read"))

    def save(self):
        data = {
            "username": self.username_edit.text().strip(),
            "email": self.email_edit.text().strip(),
            "role": self.role_combo.currentText(),
        }
        password = self.password_edit.text().strip()
        if password:
            data["password"] = password
        if not data["username"] or not data["email"]:
            self.show_error("Username and email are required")
            return
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            server_url = get_server_url()
            if self.user:
                resp = requests.put(
                    f"{server_url}/users/{self.user['id']}",
                    json=data,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                )
            else:
                data["password"] = password
                resp = requests.post(
                    f"{server_url}/users",
                    json=data,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                )
            if resp.status_code in (200, 201):
                self.accept()
            else:
                msg = resp.json().get("detail", resp.text)
                self.show_error(msg)
        except Exception as e:
            self.show_error(str(e))

    def show_error(self, message):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Error")
        msg.setText(message)
        base = get_base_font_size()
        label_size = max(8, base + 3)
        button_size = max(8, base + 2)
        msg.setStyleSheet(
            f"""
            QMessageBox {{
                background: #FFFFFF;
                font-family: '{MODERN_FONT}';
            }}
            QMessageBox QLabel {{
                color: #374151;
                font-size: {label_size}px;
                padding: 8px;
            }}
            QMessageBox QPushButton {{
                background: #3B82F6;
                color: white;
                border: none;
                padding: 6px 20px;
                border-radius: 6px;
                font-weight: 500;
                font-size: {button_size}px;
                min-width: 80px;
            }}
            QMessageBox QPushButton:hover {{
                background: #2563EB;
            }}
        """
        )
        msg.exec()


class UserManagementDialog(QDialog):
    """Interfaz para administrar usuarios"""

    def __init__(self, token):
        super().__init__()
        self.token = token
        self.setWindowTitle("User Management")
        self.setMinimumSize(500, 400)
        self.setup_ui()
        self.load_users()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Username", "Email", "Role"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header_font = max(8, get_base_font_size() + 3)
        self.table.setStyleSheet(
            f"""
    QHeaderView::section {{
        background-color: #E5E5E5;
        color: #000000;
        padding: 8px 4px;
        border: none;
        border-right: 1px solid #D1D5DB;
        font-size: {header_font}px;
        font-weight: 600;
    }}
        """
        )
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.add_btn = ModernButton("Add", "primary")
        self.edit_btn = ModernButton("Edit", "secondary")
        self.delete_btn = ModernButton("Delete", "danger")
        self.add_btn.clicked.connect(self.add_user)
        self.edit_btn.clicked.connect(self.edit_user)
        self.delete_btn.clicked.connect(self.delete_user)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        layout.addLayout(btn_layout)

    def load_users(self):
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            server_url = get_server_url()
            resp = requests.get(f"{server_url}/users", headers=headers, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                users = resp.json()
                self.table.setRowCount(len(users))
                for row, user in enumerate(users):
                    self.table.setItem(row, 0, QTableWidgetItem(str(user["id"])))
                    self.table.setItem(row, 1, QTableWidgetItem(user["username"]))
                    self.table.setItem(row, 2, QTableWidgetItem(user["email"]))
                    self.table.setItem(row, 3, QTableWidgetItem(user["role"]))
            else:
                self.show_error(resp.text)
        except Exception as e:
            self.show_error(str(e))

    def get_selected_user(self):
        row = self.table.currentRow()
        if row == -1:
            return None
        return {
            "id": int(self.table.item(row, 0).text()),
            "username": self.table.item(row, 1).text(),
            "email": self.table.item(row, 2).text(),
            "role": self.table.item(row, 3).text(),
        }

    def add_user(self):
        dlg = UserFormDialog(self.token)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_users()

    def _create_form_label(self, text: str) -> QLabel:
        label = QLabel(text)
        apply_scaled_font(label, offset=1, weight=QFont.Weight.Medium)
        label.setStyleSheet("color: #374151;")
        return label

    def edit_user(self):
        user = self.get_selected_user()
        if not user:
            self.show_error("Select a user")
            return
        dlg = UserFormDialog(self.token, user)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_users()

    def delete_user(self):
        user = self.get_selected_user()
        if not user:
            self.show_error("Select a user")
            return
        msg = QMessageBox.question(
            self,
            "Confirm",
            f"Delete user {user['username']}?",
        )
        if msg == QMessageBox.StandardButton.Yes:
            headers = {"Authorization": f"Bearer {self.token}"}
            try:
                server_url = get_server_url()
                resp = requests.delete(
                    f"{server_url}/users/{user['id']}",
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                )
                if resp.status_code == 200:
                    self.load_users()
                else:
                    self.show_error(resp.text)
            except Exception as e:
                self.show_error(str(e))

    def show_error(self, message):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Error")
        msg.setText(message)
        msg.exec()
