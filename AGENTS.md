# Codex - Instrucciones del repositorio

Este repositorio contiene un descargador multimedia ya implementado en Python (CLI en `app.py` y GUI Tkinter en `gui.py`). No lo reescribas ni elimines sin antes diagnosticarlo.

## Objetivo
Modernizar gradualmente la aplicacion de Windows con una interfaz profesional (PySide6), gestion de formatos disponibles, descarga por lotes, historial y empaquetado reproducible. Mantener el uso permitido y autorizado de contenido.

## Reglas de trabajo
- Trabaja en ramas `codex/*` y presenta los cambios mediante pull request. No alteres directamente `main`.
- Primero ejecuta `python -m pytest -q` y `python -m compileall -q app.py gui.py`.
- Mantiene compatibilidad con la CLI existente y con los formatos ya admitidos, salvo cambios justificados y documentados.
- Separa logica de descarga, GUI y persistencia. No bloquees el hilo principal de Qt.
- Escribe tests para logica pura; simula yt-dlp y FFmpeg. No realices descargas reales en CI.
- Los enlaces no deben contener credenciales incrustadas; no registres secretos, cookies ni tokens.
- No implementes elusion de DRM, controles de pago, autenticacion ni restricciones de acceso.
- Marca como `pendiente` todo lo que no se haya comprobado fisicamente en Windows.
- Usa `docs/CODEX_CLOUD.md` como hoja de ruta del entorno y actualizala a medida que avances.

## Verificacion minima
```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q
python -m compileall -q app.py gui.py
```

Para el artefacto Windows, utiliza el workflow manual de GitHub Actions.
