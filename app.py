import argparse
import shutil
import subprocess
import sys
from pathlib import Path


# Formatos permitidos por el programa.
AUDIO_FORMATS = {"mp3", "m4a", "wav", "flac", "opus"}
VIDEO_FORMATS = {"mp4", "webm", "mkv"}
ALLOWED_FORMATS = AUDIO_FORMATS | VIDEO_FORMATS

# Carpeta predeterminada donde se guardaran las descargas.
DEFAULT_DOWNLOADS_DIR = Path(__file__).resolve().parent / "descargas"

LEGAL_NOTICE = """
Aviso de uso responsable:
Usa esta herramienta solo con contenido propio, con permiso del autor,
Creative Commons o contenido autorizado para descarga. Este programa no debe
usarse para saltarse DRM, contenido privado, inicios de sesion, restricciones
de pago ni protecciones tecnicas.
""".strip()


def check_tool_installed(tool_name):
    """Verifica si un programa externo esta disponible en el sistema."""
    if shutil.which(tool_name) is None:
        print(
            f"Error: no se encontro '{tool_name}'. Instala {tool_name} y vuelve a intentarlo.",
            file=sys.stderr,
        )
        return False

    return True


def get_ytdlp_command():
    """Devuelve el comando disponible para ejecutar yt-dlp."""
    if shutil.which("yt-dlp") is not None:
        return ["yt-dlp"]

    # En Windows a veces yt-dlp esta instalado como modulo, pero el comando
    # yt-dlp no queda disponible en el PATH. Este fallback usa el mismo Python
    # que esta ejecutando la aplicacion.
    result = subprocess.run(
        [sys.executable, "-m", "yt_dlp", "--version"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        return [sys.executable, "-m", "yt_dlp"]

    return None


def check_ytdlp_installed():
    """Verifica si yt-dlp se puede ejecutar como comando o como modulo."""
    if get_ytdlp_command() is not None:
        return True

    print(
        "Error: no se encontro yt-dlp. Instala las dependencias con: "
        "python -m pip install -r requirements.txt",
        file=sys.stderr,
    )
    return False


def normalize_urls(raw_urls):
    """Limpia una lista de enlaces y elimina lineas vacias."""
    return [url.strip() for url in raw_urls if url.strip()]


def build_output_template(output_dir, output_name, url_count=1):
    """Crea la ruta base de salida para yt-dlp dentro de la carpeta elegida."""
    output_dir.mkdir(parents=True, exist_ok=True)

    if output_name:
        if url_count > 1:
            # Si hay varias URLs, se agrega un numero para evitar sobrescribir archivos.
            return str(output_dir / f"{output_name}_%(autonumber)s.%(ext)s")

        # El usuario puede elegir un nombre simple, por ejemplo: --output musica.
        return str(output_dir / f"{output_name}.%(ext)s")

    # Si no se indica un nombre, yt-dlp usara el titulo del contenido.
    return str(output_dir / "%(title)s.%(ext)s")


def build_audio_command(urls, output_template, audio_format):
    """Construye el comando para descargar y convertir a un formato de audio."""
    return [
        *get_ytdlp_command(),
        "--no-playlist",
        "--extract-audio",
        "--audio-format",
        audio_format,
        "--output",
        output_template,
        *urls,
    ]


def build_video_command(urls, output_template, video_format):
    """Construye el comando para descargar y guardar como video."""
    return [
        *get_ytdlp_command(),
        "--no-playlist",
        "--format",
        "bestvideo+bestaudio/best",
        "--merge-output-format",
        video_format,
        "--output",
        output_template,
        *urls,
    ]


def download_media(urls, media_format, output_dir, output_name=None):
    """Ejecuta yt-dlp con los argumentos adecuados segun el formato elegido."""
    urls = normalize_urls(urls)
    output_template = build_output_template(output_dir, output_name, len(urls))

    if media_format in AUDIO_FORMATS:
        command = build_audio_command(urls, output_template, media_format)
    else:
        command = build_video_command(urls, output_template, media_format)

    try:
        # shell=False es el valor predeterminado, y se usa una lista de argumentos
        # para evitar ejecutar texto como comando del sistema.
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as error:
        print(
            f"Error: yt-dlp no pudo completar la descarga. Codigo de salida: {error.returncode}",
            file=sys.stderr,
        )
        return False

    print(f"Descarga finalizada. Revisa la carpeta: {output_dir}")
    return True


def ask_non_empty(prompt):
    """Pide texto al usuario hasta recibir una respuesta no vacia."""
    while True:
        value = input(prompt).strip()

        if value:
            return value

        print("Este campo no puede quedar vacio.")


def ask_format():
    """Muestra los formatos disponibles y devuelve uno valido."""
    audio_options = ", ".join(sorted(AUDIO_FORMATS))
    video_options = ", ".join(sorted(VIDEO_FORMATS))

    print(f"Formatos de audio: {audio_options}")
    print(f"Formatos de video: {video_options}")

    while True:
        media_format = input("Formato deseado: ").strip().lower()

        if media_format in ALLOWED_FORMATS:
            return media_format

        print("Formato no permitido. Intenta con uno de la lista.")


def ask_urls():
    """Pide uno o varios enlaces, uno por linea."""
    print("Pega uno o varios enlaces permitidos.")
    print("Escribe un enlace por linea y presiona Enter en una linea vacia para continuar.")

    urls = []

    while True:
        prompt = "URL: " if not urls else "Otra URL o Enter para continuar: "
        value = input(prompt).strip()

        if not value:
            if urls:
                return urls

            print("Debes escribir al menos una URL.")
            continue

        urls.append(value)


def ask_output_dir():
    """Pide la carpeta de salida y usa descargas/ si el usuario presiona Enter."""
    value = input(f"Carpeta de salida [{DEFAULT_DOWNLOADS_DIR}]: ").strip()

    if not value:
        return DEFAULT_DOWNLOADS_DIR

    return Path(value).expanduser().resolve()


def ask_confirmation(urls, media_format, output_dir):
    """Pide confirmacion antes de iniciar la descarga."""
    print()
    print("Resumen:")
    print(f"Cantidad de enlaces: {len(urls)}")
    for index, url in enumerate(urls, start=1):
        print(f"{index}. {url}")
    print(f"Formato: {media_format}")
    print(f"Carpeta de salida: {output_dir}")
    print()

    answer = input("Confirmar descarga? [s/N]: ").strip().lower()
    return answer in {"s", "si", "y", "yes"}


def run_interactive_menu():
    """Ejecuta el menu interactivo para usuarios principiantes."""
    print("Menu interactivo")
    print()

    urls = ask_urls()
    media_format = ask_format()
    output_dir = ask_output_dir()

    if not ask_confirmation(urls, media_format, output_dir):
        print("Descarga cancelada.")
        return 0

    if not check_ytdlp_installed():
        return 1

    if not check_tool_installed("ffmpeg"):
        return 1

    success = download_media(urls, media_format, output_dir)
    return 0 if success else 1


def parse_args():
    """Lee y valida los argumentos escritos por el usuario en la consola."""
    parser = argparse.ArgumentParser(
        description="Descarga contenido permitido como audio o video usando yt-dlp y ffmpeg."
    )
    parser.add_argument(
        "urls",
        nargs="*",
        help="Uno o varios enlaces autorizados para descargar. Si se omiten, se abre el menu.",
    )
    parser.add_argument(
        "--formato",
        choices=sorted(ALLOWED_FORMATS),
        help="Formato de salida permitido.",
    )
    parser.add_argument(
        "--carpeta",
        default=str(DEFAULT_DOWNLOADS_DIR),
        help="Carpeta de salida. Por defecto usa descargas/.",
    )
    parser.add_argument(
        "--output",
        help="Nombre opcional del archivo final, sin extension. Ejemplo: --output musica",
    )
    return parser.parse_args()


def main():
    """Punto de entrada principal del programa."""
    print(LEGAL_NOTICE)
    print()

    args = parse_args()

    if not args.urls:
        return run_interactive_menu()

    if not args.formato:
        print("Error: cuando escribes URLs por comando debes indicar --formato.", file=sys.stderr)
        return 1

    if not check_ytdlp_installed():
        return 1

    if not check_tool_installed("ffmpeg"):
        return 1

    output_dir = Path(args.carpeta).expanduser().resolve()
    success = download_media(args.urls, args.formato, output_dir, args.output)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
