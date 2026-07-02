# descargador-multimedia

`descargador-multimedia` es una aplicacion hecha en Python para descargar contenido permitido desde un enlace y guardarlo como audio o video usando `yt-dlp` y `ffmpeg`.

El proyecto incluye tres formas de uso:

- Interfaz grafica con Tkinter.
- Menu interactivo en consola.
- Comandos directos desde terminal.

## Aviso legal de uso responsable

Usa este programa solo con contenido propio, con permiso del autor, Creative Commons o contenido autorizado para descarga.

No uses esta herramienta para saltarte DRM, contenido privado, inicios de sesion, restricciones de pago, suscripciones, muros de pago ni protecciones tecnicas.

El usuario es responsable de cumplir las leyes aplicables y los terminos de uso de cada sitio.

## Que hace el programa

El programa permite:

- Pegar o escribir una URL.
- Pegar varios enlaces y descargarlos en lote.
- Elegir si quieres guardar el contenido como audio o video.
- Elegir el formato de salida.
- Seleccionar una carpeta de salida.
- Ver el progreso real de la descarga en una barra de progreso.
- Ver el porcentaje de avance.
- Ver el estado actual del proceso.
- Descargar usando `yt-dlp`.
- Convertir o unir audio/video usando `ffmpeg`.
- Guardar los archivos en `descargas/` o en la carpeta que elijas.

## Estructura del proyecto

```text
descargador-multimedia/
|-- app.py
|-- gui.py
|-- requirements.txt
|-- instalar_dependencias.bat
|-- ejecutar_gui.bat
|-- .gitignore
|-- README.md
`-- descargas/
    `-- .gitkeep
```

## Para que sirve cada archivo

- `app.py`: version de consola. Permite usar menu interactivo o comandos directos.
- `gui.py`: version con interfaz grafica usando Tkinter.
- `requirements.txt`: lista de dependencias de Python. Incluye `yt-dlp` e `imageio-ffmpeg`.
- `instalar_dependencias.bat`: instalador rapido para Windows. Verifica Python, intenta instalarlo o actualizarlo con Winget, si no hay Winget intenta descargar Python desde python.org, agrega Python y Scripts al PATH del usuario, instala dependencias de Python, verifica `yt-dlp` e instala un respaldo de `ffmpeg`.
- `ejecutar_gui.bat`: abre la interfaz grafica con doble clic.
- `.gitignore`: evita subir caches, entornos virtuales y archivos descargados.
- `README.md`: instrucciones del proyecto.
- `descargas/`: carpeta predeterminada donde se guardan los archivos descargados.

## Formatos permitidos

Audio:

- `mp3`
- `m4a`
- `wav`
- `flac`
- `opus`

Video:

- `mp4`
- `webm`
- `mkv`

## Interfaz grafica con Tkinter

El programa incluye una interfaz grafica hecha con Tkinter. Esta interfaz esta pensada para usar el descargador sin escribir comandos.

Desde la ventana puedes:

- Pegar una URL o varias URLs, una por linea.
- Elegir el formato de salida.
- Seleccionar la carpeta de salida con el boton `Examinar`.
- Presionar el boton `Descargar`.
- Ver una barra de progreso real durante la descarga.
- Ver el porcentaje de avance, por ejemplo `45.8%`.
- Ver mensajes de estado durante el proceso.

Los formatos disponibles desde la interfaz son:

- `mp3`
- `m4a`
- `wav`
- `flac`
- `opus`
- `mp4`
- `webm`
- `mkv`

La interfaz muestra estados como:

- `Preparando descarga...`
- `Descargando...`
- `Calculando progreso...`
- `Convirtiendo archivo...`
- `Descarga finalizada.`
- `Error en la descarga.`

Mientras se realiza la descarga, el boton `Descargar` se bloquea para evitar iniciar otra descarga encima. Cuando el proceso termina o ocurre un error, el boton vuelve a activarse.

La barra de progreso usa los `progress_hooks` de `yt-dlp`, por eso puede mostrar el progreso real cuando el sitio informa el tamano total del archivo. Si `yt-dlp` no puede calcular el tamano total, la barra cambia a modo indeterminado y muestra `Calculando progreso...`.

Cuando descargas audio en `mp3`, `m4a`, `wav`, `flac` u `opus`, el programa usa FFmpeg para convertir el archivo y muestra `Convirtiendo archivo...`.

## Requisitos

Necesitas instalar:

- Python 3.9 o superior.
- `yt-dlp`, instalado desde `requirements.txt`.
- `ffmpeg`, instalado en Windows o disponible como respaldo mediante `imageio-ffmpeg`.

Tkinter normalmente ya viene incluido con Python en Windows. No se instala desde `pip`.

## Paso 1: instalar Python en Windows

1. Entra a la pagina oficial:

   <https://www.python.org/downloads/>

2. Descarga Python para Windows.

3. Abre el instalador.

4. Muy importante: marca la casilla:

```text
Add python.exe to PATH
```

5. Luego presiona `Install Now`.

6. Cuando termine, cierra y vuelve a abrir PowerShell.

7. Verifica que Python funciona:

```powershell
python --version
```

Tambien verifica que `pip` funciona usando:

```powershell
python -m pip --version
```

Si ambos comandos muestran una version, Python quedo instalado correctamente.

## Paso 2: abrir la carpeta del proyecto

En PowerShell, entra a la carpeta del proyecto:

```powershell
cd C:\Users\custo\Documents\Codex\2026-06-25\crea-un-proyecto-en-python-llamado\descargador-multimedia
```

Si moviste el proyecto a otra carpeta, usa la ruta donde lo guardaste.

## Paso 3: instalar dependencias con el archivo BAT

El proyecto incluye un archivo llamado:

```text
instalar_dependencias.bat
```

Este archivo sirve para facilitar la instalacion en Windows.

Puedes ejecutarlo con doble clic. Tambien puedes ejecutarlo desde PowerShell:

```powershell
.\instalar_dependencias.bat
```

El archivo hace estas tareas:

- Entra automaticamente a la carpeta del proyecto.
- Verifica si `python` esta disponible.
- Si no encuentra `python`, intenta usar el Python Launcher `py`.
- Si Python no esta instalado, intenta instalarlo con Winget usando `winget install Python.Python.3.12`.
- Si no existe Winget, intenta descargar el instalador oficial de Python desde `python.org`.
- Instala Python en modo silencioso con `pip` y con opcion de agregarlo al PATH.
- Despues de instalar Python, busca `python.exe` en rutas comunes de Windows.
- Agrega la carpeta de Python y la carpeta `Scripts` al PATH del usuario.
- Actualiza el PATH de la ventana actual para poder seguir instalando sin reiniciar en muchos casos.
- Si Python ya esta instalado, intenta actualizarlo con Winget usando `winget upgrade Python.Python.3.12`.
- Ejecuta `ensurepip` para asegurar que `pip` exista.
- Actualiza `pip`.
- Instala las dependencias de `requirements.txt`.
- Verifica que `yt-dlp` haya quedado instalado.
- Verifica si `ffmpeg` existe.
- Si falta `ffmpeg`, instala `imageio-ffmpeg` como respaldo para que la aplicacion pueda convertir sin depender del PATH del sistema.
- Si el respaldo falla, intenta instalar `ffmpeg` con Winget usando `winget install Gyan.FFmpeg`.
- Si ocurre un error importante, muestra un diagnostico con el paso exacto, que fallo, por que pudo fallar y que debe hacer el usuario.
- Guarda el diagnostico en `diagnostico_instalacion.txt`.
- Al final indica como ejecutar el programa.

En resumen: el archivo intenta prepararse para varios escenarios: PC con Winget, PC sin Winget, Python fuera del PATH, alias falso de Microsoft Store, falta de `pip`, falta de `yt-dlp` y falta de `ffmpeg`.

Importante: si no hay Winget, el `.bat` intentara descargar Python desde python.org usando PowerShell. Si la red bloquea la descarga o no hay internet, entonces te pedira instalar Python manualmente desde:

<https://www.python.org/downloads/>

Durante la instalacion de Python debes marcar:

```text
Add python.exe to PATH
```

Despues de instalar Python, ya sea con Winget, descarga directa o manualmente, normalmente el instalador intenta actualizar el PATH sin reiniciar. Si aun asi Windows no reconoce `python`, cierra y vuelve a abrir PowerShell. Luego ejecuta otra vez `instalar_dependencias.bat`.

## Paso 4: instalar dependencias manualmente

Si prefieres no usar el archivo `.bat`, puedes instalar las dependencias manualmente.

La forma recomendada es:

```powershell
python -m pip install -r requirements.txt
```

Esto instala `yt-dlp`.

En Windows tambien puedes hacer doble clic en:

```text
instalar_dependencias.bat
```

Ese archivo ejecuta automaticamente la instalacion de dependencias y tambien intenta ayudarte con `ffmpeg` si tienes Winget.

Los comandos principales que ejecuta son:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Paso 5: instalar ffmpeg en Windows

`ffmpeg` es necesario para convertir audio y unir video con audio. Si quieres descargar audio en `mp3`, `m4a`, `wav`, `flac` u `opus`, FFmpeg es obligatorio para hacer la conversion.

Si usaste `instalar_dependencias.bat`, el archivo ya intento revisar o instalar `ffmpeg` con Winget. Si no funciono, puedes instalarlo manualmente con las instrucciones de esta seccion.

El proyecto tambien incluye `imageio-ffmpeg` como respaldo. Esto permite que la aplicacion encuentre un `ffmpeg` instalado por Python aunque el comando `ffmpeg` no exista en el PATH de Windows.

### Opcion recomendada: instalar con Winget

Abre PowerShell y ejecuta:

```powershell
winget install Gyan.FFmpeg
```

Cuando termine, cierra PowerShell y vuelve a abrirlo.

Verifica que `ffmpeg` funciona:

```powershell
ffmpeg -version
```

Si aparece informacion de version, `ffmpeg` quedo instalado correctamente.

### Opcion manual si no tienes Winget

1. Entra a:

   <https://www.gyan.dev/ffmpeg/builds/>

2. Descarga una version de ffmpeg para Windows.

3. Descomprime el archivo.

4. Busca la carpeta `bin`, donde debe estar `ffmpeg.exe`.

5. Agrega esa carpeta `bin` al `PATH` de Windows.

6. Cierra y vuelve a abrir PowerShell.

7. Verifica:

```powershell
ffmpeg -version
```

## Forma recomendada de uso: interfaz grafica

La forma mas facil es abrir la interfaz grafica.

Puedes hacerlo con doble clic en:

```text
ejecutar_gui.bat
```

Este archivo `.bat` entra automaticamente a la carpeta del proyecto y ejecuta:

```powershell
python gui.py
```

Por eso, despues de instalar dependencias, una persona puede abrir el programa sin escribir comandos, solo con doble clic en `ejecutar_gui.bat`.

Tambien puedes abrirla desde PowerShell:

```powershell
python gui.py
```

La ventana permite:

1. Pegar una URL o varios enlaces, uno por linea.
2. Elegir el formato de salida: `mp3`, `m4a`, `wav`, `flac`, `opus`, `mp4`, `webm` o `mkv`.
3. Elegir la carpeta de salida con el boton `Examinar`.
4. Presionar `Descargar`.
5. Ver la barra de progreso y el porcentaje.
6. Ver el estado actual de la descarga.

Antes de iniciar, la aplicacion muestra una confirmacion con la URL, el formato y la carpeta elegida.

Durante la descarga, el boton `Descargar` queda desactivado. Al finalizar o fallar, vuelve a activarse automaticamente.

### Descargar varios enlaces desde la interfaz

En la caja de texto de URLs puedes pegar varios enlaces, uno debajo del otro:

```text
https://ejemplo.com/video-1
https://ejemplo.com/video-2
https://ejemplo.com/video-3
```

Luego eliges el formato y presionas `Descargar`. El programa enviara todos los enlaces a `yt-dlp` en una sola operacion de lote.

## Uso con menu interactivo en consola

Si prefieres usar la terminal, ejecuta:

```powershell
python app.py
```

El programa te pedira:

1. Una o varias URLs.
2. Formato deseado.
3. Carpeta de salida.
4. Confirmacion antes de descargar.

Si presionas Enter cuando pide la carpeta de salida, se usara la carpeta predeterminada:

```text
descargas/
```

## Uso con comandos directos

Tambien puedes usar comandos directos.

### Descargar como MP3

```powershell
python app.py "URL_DEL_VIDEO" --formato mp3
```

### Descargar varios enlaces como MP3

Puedes escribir varios enlaces en el mismo comando:

```powershell
python app.py "URL_1" "URL_2" "URL_3" --formato mp3
```

Todos se guardaran en la carpeta de salida con el mismo formato.

### Descargar como MP4

```powershell
python app.py "URL_DEL_VIDEO" --formato mp4
```

### Descargar como WAV

```powershell
python app.py "URL_DEL_VIDEO" --formato wav
```

### Descargar como M4A

```powershell
python app.py "URL_DEL_VIDEO" --formato m4a
```

### Elegir nombre de archivo

Puedes elegir el nombre del archivo final usando `--output`.

No escribas la extension, porque el programa la agrega segun el formato.

```powershell
python app.py "URL_DEL_VIDEO" --formato mp3 --output musica
```

Ese comando guardara un archivo llamado algo como:

```text
musica.mp3
```

Si usas `--output` con varios enlaces, el programa agrega un numero automaticamente para evitar sobrescribir archivos:

```powershell
python app.py "URL_1" "URL_2" --formato mp3 --output musica
```

Esto puede crear archivos como:

```text
musica_00001.mp3
musica_00002.mp3
```

### Elegir carpeta de salida

Puedes indicar otra carpeta usando `--carpeta`:

```powershell
python app.py "URL_DEL_VIDEO" --formato mp4 --carpeta "C:\Videos"
```

## Donde se guardan las descargas

Por defecto, los archivos se guardan en:

```text
descargador-multimedia/descargas/
```

Si usas la interfaz grafica, puedes elegir otra carpeta con el boton `Examinar`.

Si usas consola, puedes elegir otra carpeta con `--carpeta`.

## Instalacion y ejecucion con archivos BAT

El proyecto incluye dos archivos `.bat` para usuarios de Windows:

```text
instalar_dependencias.bat
ejecutar_gui.bat
```

### instalar_dependencias.bat

Sirve para preparar la computadora.

Hace lo siguiente:

- Comprueba si Python esta instalado.
- Si no esta instalado, intenta instalar Python con Winget.
- Si Python ya esta instalado, intenta actualizarlo con Winget.
- Actualiza `pip`.
- Instala `yt-dlp` desde `requirements.txt`.
- Comprueba si `yt-dlp` funciona.
- Comprueba si `ffmpeg` esta instalado.
- Si falta `ffmpeg`, instala `imageio-ffmpeg` como respaldo.
- Si el respaldo no funciona y hay Winget, intenta instalar ffmpeg del sistema.
- Si algo falla, muestra un diagnostico claro.

Si el `.bat` instala Python por primera vez, normalmente intentara seguir solo porque agrega Python al PATH de la ventana actual y al PATH del usuario. Si Windows aun no reconoce `python`, cierra la ventana y ejecuta `instalar_dependencias.bat` una segunda vez.

### Diagnostico de errores del instalador

Si `instalar_dependencias.bat` falla, no solo mostrara `ERROR`. Tambien mostrara:

- En que paso ocurrio.
- Que fallo.
- Por que pudo fallar.
- Que debe hacer el usuario.

Ademas, crea o actualiza este archivo:

```text
diagnostico_instalacion.txt
```

Ese archivo queda en la misma carpeta del programa. Si necesitas pedir ayuda, puedes enviar una captura del mensaje o compartir el contenido de `diagnostico_instalacion.txt`.

### ejecutar_gui.bat

Sirve para abrir el programa.

Hace lo siguiente:

- Entra automaticamente a la carpeta del proyecto.
- Ejecuta `python gui.py`.
- Si ocurre un error, deja la ventana abierta para que puedas leer el mensaje.

Flujo recomendado:

1. Doble clic en `instalar_dependencias.bat`.
2. Si instala Python pero no puede continuar, cerrar y ejecutar otra vez `instalar_dependencias.bat`.
3. Doble clic en `ejecutar_gui.bat`.
4. Pegar uno o varios enlaces.
5. Elegir formato y carpeta.
6. Descargar.

## Errores comunes y soluciones

### Error: no se encontro yt-dlp

Significa que falta instalar la dependencia de Python.

Solucion:

```powershell
python -m pip install -r requirements.txt
```

Tambien puedes ejecutar:

```text
instalar_dependencias.bat
```

### pip no se reconoce como comando

Usa `pip` a traves de Python:

```powershell
python -m pip install -r requirements.txt
```

Si `python` tampoco se reconoce, instala Python y marca `Add python.exe to PATH`.

### Error: no se encontro ffmpeg

Significa que `ffmpeg` no esta instalado o no esta en el `PATH`.

Primero ejecuta:

```text
instalar_dependencias.bat
```

Ese archivo instala `imageio-ffmpeg` como respaldo. Si aun asi falla, instala ffmpeg del sistema.

Solucion recomendada para ffmpeg del sistema:

```powershell
winget install Gyan.FFmpeg
```

Despues cierra y vuelve a abrir PowerShell.

Verifica:

```powershell
ffmpeg -version
```

### La barra muestra Calculando progreso

Esto no siempre es un error. A veces `yt-dlp` no puede saber el tamano total del archivo antes o durante la descarga. En ese caso, la interfaz usa una barra indeterminada y muestra:

```text
Calculando progreso...
```

La descarga puede continuar normalmente aunque no se muestre un porcentaje exacto.

### La GUI muestra Error en la descarga

La interfaz muestra `Error en la descarga` cuando `yt-dlp` no puede completar el proceso. El mensaje incluye el detalle real devuelto por `yt-dlp`.

Puede ocurrir por:

- URL invalida.
- Contenido privado.
- Contenido con restricciones de pago.
- Sitio que no permite descargar ese contenido.
- Problemas de internet.
- Falta de FFmpeg para convertir o unir archivos.

### La ventana no abre

Verifica que Python funcione:

```powershell
python --version
```

Luego intenta abrir la GUI desde PowerShell para ver el error:

```powershell
python gui.py
```

Si ves un mensaje como `Python was not found; run without arguments to install from the Microsoft Store`, Windows esta usando el alias de Microsoft Store en lugar del Python real. Ejecuta:

```text
instalar_dependencias.bat
```

Luego abre el programa con:

```text
ejecutar_gui.bat
```

El archivo `ejecutar_gui.bat` busca el `python.exe` real en rutas comunes, prueba el Python Launcher `py` y evita quedarse solamente con el alias de Microsoft Store.

### No se encontro Winget

En algunas computadoras Windows no trae Winget instalado. En ese caso, `instalar_dependencias.bat` intenta descargar Python directamente desde python.org.

Si tambien falla esa descarga, normalmente es por:

- No hay internet.
- La red bloquea descargas.
- PowerShell tiene restricciones.
- El antivirus bloqueo el instalador.

Solucion:

1. Instala Python manualmente desde <https://www.python.org/downloads/>.
2. Marca `Add python.exe to PATH`.
3. Ejecuta otra vez `instalar_dependencias.bat`.

### La descarga falla aunque yt-dlp y ffmpeg estan instalados

Puede pasar si:

- El enlace no es valido.
- El sitio no permite descargar ese contenido.
- El contenido es privado.
- El contenido requiere inicio de sesion.
- El contenido tiene restricciones de pago o protecciones.
- No tienes conexion a internet.

Este programa no intenta saltarse restricciones, logins, DRM ni protecciones.

## Recomendacion para subir a GitHub

Antes de subir el proyecto, puedes mantener esta estructura:

```text
descargador-multimedia/
|-- app.py
|-- gui.py
|-- requirements.txt
|-- instalar_dependencias.bat
|-- ejecutar_gui.bat
|-- .gitignore
|-- README.md
`-- descargas/
    `-- .gitkeep
```

No subas archivos descargados dentro de `descargas/`. La carpeta incluye `.gitkeep` solo para que GitHub conserve la carpeta vacia.

## Carpeta limpia para compartir

Si quieres compartir el proyecto con otra persona, usa la carpeta `reales`.

Esa carpeta debe contener solamente los archivos necesarios:

```text
reales/
`-- descargador-multimedia/
    |-- app.py
    |-- gui.py
    |-- requirements.txt
    |-- instalar_dependencias.bat
    |-- ejecutar_gui.bat
    |-- .gitignore
    |-- README.md
    `-- descargas/
        `-- .gitkeep
```

No debe incluir:

- `__pycache__/`
- `.venv/`
- archivos descargados como `.mp3`, `.mp4`, `.wav`, etc.
- carpetas internas de Codex.
- archivos temporales.
- datos personales o confidenciales.

La persona que reciba esa carpeta puede hacer esto:

1. Abrir `reales/descargador-multimedia`.
2. Ejecutar `instalar_dependencias.bat`.
3. Ejecutar `ejecutar_gui.bat`.

## Resumen rapido

1. Abre la carpeta del proyecto.
2. Ejecuta `instalar_dependencias.bat`.
3. Si el `.bat` instala Python pero no puede continuar, cierra la ventana y ejecuta otra vez `instalar_dependencias.bat`.
4. Si el `.bat` no pudo instalar ffmpeg, instala ffmpeg con `winget install Gyan.FFmpeg`.
5. Abre el programa con `ejecutar_gui.bat`.
6. Pega una URL permitida o varios enlaces, uno por linea.
7. Elige formato y carpeta.
8. Presiona `Descargar`.
