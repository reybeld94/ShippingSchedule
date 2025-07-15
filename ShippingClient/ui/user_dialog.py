from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QHBoxLayout, QMessageBox, QLineEdit
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

import requests

from .widgets import ModernButton, ModernLineEdit, ModernComboBox, ProfessionalCard
from core.config import SERVER_URL, REQUEST_TIMEOUT, MODERN_FONT

class UserManagementDialog(QDialog):
    def __init__(self, token):
        super().__init__()
        self.token = token
        self.setWindowTitle("Create User")
        self.setMinimumSize(400, 300)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        card = ProfessionalCard("New User")
        form_layout = QVBoxLayout()

        self.username_edit = ModernLineEdit("Username")
        self.email_edit = ModernLineEdit("Email")
        self.password_edit = ModernLineEdit("Password")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.role_combo = ModernComboBox()
        self.role_combo.addItems(["read", "write"])

        form_layout.addWidget(QLabel("Username"))
        form_layout.addWidget(self.username_edit)
        form_layout.addWidget(QLabel("Email"))
        form_layout.addWidget(self.email_edit)
        form_layout.addWidget(QLabel("Password"))
        form_layout.addWidget(self.password_edit)
        form_layout.addWidget(QLabel("Role"))
        form_layout.addWidget(self.role_combo)
        card.add_layout(form_layout)

        button_layout = QHBoxLayout()
        save_btn = ModernButton("Create", "primary")
        cancel_btn = ModernButton("Cancel", "secondary")
        save_btn.clicked.connect(self.create_user)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)

        layout.addWidget(card)
        layout.addLayout(button_layout)

    def create_user(self):
        data = {
            "username": self.username_edit.text().strip(),
            "email": self.email_edit.text().strip(),
            "password": self.password_edit.text().strip(),
            "role": self.role_combo.currentText()
        }
        if not all(data.values()):
            self.show_error("All fields are required")
            return

        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            resp = requests.post(f"{SERVER_URL}/users", json=data, headers=headers, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                self.accept()
            else:
                msg = resp.json().get("detail", resp.text)
                self.show_error(f"Failed to create user:\n{msg}")
        except Exception as e:
            self.show_error(str(e))

    def show_error(self, message):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Error")
        msg.setText(message)
        msg.exec()
