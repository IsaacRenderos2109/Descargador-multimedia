# Informe de validación

Fecha: 16 de noviembre de 2026. Rama: `feat/video-downloader-desktop`.

## Entorno utilizado

Linux x86_64, Python 3.12.14, PySide6 6.12.0, yt-dlp 2026.10.26,
yt-dlp-ejs 0.8.0, FFmpeg/FFprobe 7.1.5, Node.js 24.22.1.
Dependencias exactas registradas en los dos archivos requirements.

## Resultados comprobados

| Comprobación | Resultado |
| --- | --- |
| `python -m pytest -q` con Qt offscreen | **63 aprobadas**, 0 fallos, 0 errores, 0 omitidas |
| Ruff (src, tests, scripts y lanzadores) | Sin errores |
| Ruff format | 25 archivos conformes |
| Mypy | Sin errores en los 9 módulos del paquete |
| `pip check` | Sin incompatibilidades detectadas |
| Diagnóstico de herramientas | FFmpeg, FFprobe y Node ejecutados correctamente |
| Qt desde el código | Ventana y tres pestañas; selección y señales comprobadas |
| `--smoke-test` desde Python | Arranque/cierre offline e IPC con `spawn` correctos |
| yt-dlp sin stdout/stderr | Inicialización y carga del extractor YouTube correctas |
| Conversiones FFmpeg reales | WAV sintético a MP3, MKV sintético a MP4; FFprobe verifica salida |
| SQLite | Persistencia, escrituras concurrentes, idempotencia y CSV comprobados |
| Procesos | IPC, cancelación de un hijo real simulado y detección de terminación inesperada |
| Windows | Validación simulada de la llamada `taskkill /T /F` y saneamiento de nombres con yt-dlp |
| PyInstaller en Linux | Compilación en formato carpeta completada |
| Binario Linux `--smoke-test` | Arranque Qt, `spawn`, extractor YouTube y recursos EJS correctos |
| Distribución Python | Wheel y sdist construidos |
| Workflow de Actions | Validación estática con actionlint 1.7.7 sin errores |
| Git | `git diff --check` sin errores |

Las pruebas incluyen URLs malformadas, hosts impostores, duplicados, listas
inaccesibles y grandes, formatos DRM excluidos, restricciones, errores de red,
resolución no disponible, progreso indeterminado, cancelación y consentimiento.
La captura `interface.png` muestra **datos simulados**, no un análisis real.

## Alcance de las simulaciones

**No se realizaron descargas reales de YouTube.** Sus respuestas de metadatos,
listas, errores y transferencias se simulan. La prueba de cola/interfaz usa un
worker simulado; las pruebas de procesos sí crean y cancelan procesos del sistema.
Los archivos sintéticos usados con FFmpeg se generan localmente y no provienen
de YouTube. No se comprobó la descarga real de miniaturas por Internet.

## Limitaciones y pendientes externos

- Este entorno ejecuta Linux. **No se generó ni ejecutó un `.exe` nativo de Windows**.
  No se ejecutó el workflow en los servidores de GitHub; actionlint solo valida
  su definición estáticamente. Las pruebas de la matriz 3.11/3.13 están preparadas,
  pero solo Python 3.12 se ejecutó en esta máquina.
- El build local de PyInstaller es ELF para Linux; no debe renombrarse a `.exe`.
  El artefacto Windows requiere el workflow o una compilación local en Windows.
- La validación de red/proveedor en producción requiere una descarga manual de
  contenido propio o autorizado. Cambios de YouTube, red, geografía o límites de
  plataforma pueden afectar disponibilidad aunque las simulaciones pasen.
- El ejecutable necesita FFmpeg/FFprobe y Node/Deno instalados o en `tools`.
  Por defecto no se distribuyen esos binarios. El paquete no está firmado.
- Se admiten videos públicos finalizados y listas de hasta 200 entradas; no hay
  soporte de directos, autenticación, DRM ni recuperación de la cola tras reiniciar.
- Un cierre forzado puede dejar archivos parciales. La cancelación cooperativa del
  análisis puede tardar mientras finalizan solicitudes/reintentos en curso.
- Un MP4 existente puede conservar codecs que requieran un reproductor actualizado.
  FFmpeg no aumenta la calidad de fuentes de audio ni escala las resoluciones.

PyInstaller mostró avisos relativos a módulos opcionales (`curl_cffi` y el soporte
Emscripten de urllib3). No son dependencias del flujo elegido; el arranque empaquetado,
extractor y recursos EJS se comprobaron correctamente. Fontconfig emitió un aviso
de caché no escribible en Linux; no impidió las pruebas Qt ni el arranque.

## Cómo obtener y probar el `.exe`

1. Sube esta rama a GitHub y ejecuta **Tests and Windows build**. Las pruebas deben
   aprobar antes del trabajo `windows-build`.
2. Descarga **VideoDownloader-Windows-x64** de los artefactos de esa ejecución y
   extrae la carpeta completa. Conserva `_internal` junto a `VideoDownloader.exe`.
3. Instala FFmpeg/FFprobe y Node.js 24 en PATH, o coloca sus ejecutables en `tools`.
4. Ejecuta `VideoDownloader.exe`, comprueba herramientas y realiza una prueba manual
   con un video propio/autorizado y una lista pública autorizada. Comprueba MP4,
   MP3, cancelación, destino Unicode, duplicados e historial en una VM limpia.
5. Para compilar directamente en Windows, instala `requirements-dev.txt`, instala
   el proyecto y ejecuta `./scripts/build_windows.ps1`. Revisa las licencias de
   redistribución y firma el ejecutable antes de una publicación de producción.

Las instrucciones completas y comandos reproducibles están en el README.
