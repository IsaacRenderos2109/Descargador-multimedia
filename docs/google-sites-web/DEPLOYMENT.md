# Despliegue del servicio web

Para una alternativa con presupuesto estricto de USD 0, consulta
[Preparación para Oracle Cloud Always Free](ORACLE-ALWAYS-FREE.md). La guía no
declara que Oracle sea gratuito para esta cuenta y prohíbe continuar mientras
la consola no confirme costo cero para todos los recursos.

Google Sites presenta la aplicación; el backend FastAPI y los procesos de
yt-dlp/FFmpeg viven en un host Linux remoto. Quien la usa solo necesita un
navegador. No debe instalar programas ni dejar su computadora encendida.

El backend no se ha desplegado ni se ha probado en un sitio público. La guía
describe cómo prepararlo desde la consola web del proveedor y cómo verificarlo
después de publicar.

## Arquitectura de alojamiento

La configuración actual contiene dos contenedores Compose:

- `web`: FastAPI y los workers. Solo publica `127.0.0.1:8000` en el host.
- `egress-proxy`: proxy CONNECT con lista permitida y verificación de IP pública.
  No publica puertos al host.

La red `backend` es interna. El contenedor web no tiene salida de red directa;
solo el proxy puede salir a los dominios de YouTube/Google Video permitidos. El
volumen `web_jobs` guarda medios temporales. El estado de la cola permanece en
memoria de una sola instancia.

### Comparación técnica de candidatos

Esta es una evaluación arquitectónica preliminar. Las condiciones vigentes y
las cuotas de cada plan deben confirmarse en su documentación oficial antes de
seleccionar o pagar un servicio.

| Opción | Compatibilidad con esta solución | Trabajo y límites que hay que considerar | Precio vigente |
| --- | --- | --- | --- |
| VM/VPS Linux, por ejemplo DigitalOcean Droplet | Ejecuta Docker Compose sin traducir sus dos servicios, redes y volumen. Es la opción más cercana a la configuración probada. | El operador mantiene el sistema, firewall, Docker, TLS, copias y alertas. Una VM fija sigue generando costo aunque no haya trabajos. | No verificado en esta revisión. |
| Google Cloud Run | Este archivo Compose no se despliega directamente. | Habría que traducir los servicios y validar las opciones vigentes de red, almacenamiento temporal y contenedores auxiliares. El estado de tareas en memoria no admite escalar libremente entre instancias. | No verificado en esta revisión. |
| Render | La configuración Compose no se despliega directamente como un stack. | Habría que traducir los servicios y confirmar red privada, política de salida, disco, reinicios y transferencia del plan elegido. | No verificado en esta revisión. |

**Recomendación de arquitectura:** empezar con una VM/VPS Linux de una sola
instancia que permita Docker Compose v2, redes internas y volumen local. Como
punto de partida para validar carga, reservar al menos 2 vCPU, 4 GB de RAM y
40 GB de disco; el Compose limita `web` a 1 GB/2 CPU y el proxy a 256 MB/1 CPU.
El volumen temporal está limitado por la aplicación a 1 GiB por configuración
predeterminada. Estos recursos son una estimación operativa inicial, no un precio
ni una garantía de rendimiento. Deben confirmarse con la calculadora del
proveedor elegido y medirse con uso autorizado.

No recomiendo todavía un proveedor concreto ni doy importes mensuales. Los
enlaces oficiales para comprobar planes, región, disco y transferencia son:

- [Precios de DigitalOcean Droplets](https://www.digitalocean.com/pricing/droplets)
- [Precios de Google Cloud Run](https://cloud.google.com/run/pricing)
- [Precios de Render](https://render.com/pricing)

Además del cómputo, calcula disco, transferencia de salida, dominio, copias de
seguridad y TLS administrado. El egreso puede dominar el costo: el servidor
recibe el video desde la fuente y luego lo envía al navegador. No contrates un
plan hasta revisar el precio de la región y sus cuotas de salida.

## PUBLICAR VIDEO DOWNLOADER WEB SIN INSTALAR NADA EN MI COMPUTADORA

Los pasos de terminal siguientes se ejecutan **en la consola web del servidor
remoto del proveedor**. No los ejecutes en tu computadora. Si el proveedor ofrece
un terminal de navegador, úsalo; también puedes elegir una imagen de servidor
que ya traiga Docker Engine y Compose v2.33.1 o posterior. No guardes secretos
en GitHub, en datos de inicialización de la VM ni en capturas compartidas.

### 1. Crear el host desde el navegador

1. En la consola web del proveedor, crea una VM Linux con recursos iniciales de
   al menos 2 vCPU, 4 GB de RAM y 40 GB de disco. Selecciona una región cercana a
   las personas que usarán el sitio.
2. En el firewall del proveedor, permite TCP 80 y 443 desde Internet. Restringe
   SSH a la dirección administrativa cuando sea posible. No abras los puertos
   8000 ni 3128.
3. Asocia un dominio o subdominio, por ejemplo `media.example.com`, a la IP del
   host desde el panel web de DNS.
4. Abre la consola web del host y confirma que están disponibles Docker Engine y
   Docker Compose v2.33.1 o posterior.

### 2. Obtener el código y crear secretos

Desde la consola web del servidor, clona la rama publicada:

```sh
sudo mkdir -p /opt/video-downloader
sudo chown "$USER" /opt/video-downloader
git clone --depth 1 --branch feat/google-sites-web \
  https://github.com/IsaacRenderos2109/Descargador-multimedia.git \
  /opt/video-downloader
cd /opt/video-downloader
python3 scripts/create_web_env.py
```

El script crea `.env` con `ACCESS_CODE` y `SESSION_SECRET` aleatorios y permisos
privados. No subas `.env` a GitHub. Edita ese archivo **en el host remoto** para
establecer estos valores con el dominio real:

```dotenv
PUBLIC_BASE_URL=https://media.example.com
COOKIE_SECURE=true
ALLOWED_HOSTS=media.example.com
GOOGLE_SITES_ORIGINS=https://sites.google.com
```

Si Google Sites usa un dominio personalizado, agrega su origen HTTPS a
`GOOGLE_SITES_ORIGINS`. Conserva el `MEDIA_PROXY` interno de Compose. Obtén
`ACCESS_CODE` desde la consola segura del host y guárdalo en un gestor de
contraseñas o compártelo con los usuarios autorizados por un canal privado; no
lo pegues en este chat ni en los logs de GitHub. `SESSION_SECRET` no debe
compartirse.

### 3. Configurar HTTPS sin exponer los puertos internos

Configura un proxy inverso en el host o usa el proxy HTTPS que ofrezca el
proveedor. Debe:

- terminar TLS y renovar certificados;
- reenviar a `http://127.0.0.1:8000`;
- reemplazar los encabezados `X-Forwarded-*` que reciba del cliente;
- conservar `Host` y marcar el protocolo original como HTTPS;
- limitar las solicitudes y no aceptar archivos de carga innecesarios.

`deploy/Caddyfile.example` muestra un ejemplo para Caddy ejecutado en el host.
No expongas el puerto 8000 ni publiques el puerto del proxy CONNECT. El
`compose.web.yml` mantiene el puerto de la aplicación ligado a loopback y no
publica el proxy.

En una VM, instala Caddy siguiendo la guía oficial correspondiente a la
distribución del host, desde la consola web remota. Copia el ejemplo a
`/etc/caddy/Caddyfile`, sustituye `media.example.com` por el dominio configurado
en DNS y recarga el servicio Caddy. El nombre debe resolver a la VM y el firewall
debe permitir los puertos 80/443 para que Caddy pueda emitir y renovar TLS.
Guía oficial: [instalar Caddy](https://caddyserver.com/docs/install).

### 4. Arrancar y comprobar desde la consola web

En la consola web del host remoto:

```sh
cd /opt/video-downloader
docker compose -f compose.web.yml config --quiet
docker compose -f compose.web.yml up --build -d
docker compose -f compose.web.yml ps
curl --fail http://127.0.0.1:8000/health
curl --fail https://media.example.com/health
```

Ambas comprobaciones deben responder `{"status":"ok"}`. Revisa en el panel
del proveedor el estado de los contenedores, uso de memoria, disco, CPU y tráfico.
Si la instancia se reinicia, la cola en memoria se pierde; el servicio borra la
carpeta de la instancia al cerrar de forma controlada y limpia carpetas antiguas
al iniciar. Conserva el volumen solo para permitir la limpieza por TTL; no lo
uses como almacenamiento permanente.

Para actualizar después de revisar el cambio en GitHub, vuelve a la consola web
del host:

```sh
cd /opt/video-downloader
git status --short
git fetch origin
git pull --ff-only origin feat/google-sites-web
docker compose -f compose.web.yml up --build -d
```

Si `git status --short` muestra cambios locales, detente y consérvalos antes de
actualizar. La actualización conserva `.env` y el volumen `web_jobs`; no uses
`docker compose ... down -v`.

### 5. Insertar en Google Sites

1. Abre Google Sites en el navegador y edita la página principal.
2. Selecciona **Insertar → Incorporar → Por URL**.
3. Pega `https://media.example.com/` y confirma la vista previa.
4. Publica el sitio y prueba el código de acceso, análisis, progreso y descarga.
5. Mantén también visible el enlace para abrir `https://media.example.com/` en
   otra pestaña. Las políticas del navegador pueden bloquear cookies de terceros
   dentro del iframe; la URL directa conserva la sesión en el origen del servicio.

El backend envía `Content-Security-Policy: frame-ancestors` para
`https://sites.google.com` y los orígenes configurados, omite
`X-Frame-Options` y usa cookie `SameSite=None; Secure` cuando HTTPS está activo.
Esto valida la configuración del servidor, no la inserción real en una cuenta
concreta de Google Sites. Esa prueba queda pendiente hasta que haya una URL
pública y acceso a la página publicada.

## Límites y operación

- Solo acepta enlaces HTTPS a videos públicos individuales, accesibles sin
  cuenta. No admite listas, emisiones en directo, contenido privado/no listado,
  DRM ni autenticación.
- Predeterminados: 100 MiB por archivo, trabajo de hasta 600 segundos, medios de
  hasta 30 minutos, una descarga simultánea, ocho tareas pendientes, hasta 1 GiB
  de almacenamiento temporal y borrado tras una hora.
- La aplicación hace cumplir `MAX_STORAGE_BYTES`, pero el volumen Docker no tiene
  una cuota física propia en todos los drivers. Configura alertas de disco en el
  proveedor y conserva margen en la VM.
- Cola, sesiones y límites de frecuencia viven en una instancia/proceso. No
  ejecutes varias réplicas ni balancees sesiones entre instancias sin rediseñar
  almacenamiento, cola y coordinación.
- El código de acceso es compartido. Rótalo si se filtra y limita quién puede
  verlo. No se conserva un historial permanente de URLs.

## Verificación antes de anunciar el servicio

Los tests locales y de CI usan mocks y medios sintéticos. Antes de anunciar una
URL de producción comprueba desde un navegador real la autenticación, `/health`,
cabeceras CSP/cookies, análisis de un enlace autorizado, una descarga autorizada,
el progreso/cancelación, la expiración de archivos y el uso en móvil. Después
prueba la misma URL incorporada en un Google Sites publicado y prueba el enlace
directo. Registra por separado las pruebas reales y simuladas. No publiques la
URL como disponible hasta que esas comprobaciones pasen.

El workflow de GitHub valida el código web, la configuración Compose y la imagen
Linux. No despliega servicios ni crea una URL pública. La aplicación web tampoco
requiere una instalación en el dispositivo de quien la usa.
