from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox
)
from database import authenticate


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Вход")
        self.setFixedSize(320, 200)
        self.user = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Логин:"))
        self.login_edit = QLineEdit()
        self.login_edit.setText("admin")
        layout.addWidget(self.login_edit)

        layout.addWidget(QLabel("Пароль:"))
        self.pwd_edit = QLineEdit()
        self.pwd_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_edit.setText("admin")
        layout.addWidget(self.pwd_edit)

        btn = QPushButton("Войти")
        btn.clicked.connect(self.try_login)
        layout.addWidget(btn)

        hint = QLabel("По умолчанию: admin / admin")
        hint.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(hint)

    def try_login(self):
        u = self.login_edit.text().strip()
        p = self.pwd_edit.text()
        user = authenticate(u, p)
        if not user:
            QMessageBox.warning(self, "Ошибка", "Неверный логин или пароль")
            return
        self.user = user
        self.accept()