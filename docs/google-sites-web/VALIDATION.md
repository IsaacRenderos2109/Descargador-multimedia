# Verificación del servicio web

Las pruebas web usan videos y contenido sintético. No contactan YouTube ni
descargan material real.

En Linux, instala FFmpeg/FFprobe y ejecuta:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-web-dev.txt
ruff check web_service infra tests_web
ruff format --check web_service infra tests_web
python -m pytest tests_web -q
docker compose -f compose.web.yml config --quiet
docker build -f Dockerfile.web -t video-downloader-web:local .
```

En una red de desarrollo que inspeccione TLS, puedes pasar su CA confiable como
secreto de BuildKit (`--secret id=ca_bundle,src=/ruta/a/ca.pem`); el certificado
solo se monta durante `pip install` y no queda en la imagen.

Las pruebas cubren la página y cabeceras de inserción, acceso y aislamiento de
trabajos, validación de URL, cancelación, filtrado SSRF del proxy, metadatos y
generación de MP3/MP4 sintéticos verificados por FFprobe. Un build de Docker solo
valida la imagen; no valida el proxy TLS de una instalación, Google Sites ni el
funcionamiento con un video autorizado.

La workflow `Google Sites web service` se dispara con cambios a esta rama, con un
Pull Request hacia `feat/video-downloader-desktop`/`codex/cloud-bootstrap-v2` y
manualmente si está visible en Actions. GitHub normalmente solo muestra el
botón manual cuando el workflow ya existe en la rama predeterminada. No es
necesario cambiar `main` para probarlo: el push de la rama y el evento de PR lo
activan si GitHub admite el workflow de la rama propuesta. El workflow web
incluye también documentación, el generador `.env` y cambios al workflow común.

Los jobs del workflow preexistente `Tests and Windows build` se saltan para esta
rama web, para evitar empaquetar una aplicación de escritorio como parte de una
publicación web. El workflow se conserva para los cambios de escritorio y se
puede ejecutar manualmente desde una rama de escritorio.

Una publicación se considera verificada solo después de comprobar en el host
remoto `/health` sobre HTTPS, login, descarga de un medio autorizado, límites,
cancelación y caducidad. El iframe se debe probar en un Google Sites publicado y
en los navegadores destino; los tests simulados no demuestran integración real.
