import PyQt6.QtWidgets
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import os

from database import (
    add_folder, list_folders, add_media, query_media, stats,
    create_user, all_users
)
from scanner import scan_folder


class ScanWorker(QThread):
    progress = pyqtSignal(int)
    finished_scan = pyqtSignal(int)

    def __init__(self, folder_path, folder_id):
        super().__init__()
        self.folder_path = folder_path
        self.folder_id = folder_id

    def run(self):
        def on_file(meta):
            add_media(self.folder_id, meta["path"], meta["filename"],
                      meta["ext"], meta["category"], meta["size"], meta["mtime"])

        def on_progress(n):
            self.progress.emit(n)

        count = scan_folder(self.folder_path, on_file=on_file, on_progress=on_progress)
        self.finished_scan.emit(count)


class MainWindow(QMainWindow):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setWindowTitle(f"Медиатека — {user['username']} ({user['role']})")
        self.resize(1100, 700)
        self.scan_worker = None
        self.progress_dialog = None

        tabs = QTabWidget()
        tabs.addTab(self.build_library_tab(), "Библиотека")
        tabs.addTab(self.build_folders_tab(), "Папки")
        if user["role"] == "admin":
            tabs.addTab(self.build_admin_tab(), "Администрирование")
        self.setCentralWidget(tabs)

        self.refresh_media()
        self.refresh_folders()

    # ---------- Библиотека ----------
    def build_library_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        top = QHBoxLayout()
        self.cat_combo = QComboBox()
        self.cat_combo.addItems([
            "Все", "Музыка", "Видео", "Изображения",
            "Учебные записи", "Презентации", "Скринкасты", "Прочее"
        ])
        self.cat_combo.currentTextChanged.connect(self.refresh_media)
        top.addWidget(QLabel("Категория:"))
        top.addWidget(self.cat_combo)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по имени файла...")
        self.search_edit.textChanged.connect(self.refresh_media)
        top.addWidget(self.search_edit)

        btn_refresh = QPushButton("Обновить")
        btn_refresh.clicked.connect(self.refresh_media)
        top.addWidget(btn_refresh)

        layout.addLayout(top)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Имя", "Категория", "Размер, МБ", "Изменён", "Папка", "Путь"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self.stats_label = QLabel()
        layout.addWidget(self.stats_label)
        return w

    def refresh_media(self):
        rows = query_media(
            category=self.cat_combo.currentText(),
            search=self.search_edit.text().strip()
        )
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(r["filename"]))
            self.table.setItem(i, 1, QTableWidgetItem(r["category"]))
            self.table.setItem(i, 2, QTableWidgetItem(f"{r['size_bytes']/1024/1024:.2f}"))
            self.table.setItem(i, 3, QTableWidgetItem(r["modified_at"][:19]))
            self.table.setItem(i, 4, QTableWidgetItem(r.get("folder_path") or ""))
            self.table.setItem(i, 5, QTableWidgetItem(r["path"]))

        s = stats()
        total_files = sum(x["cnt"] for x in s)
        total_mb = sum((x["total"] or 0) for x in s) / 1024 / 1024
        self.stats_label.setText(
            f"Всего файлов: {total_files} | Объём: {total_mb:.1f} МБ | "
            + " | ".join(f"{x['category']}: {x['cnt']}" for x in s)
        )

    # ---------- Папки ----------
    def build_folders_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        top = QHBoxLayout()
        btn_add = QPushButton("Добавить папку…")
        btn_add.clicked.connect(self.add_folder_dialog)
        top.addWidget(btn_add)
        top.addStretch()
        layout.addLayout(top)

        self.folders_list = QListWidget()
        layout.addWidget(self.folders_list)
        return w

    def refresh_folders(self):
        self.folders_list.clear()
        for f in list_folders():
            self.folders_list.addItem(f["path"])

    def add_folder_dialog(self):
        path = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if not path:
            return
        if not os.path.isdir(path):
            QMessageBox.warning(self, "Ошибка", "Папка не найдена")
            return

        folder_id = add_folder(path, self.user["id"])
        if folder_id is None:
            for f in list_folders():
                if f["path"] == path:
                    folder_id = f["id"]
                    break
            if folder_id is None:
                QMessageBox.warning(self, "Ошибка", "Не удалось добавить папку")
                return

        self.refresh_folders()
        self.start_scan(path, folder_id)

    def start_scan(self, path, folder_id):
        if self.scan_worker is not None and self.scan_worker.isRunning():
            QMessageBox.information(self, "Подождите", "Сканирование уже идёт")
            return

        self.progress_dialog = QProgressDialog("Сканирование…", "Отмена", 0, 0, self)
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setAutoReset(False)
        self.progress_dialog.show()

        self.scan_worker = ScanWorker(path, folder_id)
        self.scan_worker.progress.connect(self._on_scan_progress)
        self.scan_worker.finished_scan.connect(self.on_scan_done)
        self.scan_worker.start()

    def _on_scan_progress(self, n):
        if self.progress_dialog is not None:
            self.progress_dialog.setLabelText(f"Проиндексировано файлов: {n}")

    def on_scan_done(self, count):
        if self.progress_dialog is not None:
            self.progress_dialog.close()
            self.progress_dialog = None
        QMessageBox.information(self, "Готово", f"Проиндексировано файлов: {count}")
        self.refresh_media()
        self.refresh_folders()

    def closeEvent(self, event):
        if self.scan_worker is not None and self.scan_worker.isRunning():
            self.scan_worker.wait(3000)
        event.accept()

    # ---------- Админ ----------
    def build_admin_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        form = QHBoxLayout()
        self.new_login = QLineEdit(); self.new_login.setPlaceholderText("Логин")
        self.new_pwd = QLineEdit(); self.new_pwd.setPlaceholderText("Пароль")
        self.new_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_role = QComboBox(); self.new_role.addItems(["user", "admin"])
        btn = QPushButton("Создать пользователя")
        btn.clicked.connect(self.create_user_clicked)

        form.addWidget(self.new_login)
        form.addWidget(self.new_pwd)
        form.addWidget(self.new_role)
        form.addWidget(btn)
        layout.addLayout(form)

        self.users_table = QTableWidget(0, 4)
        self.users_table.setHorizontalHeaderLabels(["ID", "Логин", "Роль", "Создан"])
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.users_table)

        self.refresh_users()
        return w

    def refresh_users(self):
        users = all_users()
        self.users_table.setRowCount(len(users))
        for i, u in enumerate(users):
            self.users_table.setItem(i, 0, QTableWidgetItem(str(u["id"])))
            self.users_table.setItem(i, 1, QTableWidgetItem(u["username"]))
            self.users_table.setItem(i, 2, QTableWidgetItem(u["role"]))
            self.users_table.setItem(i, 3, QTableWidgetItem(u["created_at"][:19]))

    def create_user_clicked(self):
        u = self.new_login.text().strip()
        p = self.new_pwd.text()
        r = self.new_role.currentText()
        if not u or not p:
            QMessageBox.warning(self, "Ошибка", "Заполните логин и пароль")
            return
        ok, msg = create_user(u, p, r)
        if ok:
            QMessageBox.information(self, "OK", "Пользователь создан")
            self.new_login.clear(); self.new_pwd.clear()
            self.refresh_users()
        else:
            QMessageBox.warning(self, "Ошибка", msg)