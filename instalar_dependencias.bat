@echo off
setlocal
cd /d "%~dp0"
py -3 -c "import sys; assert sys.version_info >= (3, 11), 'Se requiere Python 3.11 o superior'"
if errorlevel 1 goto error
py -3 -m venv .venv
if errorlevel 1 goto error
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto error
.venv\Scripts\python.exe -m pip install --no-deps .
if errorlevel 1 goto error
echo Instalacion completada. Instala FFmpeg/FFprobe y Node.js 24 en PATH.
echo Ejecuta ejecutar_gui.bat
pause
exit /b 0
:error
echo Fallo la instalacion. Revisa el error anterior y README.md.
pause
exit /b 1
