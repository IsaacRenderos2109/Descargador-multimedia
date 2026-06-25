@echo off
cd /d "%~dp0"

echo Iniciando Descargador Multimedia...
python gui.py

if errorlevel 1 (
    echo.
    echo No se pudo iniciar la aplicacion.
    echo Verifica que Python este instalado y que las dependencias esten instaladas.
    echo Puedes ejecutar primero: instalar_dependencias.bat
    echo.
    pause
)
