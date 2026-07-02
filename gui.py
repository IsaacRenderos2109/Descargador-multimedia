import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

from app import (
    ALLOWED_FORMATS,
    AUDIO_FORMATS,
    DEFAULT_DOWNLOADS_DIR,
    LEGAL_NOTICE,
    build_output_template,
    check_ffmpeg_installed,
    get_ffmpeg_location,
    normalize_urls,
)


class DownloaderApp:
    """Interfaz grafica sencilla para descargar audio o video."""

    def __init__(self, root):
        self.root = root
        self.root.title("Descargador Multimedia")
        self.root.resizable(False, False)

        self.format_var = tk.StringVar(value="mp3")
        self.folder_var = tk.StringVar(value=str(DEFAULT_DOWNLOADS_DIR))
        self.status_var = tk.StringVar(value="Listo para descargar.")
        self.percent_var = tk.StringVar(value="0.0%")
        self.progress_is_indeterminate = False

        self.create_widgets()

    def create_widgets(self):
        """Crea los campos, botones y textos de la ventana."""
        main_frame = ttk.Frame(self.root, padding=16)
        main_frame.grid(row=0, column=0, sticky="nsew")

        title = ttk.Label(main_frame, text="Descargador Multimedia", font=("Segoe UI", 14, "bold"))
        title.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

        notice = ttk.Label(
            main_frame,
            text=LEGAL_NOTICE,
            wraplength=520,
            foreground="#444444",
            justify="left",
        )
        notice.grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 14))

        ttk.Label(main_frame, text="URLs, una por linea:").grid(row=2, column=0, sticky="w")
        self.urls_text = tk.Text(main_frame, width=62, height=6, wrap="word")
        self.urls_text.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(4, 10))
        self.urls_text.focus()

        ttk.Label(main_frame, text="Formato:").grid(row=4, column=0, sticky="w")
        format_combo = ttk.Combobox(
            main_frame,
            textvariable=self.format_var,
            values=sorted(ALLOWED_FORMATS),
            state="readonly",
            width=18,
        )
        format_combo.grid(row=5, column=0, sticky="w", pady=(4, 10))

        ttk.Label(main_frame, text="Carpeta de salida:").grid(row=6, column=0, sticky="w")
        folder_entry = ttk.Entry(main_frame, textvariable=self.folder_var, width=50)
        folder_entry.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(4, 10))

        browse_button = ttk.Button(main_frame, text="Examinar", command=self.choose_folder)
        browse_button.grid(row=7, column=2, padx=(8, 0), pady=(4, 10))

        self.progress_bar = ttk.Progressbar(
            main_frame,
            orient="horizontal",
            mode="determinate",
            maximum=100,
            length=420,
        )
        self.progress_bar.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(4, 4))

        percent_label = ttk.Label(main_frame, textvariable=self.percent_var, width=18)
        percent_label.grid(row=8, column=2, sticky="e", padx=(8, 0), pady=(4, 4))

        self.download_button = ttk.Button(main_frame, text="Descargar", command=self.start_download)
        self.download_button.grid(row=9, column=0, sticky="w", pady=(8, 8))

        status_label = ttk.Label(main_frame, textvariable=self.status_var, wraplength=520)
        status_label.grid(row=10, column=0, columnspan=3, sticky="w")

    def choose_folder(self):
        """Abre un selector para elegir donde guardar la descarga."""
        folder = filedialog.askdirectory(initialdir=self.folder_var.get())

        if folder:
            self.folder_var.set(folder)

    def validate_inputs(self):
        """Valida los datos antes de intentar descargar."""
        raw_urls = self.urls_text.get("1.0", "end").splitlines()
        urls = normalize_urls(raw_urls)
        media_format = self.format_var.get().strip().lower()
        output_dir = Path(self.folder_var.get().strip()).expanduser().resolve()

        if not urls:
            messagebox.showerror("Faltan URLs", "Pega al menos un enlace autorizado.")
            return None

        if media_format not in ALLOWED_FORMATS:
            messagebox.showerror("Formato invalido", "Elige un formato permitido.")
            return None

        if yt_dlp is None:
            messagebox.showerror(
                "Falta yt-dlp",
                "No se encontro yt-dlp. Ejecuta instalar_dependencias.bat o usa: python -m pip install -r requirements.txt",
            )
            return None

        if not check_ffmpeg_installed():
            messagebox.showerror(
                "Falta FFmpeg",
                "No se encontro FFmpeg. Ejecuta instalar_dependencias.bat o instala FFmpeg manualmente.",
            )
            return None

        return urls, media_format, output_dir

    def start_download(self):
        """Confirma la accion y lanza la descarga en un hilo separado."""
        values = self.validate_inputs()

        if values is None:
            return

        urls, media_format, output_dir = values
        urls_preview = "\n".join(f"{index}. {url}" for index, url in enumerate(urls, start=1))
        confirmed = messagebox.askyesno(
            "Confirmar descarga",
            f"Enlaces:\n{urls_preview}\n\nFormato: {media_format}\nCarpeta: {output_dir}\n\nDeseas iniciar la descarga?",
        )

        if not confirmed:
            self.status_var.set("Descarga cancelada.")
            return

        self.download_button.config(state="disabled")
        self.set_determinate_progress(0)
        self.status_var.set("Preparando descarga...")

        thread = threading.Thread(
            target=self.download_worker,
            args=(urls, media_format, output_dir),
            daemon=True,
        )
        thread.start()

    def build_ydl_options(self, media_format, output_dir, url_count):
        """Construye las opciones para usar la API de yt-dlp."""
        output_template = build_output_template(output_dir, None, url_count)
        options = {
            "outtmpl": output_template,
            "noplaylist": True,
            "progress_hooks": [self.progress_hook],
            "postprocessor_hooks": [self.postprocessor_hook],
        }

        ffmpeg_location = get_ffmpeg_location()
        if ffmpeg_location is not None:
            options["ffmpeg_location"] = ffmpeg_location

        if media_format in AUDIO_FORMATS:
            options["format"] = "bestaudio/best"
            options["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": media_format,
                    "preferredquality": "192",
                }
            ]
        else:
            options["format"] = "bestvideo+bestaudio/best"
            options["merge_output_format"] = media_format

        return options

    def progress_hook(self, data):
        """Recibe el progreso real de yt-dlp desde el hilo secundario."""
        status = data.get("status")

        if status == "downloading":
            downloaded = data.get("downloaded_bytes") or 0
            total = data.get("total_bytes") or data.get("total_bytes_estimate")

            if total:
                percent = min((downloaded / total) * 100, 100)
                self.root.after(0, self.set_determinate_progress, percent)
                self.root.after(0, self.status_var.set, "Descargando...")
            else:
                self.root.after(0, self.set_indeterminate_progress, "Calculando progreso...")

        elif status == "finished":
            self.root.after(0, self.set_determinate_progress, 100)

    def postprocessor_hook(self, data):
        """Actualiza el estado durante conversiones o uniones con ffmpeg."""
        status = data.get("status")

        if status == "started":
            self.root.after(0, self.status_var.set, "Convirtiendo archivo...")
        elif status == "finished":
            self.root.after(0, self.set_determinate_progress, 100)

    def download_worker(self, urls, media_format, output_dir):
        """Ejecuta yt-dlp sin congelar la ventana."""
        try:
            options = self.build_ydl_options(media_format, output_dir, len(urls))
            self.root.after(0, self.status_var.set, "Preparando descarga...")

            with yt_dlp.YoutubeDL(options) as ydl:
                ydl.download(urls)

            self.root.after(0, self.finish_download, True, f"Descarga finalizada en: {output_dir}")
        except yt_dlp.utils.DownloadError as error:
            self.root.after(
                0,
                self.finish_download,
                False,
                f"Error en la descarga.\n\nDetalle real de yt-dlp:\n{error}",
            )
        except Exception as error:
            self.root.after(
                0,
                self.finish_download,
                False,
                f"Error en la descarga.\n\nDetalle:\n{error}",
            )

    def set_determinate_progress(self, percent):
        """Muestra una barra con porcentaje conocido."""
        if self.progress_is_indeterminate:
            self.progress_bar.stop()
            self.progress_bar.config(mode="determinate")
            self.progress_is_indeterminate = False

        percent = max(0, min(float(percent), 100))
        self.progress_bar["value"] = percent
        self.percent_var.set(f"{percent:.1f}%")

    def set_indeterminate_progress(self, message):
        """Muestra una barra animada cuando yt-dlp no sabe el tamano total."""
        if not self.progress_is_indeterminate:
            self.progress_bar.config(mode="indeterminate")
            self.progress_bar.start(10)
            self.progress_is_indeterminate = True

        self.percent_var.set("Calculando progreso...")
        self.status_var.set(message)

    def finish_download(self, success, message):
        """Actualiza la interfaz cuando termina la descarga."""
        if self.progress_is_indeterminate:
            self.progress_bar.stop()
            self.progress_bar.config(mode="determinate")
            self.progress_is_indeterminate = False

        self.download_button.config(state="normal")
        self.status_var.set("Descarga finalizada." if success else "Error en la descarga.")

        if success:
            self.set_determinate_progress(100)
            messagebox.showinfo("Descarga completada", message)
        else:
            self.set_determinate_progress(0)
            messagebox.showerror("Error de descarga", message)


def main():
    """Inicia la ventana principal de Tkinter."""
    root = tk.Tk()
    DownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
