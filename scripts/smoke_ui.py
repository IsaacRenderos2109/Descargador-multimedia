"""Offline GUI boot check, also runnable with the frozen executable's --smoke-test."""

import tempfile
from pathlib import Path

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication

from video_downloader.history import History
from video_downloader.ui import MainWindow

app = QApplication([])
with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    window = MainWindow(
        History(base / "history.sqlite3"),
        QSettings(str(base / "settings.ini"), QSettings.Format.IniFormat),
    )
    window.show()
    app.processEvents()
    assert window.isVisible()
    assert window.tabs.count() == 3
    QTimer.singleShot(100, window.close)
    QTimer.singleShot(200, app.quit)
    assert app.exec() == 0
print("GUI startup OK (offline)")
