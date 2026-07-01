@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo =========================================
echo Instalador de Descargador Multimedia
echo =========================================
echo.

set "PYTHON_EXE="
set "PYTHON_INSTALLER_URL=https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe"
set "PYTHON_INSTALLER=%TEMP%\python-3.12-installer.exe"

echo Verificando Python en el PATH...
for /f "delims=" %%P in ('where python 2^>nul') do (
    set "PYTHON_EXE=%%P"
    echo %%P | findstr /I "\\WindowsApps\\python" >nul
    if not errorlevel 1 (
        echo Se encontro el alias de Microsoft Store, no una instalacion real de Python.
    ) else (
        goto :python_found
    )
)

if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"
    goto :python_found
)

if exist "%ProgramFiles%\Python312\python.exe" (
    set "PYTHON_EXE=%ProgramFiles%\Python312\python.exe"
    goto :python_found
)

if exist "%ProgramFiles(x86)%\Python312\python.exe" (
    set "PYTHON_EXE=%ProgramFiles(x86)%\Python312\python.exe"
    goto :python_found
)

echo No se encontro python en el PATH.
echo Verificando Python Launcher...
where py >nul 2>nul
if not errorlevel 1 (
    for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do (
        set "PYTHON_EXE=%%P"
        goto :python_found
    )
)

echo No se encontro Python Launcher.
echo Intentando instalar Python con Winget...
goto :install_python

:install_python
where winget >nul 2>nul
if errorlevel 1 (
    echo.
    echo No se encontro Winget.
    echo Se intentara descargar Python directamente desde python.org.
    goto :download_python
)

winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
    echo.
    echo Winget no pudo instalar Python.
    echo Se intentara descargar Python directamente desde python.org.
    goto :download_python
)
goto :find_python_after_install

:download_python
echo.
echo Descargando instalador oficial de Python...
echo %PYTHON_INSTALLER_URL%
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYTHON_INSTALLER_URL%' -OutFile '%PYTHON_INSTALLER%'"
if errorlevel 1 (
    echo.
    echo ERROR: No se pudo descargar Python automaticamente.
    echo Posibles causas: no hay internet, PowerShell bloqueado o conexion restringida.
    echo Instala Python manualmente desde:
    echo https://www.python.org/downloads/
    echo Durante la instalacion marca: Add python.exe to PATH
    echo Luego ejecuta este archivo otra vez.
    echo.
    pause
    exit /b 1
)

echo.
echo Instalando Python silenciosamente y agregandolo al PATH...
"%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_launcher=1
if errorlevel 1 (
    echo.
    echo ERROR: No se pudo instalar Python automaticamente.
    echo Ejecuta el instalador manualmente:
    echo %PYTHON_INSTALLER%
    echo Luego ejecuta este archivo otra vez.
    echo.
    pause
    exit /b 1
)

:find_python_after_install

echo.
echo Buscando Python despues de la instalacion...
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"
    goto :python_found
)

if exist "%ProgramFiles%\Python312\python.exe" (
    set "PYTHON_EXE=%ProgramFiles%\Python312\python.exe"
    goto :python_found
)

if exist "%ProgramFiles(x86)%\Python312\python.exe" (
    set "PYTHON_EXE=%ProgramFiles(x86)%\Python312\python.exe"
    goto :python_found
)

for /f "delims=" %%P in ('where python 2^>nul') do (
    set "PYTHON_EXE=%%P"
    goto :python_found
)

where py >nul 2>nul
if not errorlevel 1 (
    for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do (
        set "PYTHON_EXE=%%P"
        goto :python_found
    )
)

echo.
echo ERROR: Python fue solicitado con Winget, pero no se pudo localizar python.exe.
echo Cierra esta ventana, abre una nueva terminal y ejecuta otra vez este archivo.
echo Si el problema continua, instala Python manualmente desde:
echo https://www.python.org/downloads/
echo.
pause
exit /b 1

:python_found
echo Python encontrado:
echo %PYTHON_EXE%
"%PYTHON_EXE%" -c "import sys; print(sys.version)"
if errorlevel 1 (
    echo.
    echo El archivo encontrado no parece ser una instalacion valida de Python.
    echo Se intentara instalar Python con Winget.
    echo.
    goto :install_python
)
echo.

for %%D in ("%PYTHON_EXE%") do set "PYTHON_DIR=%%~dpD"
set "PYTHON_DIR=%PYTHON_DIR:~0,-1%"
set "PYTHON_SCRIPTS=%PYTHON_DIR%\Scripts"

echo Agregando Python y Scripts al PATH del usuario si hace falta...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$pythonDir = '%PYTHON_DIR%'; $scriptsDir = '%PYTHON_SCRIPTS%'; $userPath = [Environment]::GetEnvironmentVariable('Path','User'); if ($null -eq $userPath) { $userPath = '' }; $parts = $userPath -split ';' | Where-Object { $_ -ne '' }; foreach ($dir in @($pythonDir, $scriptsDir)) { if ($parts -notcontains $dir) { $parts += $dir } }; [Environment]::SetEnvironmentVariable('Path', ($parts -join ';'), 'User')"

set "PATH=%PYTHON_DIR%;%PYTHON_SCRIPTS%;%PATH%"
echo PATH actualizado para esta ventana.
echo Si era una instalacion nueva, tambien se guardo en el PATH del usuario.
echo.

echo Intentando actualizar Python con Winget si hay una version nueva...
where winget >nul 2>nul
if errorlevel 1 (
    echo Winget no esta disponible. Se omite la actualizacion automatica de Python.
) else (
    winget upgrade Python.Python.3.12 --accept-package-agreements --accept-source-agreements
)
echo.

echo Instalando o actualizando pip...
"%PYTHON_EXE%" -m ensurepip --upgrade
"%PYTHON_EXE%" -m pip install --upgrade pip
if errorlevel 1 (
    echo.
    echo ERROR: No se pudo actualizar pip.
    echo Intenta ejecutar este archivo de nuevo.
    echo.
    pause
    exit /b 1
)

echo.
echo Instalando dependencias de Python desde requirements.txt...
"%PYTHON_EXE%" -m pip install -r requirements.txt
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
"%PYTHON_EXE%" -m yt_dlp --version
if errorlevel 1 (
    echo.
    echo ERROR: yt-dlp no quedo instalado correctamente.
    echo Intenta ejecutar:
    echo "%PYTHON_EXE%" -m pip install yt-dlp
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
    echo Instalando respaldo de ffmpeg para Python con imageio-ffmpeg...
    "%PYTHON_EXE%" -m pip install imageio-ffmpeg
    "%PYTHON_EXE%" -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"
    if not errorlevel 1 (
        echo Respaldo de ffmpeg instalado correctamente para la aplicacion.
        goto :install_done
    )
    echo.
    echo No se pudo instalar el respaldo de ffmpeg con Python.
    echo Intentando instalar ffmpeg con Winget...
    where winget >nul 2>nul
    if errorlevel 1 (
        echo.
        echo No se encontro Winget.
        echo Si la aplicacion falla al convertir, instala ffmpeg manualmente desde:
        echo https://www.gyan.dev/ffmpeg/builds/
        echo Luego agrega la carpeta bin de ffmpeg al PATH.
        echo.
    ) else (
        winget install Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
        echo.
        echo Si Winget instalo ffmpeg, cierra y vuelve a abrir PowerShell
        echo antes de ejecutar el programa si el comando ffmpeg no aparece de inmediato.
        echo.
    )
) else (
    ffmpeg -version
)

:install_done
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
