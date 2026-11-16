# Entorno de desarrollo: Codex Cloud

## Estado inicial
Repositorio existente: `IsaacRenderos2109/Descargador-multimedia`.
La rama `main` conserva el programa original: `app.py` (CLI) y `gui.py` (Tkinter).
La rama `codex/cloud-bootstrap-v2` configura el entorno de trabajo sin cambiar la logica de descargas.

## Configuracion del entorno Cloud
- Sistema: Linux, Python 3.12 o superior (preferible 3.12 para consistencia con CI).
- Comando de instalacion:
  ```bash
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt -r requirements-dev.txt
  ```
- Comandos de comprobacion:
  ```bash
  python -m pytest -q
  python -m compileall -q app.py gui.py
  ```
- No se requieren credenciales de YouTube, claves de API ni secretos para el desarrollo o CI.
- No realizar pruebas de descarga real contra plataformas en el entorno automatizado.

## Crear una tarea en Codex
Selecciona este repositorio como entorno de trabajo, configura la instalacion anterior y pide una implementacion incremental. Conserva la CLI y la GUI Tkinter mientras introduces PySide6 en un modulo aislado, hasta contar con pruebas y una version Windows comprobada.

### Primer encargo recomendado
1. Auditar el codigo existente y documentar dependencias y riesgos.
2. Crear arquitectura modular sin romper `app.py` ni `gui.py`.
3. Desarrollar una nueva GUI en PySide6 con enlace, formato, resolucion disponible, carpeta, cola y progreso.
4. Agregar manejo seguro de errores, cancelacion y pruebas con mocks.
5. Introducir pruebas de integración sin conexiones externas.
6. Actualizar CI y el flujo de compilacion de Windows para empaquetar la nueva entrada.
7. Crear PR con informe de resultados, evidencia y pasos de prueba manual.

## Automatizaciones incluidas
- `.github/workflows/ci.yml`: revisa sintaxis y pruebas en Linux/Windows.
- `.github/workflows/build-windows.yml`: empaqueta la GUI Tkinter actual en Windows mediante PyInstaller; se ejecuta manualmente.

**Nota:** El flujo de Windows es un primer intento reproducible; requiere una ejecucion exitosa de Actions y una prueba local del .exe antes de considerarse validado.

## Limites de uso
Solo contenido propio, libre o autorizado. No implementar bypass de DRM, restricciones de pago ni protecciones de acceso.
