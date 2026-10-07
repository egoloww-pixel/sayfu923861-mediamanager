import sqlite3
import hashlib
from datetime import datetime

DB_PATH = "media.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(pwd: str) -> str:
    return hashlib.sha256(pwd.encode("utf-8")).hexdigest()


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user','admin')),
            created_at TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            added_by INTEGER,
            added_at TEXT NOT NULL,
            FOREIGN KEY(added_by) REFERENCES users(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_id INTEGER,
            path TEXT UNIQUE NOT NULL,
            filename TEXT NOT NULL,
            ext TEXT NOT NULL,
            category TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            modified_at TEXT NOT NULL,
            indexed_at TEXT NOT NULL,
            FOREIGN KEY(folder_id) REFERENCES folders(id) ON DELETE CASCADE
        )
    """)

    c.execute("CREATE INDEX IF NOT EXISTS idx_media_cat ON media(category)")
    conn.commit()

    c.execute("SELECT COUNT(*) FROM users WHERE role='admin'")
    if c.fetchone()[0] == 0:
        c.execute(
            "INSERT INTO users (username, password_hash, role, created_at) VALUES (?,?,?,?)",
            ("admin", hash_password("admin"), "admin", datetime.now().isoformat())
        )
        conn.commit()

    conn.close()


def authenticate(username: str, password: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT id, username, role FROM users WHERE username=? AND password_hash=?",
        (username, hash_password(password))
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_user(username: str, password: str, role: str = "user"):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, role, created_at) VALUES (?,?,?,?)",
            (username, hash_password(password), role, datetime.now().isoformat())
        )
        conn.commit()
        return True, "OK"
    except sqlite3.IntegrityError:
        return False, "Пользователь уже существует"
    finally:
        conn.close()


def add_folder(path: str, user_id: int):
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO folders (path, added_by, added_at) VALUES (?,?,?)",
            (path, user_id, datetime.now().isoformat())
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def list_folders():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM folders ORDER BY added_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_media(folder_id, path, filename, ext, category, size, mtime):
    conn = get_conn()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO media
            (folder_id, path, filename, ext, category, size_bytes, modified_at, indexed_at)
            VALUES (?,?,?,?,?,?,?,?)
        """, (folder_id, path, filename, ext, category, size, mtime, datetime.now().isoformat()))
        conn.commit()
    finally:
        conn.close()


def query_media(category=None, search=None, limit=1000):
    conn = get_conn()
    sql = "SELECT m.*, f.path AS folder_path FROM media m LEFT JOIN folders f ON m.folder_id=f.id WHERE 1=1"
    params = []
    if category and category != "Все":
        sql += " AND m.category=?"
        params.append(category)
    if search:
        sql += " AND m.filename LIKE ?"
        params.append(f"%{search}%")
    sql += " ORDER BY m.modified_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def stats():
    conn = get_conn()
    rows = conn.execute(
        "SELECT category, COUNT(*) AS cnt, SUM(size_bytes) AS total FROM media GROUP BY category"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def all_users():
    conn = get_conn()
    rows = conn.execute("SELECT id, username, role, created_at FROM users").fetchall()
    conn.close()
    return [dict(r) for r in rows]