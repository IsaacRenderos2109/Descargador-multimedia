@echo off
cd /d "%~dp0"

echo =========================================
echo Instalador de Descargador Multimedia
echo =========================================
echo.

echo Verificando Python...
where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo No se encontro Python.
    echo Intentando instalar Python con Winget...
    where winget >nul 2>nul
    if errorlevel 1 (
        echo.
        echo ERROR: No se encontro Winget.
        echo Instala Python manualmente desde https://www.python.org/downloads/
        echo Durante la instalacion marca: Add python.exe to PATH
        echo Luego cierra esta ventana y ejecuta este archivo otra vez.
        echo.
        pause
        exit /b 1
    )

    winget install Python.Python.3.12
    echo.
    echo Python fue solicitado mediante Winget.
    echo Si la instalacion termino correctamente, cierra esta ventana,
    echo abre una nueva terminal y ejecuta otra vez instalar_dependencias.bat.
    echo Esto permite que Windows actualice el PATH.
    echo.
    pause
    exit /b 0
)

python --version
echo.

echo Intentando actualizar Python con Winget si hay una version nueva...
where winget >nul 2>nul
if errorlevel 1 (
    echo Winget no esta disponible. Se omite la actualizacion automatica de Python.
) else (
    winget upgrade Python.Python.3.12
)
echo.

echo Instalando o actualizando pip...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo.
    echo ERROR: No se pudo actualizar pip.
    echo Intenta ejecutar este archivo de nuevo o usa:
    echo python -m ensurepip --upgrade
    echo.
    pause
    exit /b 1
)

echo.
echo Instalando dependencias de Python desde requirements.txt...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: No se pudieron instalar las dependencias de Python.
    echo Revisa tu conexion a internet e intenta de nuevo.
    echo.
    pause
    exit /b 1
)

echo.
echo Verificando yt-dlp...
python -m yt_dlp --version
if errorlevel 1 (
    echo.
    echo ERROR: yt-dlp no quedo instalado correctamente.
    echo Intenta ejecutar:
    echo python -m pip install yt-dlp
    echo.
    pause
    exit /b 1
)

echo.
echo Verificando ffmpeg...
where ffmpeg >nul 2>nul
if errorlevel 1 (
    echo No se encontro ffmpeg.
    echo.
    echo Intentando instalar ffmpeg con Winget...
    where winget >nul 2>nul
    if errorlevel 1 (
        echo.
        echo No se encontro Winget.
        echo Instala ffmpeg manualmente desde:
        echo https://www.gyan.dev/ffmpeg/builds/
        echo Luego agrega la carpeta bin de ffmpeg al PATH.
        echo.
    ) else (
        winget install Gyan.FFmpeg
        echo.
        echo Si Winget instalo ffmpeg, cierra y vuelve a abrir PowerShell
        echo antes de ejecutar el programa.
        echo.
    )
) else (
    ffmpeg -version
)

echo.
echo =========================================
echo Instalacion finalizada
echo =========================================
echo.
echo Para abrir la interfaz grafica puedes usar:
echo ejecutar_gui.bat
echo.
echo O desde PowerShell:
echo python gui.py
echo.
pause
