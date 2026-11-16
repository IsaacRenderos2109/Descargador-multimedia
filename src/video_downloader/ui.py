from pathlib import Path
from urllib.parse import urlsplit

from PySide6.QtCore import QSettings, Qt, QTimer, QUrl
from PySide6.QtGui import QCloseEvent, QDesktopServices, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .history import History
from .models import DownloadOptions, Job, Media, Progress, Status
from .queue import DownloadQueue
from .validation import ValidationError, parse_urls
from .workers import DiagnosticsWorker, InspectWorker

STYLE = """
QWidget { background: #101827; color: #e5edf8; font-family: 'Segoe UI'; font-size: 13px; }
QMainWindow, QTabWidget::pane { border: none; }
QLabel#heading { font-size: 29px; font-weight: 700; }
QLabel#muted { color: #9eb0c8; }
QPushButton { background: #26364f; border: 1px solid #3c506d; padding: 9px 15px;
              border-radius: 7px; }
QPushButton:hover { background: #344c6e; }
QPushButton:disabled { color: #72829a; background: #1a2537; }
QPushButton#primary { background: #2563eb; border-color: #4586ff; font-weight: 600; }
QPushButton#primary:hover { background: #3578fa; }
QLineEdit, QPlainTextEdit, QListWidget, QTableWidget, QTextEdit, QComboBox {
 background: #172337; border: 1px solid #334760; border-radius: 6px; padding: 5px;
 selection-background-color: #265ac0; }
QHeaderView::section { background: #21314a; color: #c8d6ea; border: none; padding: 8px; }
QTabBar::tab { padding: 11px 20px; background: #172337; }
QTabBar::tab:selected { background: #284576; }
QProgressBar { border: 1px solid #334760; border-radius: 5px; text-align: center; }
QProgressBar::chunk { background: #2d78f4; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #8496af;
                      border-radius: 3px; background: #172337; }
QCheckBox::indicator:checked { background: #3b82f6; border-color: #b3d2ff; }
QToolTip { background: #26364f; color: white; border: 1px solid #6b83a4; }
"""


def size_text(value: float | int | None) -> str:
    if value is None:
        return "—"
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024 or unit == "GiB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return "—"


def duration_text(value: float | None) -> str:
    if value is None:
        return "—"
    seconds = int(value)
    hours, minutes = divmod(seconds // 60, 60)
    return f"{hours:02}:{minutes:02}:{seconds % 60:02}"


class MainWindow(QMainWindow):
    def __init__(self, history: History, settings: QSettings | None = None) -> None:
        super().__init__()
        self.history = history
        self.settings = settings or QSettings("VideoDownloader", "VideoDownloader")
        self.queue = DownloadQueue(history)
        self.inspector: InspectWorker | None = None
        self.tools_worker: DiagnosticsWorker | None = None
        self.closing = False
        self.media: list[Media] = []
        self.network = QNetworkAccessManager(self)
        self.thumbnail_reply: QNetworkReply | None = None
        self.thumbnail_generation = 0
        self.setWindowTitle("Video Downloader")
        self.resize(1180, 850)
        self.setMinimumSize(780, 640)
        self.setStyleSheet(STYLE)
        body = QWidget()
        self.setCentralWidget(body)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(24, 20, 24, 20)
        title = QLabel("Video Downloader")
        title.setObjectName("heading")
        layout.addWidget(title)
        subtitle = QLabel("Tu biblioteca, a tu manera · Descargas de contenido autorizado")
        subtitle.setObjectName("muted")
        layout.addWidget(subtitle)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self._download_tab()
        self._queue_tab()
        self._history_tab()
        self.statusBar().showMessage("Listo · Pega enlaces de YouTube para comenzar")
        self.queue.changed.connect(self.refresh_job)
        self.queue.progressed.connect(self.update_progress)
        self.queue.persistence_error.connect(self.show_error)
        self.queue.idle.connect(self._try_close)
        self.refresh_history()

    def _download_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("ENLACES · Un enlace por línea, incluyendo listas públicas"))
        self.urls = QPlainTextEdit()
        self.urls.setObjectName("urlInput")
        self.urls.setPlaceholderText(
            "https://www.youtube.com/watch?v=…\nhttps://www.youtube.com/playlist?list=…"
        )
        self.urls.setMaximumHeight(100)
        self.urls.setAccessibleName("Enlaces de YouTube")
        layout.addWidget(self.urls)
        buttons = QHBoxLayout()
        self.inspect_button = QPushButton("Analizar enlaces")
        self.inspect_button.setObjectName("primary")
        self.inspect_button.clicked.connect(self.inspect_urls)
        buttons.addWidget(self.inspect_button)
        self.cancel_inspect = QPushButton("Cancelar análisis")
        self.cancel_inspect.setEnabled(False)
        self.cancel_inspect.clicked.connect(self.cancel_analysis)
        buttons.addWidget(self.cancel_inspect)
        buttons.addStretch()
        self.tools_button = QPushButton("Comprobar herramientas")
        self.tools_button.clicked.connect(self.check_tools)
        buttons.addWidget(self.tools_button)
        layout.addLayout(buttons)
        self.analysis_status = QLabel(
            "Selecciona los videos después del análisis. Límite: 200 por lista."
        )
        self.analysis_status.setWordWrap(True)
        layout.addWidget(self.analysis_status)
        splitter = QSplitter()
        self.media_list = QListWidget()
        self.media_list.setAccessibleName("Videos disponibles; marca los que deseas descargar")
        self.media_list.currentRowChanged.connect(self.show_media)
        splitter.addWidget(self.media_list)
        preview = QWidget()
        preview_layout = QVBoxLayout(preview)
        self.thumbnail = QLabel("Vista previa")
        self.thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail.setMinimumHeight(90)
        self.thumbnail.setMaximumHeight(150)
        preview_layout.addWidget(self.thumbnail)
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setAcceptRichText(False)
        preview_layout.addWidget(self.details)
        splitter.addWidget(preview)
        splitter.setSizes([600, 400])
        layout.addWidget(splitter, 1)
        row = QHBoxLayout()
        all_button = QPushButton("Marcar todos")
        all_button.clicked.connect(lambda: self.mark_media(True))
        none_button = QPushButton("Desmarcar todos")
        none_button.clicked.connect(lambda: self.mark_media(False))
        row.addWidget(all_button)
        row.addWidget(none_button)
        row.addStretch()
        layout.addLayout(row)
        form = QFormLayout()
        mode_row = QHBoxLayout()
        self.mode = QComboBox()
        self.mode.addItems(["Video MP4", "Audio MP3 · 192 kbps"])
        self.resolution = QComboBox()
        for value in (360, 480, 720, 1080, 1440, 2160):
            self.resolution.addItem("4K · 2160p" if value == 2160 else f"{value}p", value)
        self.resolution.setCurrentIndex(3)
        self.mode.currentIndexChanged.connect(lambda index: self.resolution.setEnabled(index == 0))
        mode_row.addWidget(self.mode)
        mode_row.addWidget(self.resolution)
        form.addRow("Formato y resolución", mode_row)
        folder_row = QHBoxLayout()
        default = str(Path.home() / "Downloads" / "Video Downloader")
        self.destination = QLineEdit(str(self.settings.value("destination", default)))
        self.destination.setAccessibleName("Carpeta de destino")
        folder_row.addWidget(self.destination)
        browse = QPushButton("Elegir carpeta…")
        browse.clicked.connect(self.browse)
        folder_row.addWidget(browse)
        form.addRow("Destino", folder_row)
        layout.addLayout(form)
        self.consent = QCheckBox(
            "Confirmo que tengo autorización para descargar el contenido seleccionado."
        )
        layout.addWidget(self.consent)
        notice = QLabel(
            "Solo contenido público autorizado. No se eluden DRM ni restricciones de acceso."
        )
        notice.setWordWrap(True)
        notice.setObjectName("muted")
        layout.addWidget(notice)
        self.enqueue_button = QPushButton("Añadir selección a la cola")
        self.enqueue_button.setObjectName("primary")
        self.enqueue_button.clicked.connect(self.enqueue)
        layout.addWidget(self.enqueue_button)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(page)
        self.tabs.addTab(scroll, "Descargar")

    def _queue_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.queue_table = self.make_table(["Título", "Formato", "Estado", "Progreso", "Detalle"])
        layout.addWidget(self.queue_table)
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        self.progress_label = QLabel("Sin descargas activas")
        self.progress_label.setWordWrap(True)
        layout.addWidget(self.progress_label)
        row = QHBoxLayout()
        cancel = QPushButton("Cancelar seleccionada")
        cancel.clicked.connect(self.cancel_selected)
        row.addWidget(cancel)
        cancel_all = QPushButton("Cancelar todas")
        cancel_all.clicked.connect(self.queue.cancel_all)
        row.addWidget(cancel_all)
        open_folder = QPushButton("Abrir carpeta del archivo")
        open_folder.clicked.connect(self.open_selected)
        row.addWidget(open_folder)
        row.addStretch()
        layout.addLayout(row)
        self.tabs.addTab(page, "Cola")

    def _history_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(
            QLabel("Últimas 1.000 operaciones · El historial permanece en este equipo")
        )
        self.history_table = self.make_table(
            ["Fecha UTC", "Título", "Formato", "Estado", "Archivo / detalle"]
        )
        layout.addWidget(self.history_table)
        row = QHBoxLayout()
        refresh = QPushButton("Actualizar")
        refresh.clicked.connect(self.refresh_history)
        row.addWidget(refresh)
        export = QPushButton("Exportar historial CSV…")
        export.clicked.connect(self.export_history)
        row.addWidget(export)
        row.addStretch()
        layout.addLayout(row)
        self.tabs.addTab(page, "Historial")

    @staticmethod
    def make_table(headers: list[str]) -> QTableWidget:
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().hide()
        table.setColumnWidth(0, 210)
        return table

    def show_error(self, message: str) -> None:
        QMessageBox.warning(self, "Video Downloader", message)

    def inspect_urls(self) -> None:
        try:
            urls = parse_urls(self.urls.toPlainText())
        except ValidationError as error:
            self.show_error(str(error))
            return
        self.media = []
        self.media_list.clear()
        self.details.clear()
        self.thumbnail.clear()
        self.inspect_button.setEnabled(False)
        self.cancel_inspect.setEnabled(True)
        self.analysis_status.setText("Analizando metadatos y formatos…")
        worker = InspectWorker(urls)
        self.inspector = worker
        worker.found.connect(self.received_media)
        worker.failed.connect(self.analysis_failed)
        worker.cancelled.connect(lambda: self.analysis_status.setText("Análisis cancelado."))
        worker.finished.connect(self.analysis_finished)
        worker.start()

    def analysis_failed(self, message: str) -> None:
        self.analysis_status.setText(message)

    def analysis_finished(self) -> None:
        if self.inspector:
            self.inspector.deleteLater()
        self.inspector = None
        self.inspect_button.setEnabled(True)
        self.cancel_inspect.setEnabled(False)
        self._try_close()

    def cancel_analysis(self) -> None:
        if self.inspector:
            self.inspector.cancel()
            self.analysis_status.setText("Cancelando análisis; esperando respuesta de la red…")

    def received_media(self, media: list[Media]) -> None:
        self.media = media
        for item in media:
            resolutions = (
                ", ".join(f"{height}p" for height in item.resolutions)
                or "Solo audio / otros tamaños"
            )
            row = QListWidgetItem(f"{item.title}\n{duration_text(item.duration)} · {resolutions}")
            row.setToolTip(item.url)
            row.setCheckState(Qt.CheckState.Checked)
            self.media_list.addItem(row)
        self.analysis_status.setText(
            f"{len(media)} videos encontrados. Comprueba formatos antes de añadirlos."
        )
        if media:
            self.media_list.setCurrentRow(0)

    def mark_media(self, checked: bool) -> None:
        for row in range(self.media_list.count()):
            self.media_list.item(row).setCheckState(
                Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
            )

    def show_media(self, row: int) -> None:
        self.thumbnail_generation += 1
        if self.thumbnail_reply:
            self.thumbnail_reply.abort()
            self.thumbnail_reply = None
        self.thumbnail.setText("Sin miniatura")
        if row < 0 or row >= len(self.media):
            return
        media = self.media[row]
        self.details.setPlainText(
            f"{media.title}\nDuración: {duration_text(media.duration)}\n{media.url}\n\n"
            + "FORMATOS DISPONIBLES\n"
            + "\n".join(media.formats)
        )
        if media.thumbnail:
            parsed = urlsplit(media.thumbnail)
            if parsed.scheme == "https" and (parsed.hostname or "").endswith(".ytimg.com"):
                request = QNetworkRequest(QUrl(media.thumbnail))
                request.setTransferTimeout(10000)
                request.setAttribute(
                    QNetworkRequest.Attribute.RedirectPolicyAttribute,
                    QNetworkRequest.RedirectPolicy.ManualRedirectPolicy,
                )
                reply = self.network.get(request)
                self.thumbnail_reply = reply
                generation = self.thumbnail_generation
                reply.downloadProgress.connect(
                    lambda received, total: reply.abort() if received > 2_000_000 else None
                )
                reply.finished.connect(lambda: self.thumbnail_ready(reply, generation))

    def thumbnail_ready(self, reply: QNetworkReply, generation: int) -> None:
        if (
            generation == self.thumbnail_generation
            and reply.error() == QNetworkReply.NetworkError.NoError
        ):
            pixmap = QPixmap()
            if pixmap.loadFromData(reply.readAll()) and not pixmap.isNull():
                self.thumbnail.setPixmap(
                    pixmap.scaled(
                        300,
                        150,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
        if self.thumbnail_reply is reply:
            self.thumbnail_reply = None
        reply.deleteLater()

    def browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Carpeta de destino", self.destination.text()
        )
        if folder:
            self.destination.setText(folder)

    def enqueue(self) -> None:
        if not self.consent.isChecked():
            self.show_error("Confirma que tienes autorización antes de descargar.")
            return
        selected = [
            item
            for index, item in enumerate(self.media)
            if self.media_list.item(index).checkState() == Qt.CheckState.Checked
        ]
        if not selected:
            self.show_error("Analiza los enlaces y marca al menos un video.")
            return
        if not self.destination.text().strip():
            self.show_error("Selecciona una carpeta de destino.")
            return
        options = DownloadOptions(
            Path(self.destination.text()).expanduser().absolute(),
            self.mode.currentIndex() == 1,
            int(self.resolution.currentData()),
        )
        unavailable = [
            item.title
            for item in selected
            if not options.audio_only and options.resolution not in item.resolutions
        ]
        if unavailable:
            self.show_error(
                "Resolución no disponible en: "
                + ", ".join(unavailable[:5])
                + ". Selecciona otra resolución o desmarca esos videos."
            )
            return
        self.settings.setValue("destination", str(options.destination))
        self.queue.add([Job(media, options) for media in selected])
        self.tabs.setCurrentIndex(1)

    def queue_cell(self, row: int, column: int) -> QTableWidgetItem:
        item = self.queue_table.item(row, column)
        assert item is not None, "Queue table must contain initialized cells"
        return item

    def refresh_job(self, job: Job) -> None:
        row = next(
            (
                index
                for index in range(self.queue_table.rowCount())
                if self.queue_cell(index, 0).data(Qt.ItemDataRole.UserRole) == job.id
            ),
            -1,
        )
        if row < 0:
            row = self.queue_table.rowCount()
            self.queue_table.insertRow(row)
            for column in range(5):
                self.queue_table.setItem(row, column, QTableWidgetItem())
        values = [
            job.media.title,
            "MP3" if job.options.audio_only else f"MP4 {job.options.resolution}p",
            str(job.status),
            "100%" if job.status == Status.COMPLETED else "—",
            job.message,
        ]
        for column, value in enumerate(values):
            self.queue_cell(row, column).setText(value)
            self.queue_cell(row, column).setToolTip(job.path or job.message)
        self.queue_cell(row, 0).setData(Qt.ItemDataRole.UserRole, job.id)
        if job.status not in {Status.QUEUED, Status.RUNNING}:
            self.refresh_history()
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100 if job.status == Status.COMPLETED else 0)
            self.progress_label.setText(f"{job.status}: {job.media.title} · {job.message}")

    def update_progress(self, job_id: str, progress: Progress) -> None:
        if progress.percent is None or progress.phase != "Descargando":
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(int(progress.percent))
        summary = (
            f"{progress.phase} · {size_text(progress.downloaded)} / {size_text(progress.total)}"
            f" · {size_text(progress.speed)}/s · Restante {duration_text(progress.eta)}"
        )
        self.progress_label.setText(summary)
        for row in range(self.queue_table.rowCount()):
            if self.queue_cell(row, 0).data(Qt.ItemDataRole.UserRole) == job_id:
                self.queue_cell(row, 3).setText(
                    f"{progress.percent:.1f}%" if progress.percent is not None else "…"
                )
                self.queue_cell(row, 4).setText(summary)

    def cancel_selected(self) -> None:
        row = self.queue_table.currentRow()
        if row >= 0:
            self.queue.cancel(self.queue_cell(row, 0).data(Qt.ItemDataRole.UserRole))

    def open_selected(self) -> None:
        row = self.queue_table.currentRow()
        if row >= 0:
            job_id = self.queue_cell(row, 0).data(Qt.ItemDataRole.UserRole)
            job = next(job for job in self.queue.jobs if job.id == job_id)
            if job.path:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(job.path).parent)))

    def refresh_history(self) -> None:
        try:
            rows = self.history.rows()
        except Exception as error:
            self.statusBar().showMessage(f"No se puede leer el historial: {error}")
            return
        self.history_table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            for column, key in enumerate(("finished_at", "title", "format", "status", "path")):
                value = row[key] or row["error"]
                cell = QTableWidgetItem(value)
                cell.setToolTip(value)
                self.history_table.setItem(index, column, cell)

    def export_history(self) -> None:
        name, _ = QFileDialog.getSaveFileName(
            self, "Exportar historial", "historial.csv", "CSV (*.csv)"
        )
        if name:
            try:
                self.history.export_csv(Path(name))
            except Exception as error:
                self.show_error(str(error))

    def check_tools(self) -> None:
        if self.tools_worker is not None:
            return
        self.tools_button.setEnabled(False)
        worker = DiagnosticsWorker()
        self.tools_worker = worker
        worker.ready.connect(lambda result: QMessageBox.information(self, "Herramientas", result))
        worker.failed.connect(self.show_error)
        worker.finished.connect(self.tools_finished)
        worker.start()

    def tools_finished(self) -> None:
        if self.tools_worker:
            self.tools_worker.deleteLater()
        self.tools_worker = None
        self.tools_button.setEnabled(True)
        self._try_close()

    def _try_close(self) -> None:
        if (
            self.closing
            and not self.queue.busy
            and self.inspector is None
            and self.tools_worker is None
        ):
            QTimer.singleShot(0, self.close)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.queue.busy or self.inspector is not None or self.tools_worker is not None:
            if not self.closing:
                answer = QMessageBox.question(
                    self, "Cerrar Video Downloader", "¿Cancelar las operaciones y cerrar?"
                )
                if answer != QMessageBox.StandardButton.Yes:
                    event.ignore()
                    return
            self.closing = True
            self.queue.cancel_all()
            self.cancel_analysis()
            self.statusBar().showMessage("Cerrando de forma segura…")
            event.ignore()
        else:
            if self.thumbnail_reply:
                self.thumbnail_reply.abort()
            event.accept()
