@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo Iniciando Descargador Multimedia...
echo.

set "PYTHON_EXE="

if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"
    goto :run_app
)

if exist "%ProgramFiles%\Python312\python.exe" (
    set "PYTHON_EXE=%ProgramFiles%\Python312\python.exe"
    goto :run_app
)

if exist "%ProgramFiles(x86)%\Python312\python.exe" (
    set "PYTHON_EXE=%ProgramFiles(x86)%\Python312\python.exe"
    goto :run_app
)

where py >nul 2>nul
if not errorlevel 1 (
    for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do (
        set "PYTHON_EXE=%%P"
        goto :run_app
    )
)

for /f "delims=" %%P in ('where python 2^>nul') do (
    set "PYTHON_EXE=%%P"
    echo %%P | findstr /I "\\WindowsApps\\python" >nul
    if not errorlevel 1 (
        echo Se encontro el alias de Microsoft Store, se ignorara: %%P
    ) else (
        goto :run_app
    )
)

echo No se encontro una instalacion valida de Python.
echo Ejecuta primero: instalar_dependencias.bat
echo.
pause
exit /b 1

:run_app
echo Python usado:
echo %PYTHON_EXE%
"%PYTHON_EXE%" -c "import sys; print(sys.version)" >nul 2>nul
if errorlevel 1 (
    echo.
    echo El Python encontrado no es valido. Puede ser el alias de Microsoft Store.
    echo Ejecuta primero: instalar_dependencias.bat
    echo.
    pause
    exit /b 1
)

"%PYTHON_EXE%" gui.py

if errorlevel 1 (
    echo.
    echo No se pudo iniciar la aplicacion.
    echo Verifica que Python este instalado y que las dependencias esten instaladas.
    echo Puedes ejecutar primero: instalar_dependencias.bat
    echo.
    pause
)
