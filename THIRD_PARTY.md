# Componentes de terceros

El código propio está bajo MIT; las dependencias mantienen sus licencias.

- PySide6 / Shiboken / Qt: LGPLv3, GPLv3 o licencia comercial, según componente.
  Se usa enlace dinámico y se conserva la carpeta `_internal` para permitir sustituir
  bibliotecas. Consulta https://doc.qt.io/qtforpython-6/licenses.html y conserva los
  avisos de las distribuciones oficiales. No se incluyen módulos comerciales.
- yt-dlp: Unlicense; los componentes empaquetados tienen sus propias licencias.
  https://github.com/yt-dlp/yt-dlp/blob/master/LICENSE
- yt-dlp-ejs: consulta la licencia de la versión fijada en su distribución.
- PyInstaller: GPL con excepción para distribuir aplicaciones empaquetadas.
  https://pyinstaller.org/en/stable/license.html
- FFmpeg/FFprobe: LGPL o GPL dependiendo de las opciones de compilación.
  https://ffmpeg.org/legal.html
- Node.js: MIT y avisos de sus componentes. https://nodejs.org/en/about/previous-releases
- Deno (alternativo): MIT. https://github.com/denoland/deno

Los artefactos predeterminados NO incluyen FFmpeg/FFprobe ni runtimes JavaScript.
Instálalos aparte o utiliza `tools` junto al ejecutable. Si distribuyes herramientas
con `-ToolsDirectory`, incluye sus licencias, avisos y, cuando aplique, acceso al
código fuente correspondiente a las compilaciones exactas. Antes de publicar una
versión comercial revisa las obligaciones de cada binario y firma el ejecutable.
