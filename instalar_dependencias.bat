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
set "DIAGNOSTIC_FILE=%~dp0diagnostico_instalacion.txt"
set "CURRENT_STEP=Inicio"
set "FAIL_WHAT="
set "FAIL_WHY="
set "FAIL_ACTION="

echo Diagnostico de instalacion - Descargador Multimedia > "%DIAGNOSTIC_FILE%"
echo Fecha: %DATE% %TIME% >> "%DIAGNOSTIC_FILE%"
echo Carpeta: %CD% >> "%DIAGNOSTIC_FILE%"
echo. >> "%DIAGNOSTIC_FILE%"

set "CURRENT_STEP=Verificar Python"
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
set "CURRENT_STEP=Instalar Python"
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
    set "FAIL_WHAT=No se pudo descargar Python automaticamente."
    set "FAIL_WHY=Puede no haber internet, la red puede bloquear python.org, PowerShell puede estar restringido o el antivirus pudo bloquear la descarga."
    set "FAIL_ACTION=Instala Python manualmente desde https://www.python.org/downloads/ marcando Add python.exe to PATH. Luego ejecuta este archivo otra vez."
    goto :diagnostico_error
)

echo.
echo Instalando Python silenciosamente y agregandolo al PATH...
"%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_launcher=1
if errorlevel 1 (
    set "FAIL_WHAT=No se pudo instalar Python automaticamente."
    set "FAIL_WHY=El instalador pudo requerir permisos, estar bloqueado por antivirus, o Windows pudo impedir la instalacion silenciosa."
    set "FAIL_ACTION=Ejecuta manualmente el instalador descargado en %PYTHON_INSTALLER% o instala Python desde https://www.python.org/downloads/. Luego ejecuta este archivo otra vez."
    goto :diagnostico_error
)

:find_python_after_install

echo.
echo Buscando Python despues de la instalacion...
set "CURRENT_STEP=Localizar Python instalado"
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
set "FAIL_WHAT=No se pudo localizar python.exe despues de instalar Python."
set "FAIL_WHY=Windows puede no haber actualizado el PATH todavia, Python pudo instalarse en otra ruta, o la instalacion pudo quedar incompleta."
set "FAIL_ACTION=Cierra esta ventana, abre una nueva terminal y ejecuta otra vez este archivo. Si continua, instala Python manualmente desde https://www.python.org/downloads/ marcando Add python.exe to PATH."
goto :diagnostico_error

:python_found
set "CURRENT_STEP=Validar Python"
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

set "CURRENT_STEP=Agregar Python al PATH"
echo Agregando Python y Scripts al PATH del usuario si hace falta...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$pythonDir = '%PYTHON_DIR%'; $scriptsDir = '%PYTHON_SCRIPTS%'; $userPath = [Environment]::GetEnvironmentVariable('Path','User'); if ($null -eq $userPath) { $userPath = '' }; $parts = $userPath -split ';' | Where-Object { $_ -ne '' }; foreach ($dir in @($pythonDir, $scriptsDir)) { if ($parts -notcontains $dir) { $parts += $dir } }; [Environment]::SetEnvironmentVariable('Path', ($parts -join ';'), 'User')"
if errorlevel 1 (
    set "FAIL_WHAT=No se pudo agregar Python al PATH del usuario."
    set "FAIL_WHY=PowerShell pudo estar bloqueado, el usuario puede no tener permisos para modificar variables de entorno, o Windows pudo impedir el cambio."
    set "FAIL_ACTION=Agrega manualmente estas rutas al PATH del usuario: %PYTHON_DIR% y %PYTHON_SCRIPTS%. Luego abre una nueva terminal y ejecuta este archivo otra vez."
    goto :diagnostico_error
)

set "PATH=%PYTHON_DIR%;%PYTHON_SCRIPTS%;%PATH%"
echo PATH actualizado para esta ventana.
echo Si era una instalacion nueva, tambien se guardo en el PATH del usuario.
echo.

set "CURRENT_STEP=Actualizar Python con Winget"
echo Intentando actualizar Python con Winget si hay una version nueva...
where winget >nul 2>nul
if errorlevel 1 (
    echo Winget no esta disponible. Se omite la actualizacion automatica de Python.
) else (
    winget upgrade Python.Python.3.12 --accept-package-agreements --accept-source-agreements
)
echo.

set "CURRENT_STEP=Instalar o actualizar pip"
echo Instalando o actualizando pip...
"%PYTHON_EXE%" -m ensurepip --upgrade
"%PYTHON_EXE%" -m pip install --upgrade pip
if errorlevel 1 (
    set "FAIL_WHAT=No se pudo instalar o actualizar pip."
    set "FAIL_WHY=Puede faltar internet, pip puede estar danado, certificados SSL pueden fallar, o Python pudo instalarse incompleto."
    set "FAIL_ACTION=Ejecuta este archivo otra vez. Si continua, prueba manualmente: %PYTHON_EXE% -m ensurepip --upgrade"
    goto :diagnostico_error
)

echo.
set "CURRENT_STEP=Instalar dependencias de Python"
echo Instalando dependencias de Python desde requirements.txt...
"%PYTHON_EXE%" -m pip install -r requirements.txt
if errorlevel 1 (
    set "FAIL_WHAT=No se pudieron instalar las dependencias de Python."
    set "FAIL_WHY=Puede no haber internet, PyPI puede estar bloqueado por la red, el antivirus puede bloquear descargas, o requirements.txt puede no estar en la carpeta."
    set "FAIL_ACTION=Revisa la conexion a internet y ejecuta este archivo de nuevo. Si continua, ejecuta manualmente: %PYTHON_EXE% -m pip install -r requirements.txt"
    goto :diagnostico_error
)

echo.
set "CURRENT_STEP=Verificar yt-dlp"
echo Verificando yt-dlp...
"%PYTHON_EXE%" -m yt_dlp --version
if errorlevel 1 (
    set "FAIL_WHAT=yt-dlp no quedo instalado correctamente."
    set "FAIL_WHY=La instalacion de dependencias pudo fallar parcialmente, el modulo pudo quedar corrupto, o Python esta usando otro entorno."
    set "FAIL_ACTION=Ejecuta manualmente: %PYTHON_EXE% -m pip install --upgrade yt-dlp. Luego ejecuta este archivo otra vez."
    goto :diagnostico_error
)

echo.
set "CURRENT_STEP=Verificar ffmpeg"
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
        echo ADVERTENCIA: No se encontro Winget y no se pudo instalar ffmpeg del sistema.
        echo La aplicacion intentara usar imageio-ffmpeg si esta disponible.
        echo Si la conversion falla, instala ffmpeg manualmente desde:
        echo https://www.gyan.dev/ffmpeg/builds/
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
set "CURRENT_STEP=Instalacion finalizada"
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
echo Instalacion completada correctamente. >> "%DIAGNOSTIC_FILE%"
echo Ultimo paso: %CURRENT_STEP% >> "%DIAGNOSTIC_FILE%"
pause
exit /b 0

:diagnostico_error
echo.
echo =========================================
echo DIAGNOSTICO DE ERROR
echo =========================================
echo Paso donde ocurrio: %CURRENT_STEP%
echo.
echo Que fallo:
echo %FAIL_WHAT%
echo.
echo Por que pudo fallar:
echo %FAIL_WHY%
echo.
echo Que debe hacer el usuario:
echo %FAIL_ACTION%
echo.
echo Se guardo este diagnostico en:
echo %DIAGNOSTIC_FILE%
echo.
(
    echo =========================================
    echo DIAGNOSTICO DE ERROR
    echo =========================================
    echo Fecha: %DATE% %TIME%
    echo Carpeta: %CD%
    echo Paso donde ocurrio: %CURRENT_STEP%
    echo.
    echo Que fallo:
    echo %FAIL_WHAT%
    echo.
    echo Por que pudo fallar:
    echo %FAIL_WHY%
    echo.
    echo Que debe hacer el usuario:
    echo %FAIL_ACTION%
    echo.
    echo Python detectado: %PYTHON_EXE%
    echo Instalador Python: %PYTHON_INSTALLER%
) >> "%DIAGNOSTIC_FILE%"
pause
exit /b 1
