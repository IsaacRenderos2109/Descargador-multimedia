# Arquitectura

`src/video_downloader` contiene contratos tipados (`models`), validación de URLs,
SQLite, servicio yt-dlp, workers, coordinador de cola e interfaz Qt. `app.py` y
`gui.py` son lanzadores de compatibilidad. PySide6 sustituye la implementación Tkinter.

## Ejecución

- `InspectWorker`: QThread para metadatos y expansión de listas públicas. Cancelación
  cooperativa; timeout de socket 15 s y reintentos acotados. No existe una garantía
  de finalización total en 15 s, porque la operación en curso puede reintentarse.
- `DownloadQueue`: una descarga activa; deduplicación de trabajos pendientes/activos
  idénticos, continuidad después de errores, notificación por señales Qt.
- `DownloadWorker`: QThread coordinador y proceso Python independiente con `spawn`.
  Los hooks de yt-dlp cruzan una cola IPC; la GUI solo se actualiza en el hilo principal.
  Windows cancela el árbol con `taskkill /T /F`; Linux termina su grupo de procesos.
  No se usa `QThread.terminate()`. `freeze_support` soporta ejecutables PyInstaller.
- `DiagnosticsWorker`: versiones de herramientas en segundo plano.
- `History`: conexiones SQLite cortas, WAL, timeout de bloqueo, transacciones y
  parámetros SQL. Guarda estados terminales con fecha UTC; no restaura cola pendiente.

## Archivos y recursos

Cada trabajo crea `VD-<video-id>-<uuid>` en el destino; nombres exclusivos y títulos
limitados a 48 bytes mediante yt-dlp con `windowsfilenames`. Se reserva margen para
rutas Windows y temporales. Cancelación elimina exclusivamente la carpeta del trabajo.
Un apagado forzado puede dejar parciales. Los archivos de usuario anteriores se conservan.

SQLite se guarda en `QStandardPaths.AppLocalDataLocation`, bajo `%LOCALAPPDATA%`
en Windows, con las organizaciones/nombre de app de Qt. `history.sqlite3` contiene
URLs, títulos y destinos; evita compartirlo si son privados. Preferencias mediante
QSettings (registro de usuario en Windows). No se escriben datos junto al ejecutable.

FFmpeg/FFprobe se buscan en `tools` junto al ejecutable o en PATH. Deben estar en
la misma carpeta. Deno tiene prioridad frente a Node si ambos están disponibles.
No se descargan binarios durante el uso. yt-dlp[default] incorpora EJS recomendado.
Las miniaturas usan Qt Network asíncrono, HTTPS a subdominios ytimg.com, timeout,
límite 2 MB y sin redirecciones. Fallos de miniatura no impiden descargar.

El CSV usa `csv` y neutraliza prefijos de fórmulas en hojas de cálculo; pandas no
aporta valor para este exportador. PyInstaller recopila extractores y recursos EJS,
y usa bibliotecas Qt dinámicas en formato de carpeta, sin empaquetar FFmpeg/Node
por defecto. Ver THIRD_PARTY.md para licencias de redistribución.
