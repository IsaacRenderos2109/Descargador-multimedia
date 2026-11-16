import multiprocessing
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from .history import History
from .ui import MainWindow
from .workers import smoke_child


def smoke_test(app: QApplication) -> int:
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        window = MainWindow(
            History(base / "history.sqlite3"),
            QSettings(str(base / "settings.ini"), QSettings.Format.IniFormat),
        )
        window.show()
        app.processEvents()
        assert window.isVisible() and window.tabs.count() == 3
        context = multiprocessing.get_context("spawn")
        messages = context.Queue()
        child = context.Process(target=smoke_child, args=(messages,))
        child.start()
        try:
            assert messages.get(timeout=20) is True
            child.join(timeout=5)
            assert child.exitcode == 0
        finally:
            if child.is_alive():
                child.terminate()
                child.join(timeout=5)
            messages.close()
        QTimer.singleShot(100, window.close)
        QTimer.singleShot(200, app.quit)
        return app.exec()


def main() -> int:
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    app.setApplicationName("Video Downloader")
    app.setOrganizationName("VideoDownloader")
    app.setApplicationVersion("1.0.0")
    app.setStyle("Fusion")
    if "--smoke-test" in sys.argv:
        return smoke_test(app)
    directory = Path(
        QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
    )
    try:
        history = History(directory / "history.sqlite3")
    except Exception as error:
        QMessageBox.critical(
            None, "Video Downloader", f"No se pudo abrir el historial local: {error}"
        )
        return 1
    window = MainWindow(history)
    screen = app.primaryScreen()
    if screen is not None:
        available = screen.availableGeometry()
        window.resize(min(1180, available.width() - 60), min(850, available.height() - 60))
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
