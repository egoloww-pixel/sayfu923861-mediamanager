import os
from datetime import datetime

CATEGORIES = {
    "Музыка":         {".mp3", ".flac", ".wav", ".aac", ".ogg", ".m4a", ".wma"},
    "Видео":          {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"},
    "Изображения":    {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".svg"},
    "Учебные записи": {".pdf", ".doc", ".docx", ".txt", ".rtf", ".md", ".epub"},
    "Презентации":    {".ppt", ".pptx", ".odp", ".key"},
    "Скринкасты":     {".scr", ".cast"},
}


def classify(ext: str) -> str:
    ext = ext.lower()
    for cat, exts in CATEGORIES.items():
        if ext in exts:
            return cat
    return "Прочее"


def scan_folder(folder_path: str, on_file=None, on_progress=None):
    if not os.path.isdir(folder_path):
        return 0
    count = 0
    for root, _, files in os.walk(folder_path):
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            cat = classify(ext)
            if cat == "Прочее":
                continue
            full = os.path.join(root, fname)
            try:
                st = os.stat(full)
            except OSError:
                continue
            meta = {
                "path": full,
                "filename": fname,
                "ext": ext,
                "category": cat,
                "size": st.st_size,
                "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(),
            }
            count += 1
            if on_file:
                on_file(meta)
            if on_progress and count % 100 == 0:
                on_progress(count)
    return count