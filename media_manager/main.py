import sys
from PyQt5.QtWidgets import QApplication
from database import init_db
from ui_login import LoginDialog
from ui_main import MainWindow


def main():
    init_db()
    app = QApplication(sys.argv)

    login = LoginDialog()
    if login.exec() != LoginDialog.DialogCode.Accepted:
        return

    w = MainWindow(login.user)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()