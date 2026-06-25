import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from app import (
    ALLOWED_FORMATS,
    AUDIO_FORMATS,
    DEFAULT_DOWNLOADS_DIR,
    LEGAL_NOTICE,
    build_audio_command,
    build_output_template,
    build_video_command,
    get_ytdlp_command,
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

        self.download_button = ttk.Button(main_frame, text="Descargar", command=self.start_download)
        self.download_button.grid(row=8, column=0, sticky="w", pady=(4, 8))

        status_label = ttk.Label(main_frame, textvariable=self.status_var, wraplength=520)
        status_label.grid(row=9, column=0, columnspan=3, sticky="w")

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

        if get_ytdlp_command() is None:
            messagebox.showerror(
                "Falta yt-dlp",
                "No se encontro yt-dlp. Instala las dependencias con: python -m pip install -r requirements.txt",
            )
            return None

        if subprocess.run(["where", "ffmpeg"], capture_output=True, text=True).returncode != 0:
            messagebox.showerror(
                "Falta ffmpeg",
                "No se encontro ffmpeg. Instala ffmpeg y agregalo al PATH de Windows.",
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
        self.status_var.set("Descargando... espera un momento.")

        thread = threading.Thread(
            target=self.download_worker,
            args=(urls, media_format, output_dir),
            daemon=True,
        )
        thread.start()

    def download_worker(self, urls, media_format, output_dir):
        """Ejecuta yt-dlp sin congelar la ventana."""
        output_template = build_output_template(output_dir, None, len(urls))

        if media_format in AUDIO_FORMATS:
            command = build_audio_command(urls, output_template, media_format)
        else:
            command = build_video_command(urls, output_template, media_format)

        try:
            # Se pasa una lista de argumentos y no se usa shell=True.
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as error:
            self.root.after(
                0,
                self.finish_download,
                False,
                f"yt-dlp no pudo completar la descarga. Codigo de salida: {error.returncode}",
            )
            return

        self.root.after(0, self.finish_download, True, f"Descarga finalizada en: {output_dir}")

    def finish_download(self, success, message):
        """Actualiza la interfaz cuando termina la descarga."""
        self.download_button.config(state="normal")
        self.status_var.set(message)

        if success:
            messagebox.showinfo("Descarga completada", message)
        else:
            messagebox.showerror("Error de descarga", message)


def main():
    """Inicia la ventana principal de Tkinter."""
    root = tk.Tk()
    DownloaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
