# Publicar el servicio web

El servicio web es opcional. La aplicación de escritorio sigue siendo el producto
existente y usa su flujo de instalación habitual. El backend web corre en Linux
con Docker Compose; Google Sites solo muestra el sitio remoto en un marco o abre
su URL en otra pestaña.

## Requisitos

- Un host Linux con Docker Engine y Docker Compose v2.33.1 o posterior.
- Un dominio propio y un proxy inverso que termine TLS, como Caddy, Nginx o el
  proxy que ofrezca el proveedor.
- Salida HTTPS al proxy `egress-proxy` para consultar YouTube y recibir medios.
- Espacio y transferencia suficientes para archivos temporales de hasta 100 MiB.

El servicio escucha en `127.0.0.1:8000` del host. No publiques el puerto 8000
directamente a Internet. Configura el proxy inverso para enviar HTTPS a esa
dirección y conserva los encabezados `Host` y `X-Forwarded-Proto`. El proxy
inverso debe aplicar límites razonables de solicitudes y tamaño de respuesta.
Compose confía en las cabeceras `X-Forwarded-*` porque el puerto solo se publica
en la interfaz loopback del host. Mantén esa vinculación y configura el proxy
inverso para reemplazar las cabeceras reenviadas recibidas del cliente.

## Preparar el host

Desde la raíz de este repositorio:

```sh
python3 scripts/create_web_env.py
```

El script genera `.env` con un código de acceso y una clave de sesión aleatorios,
no imprime sus valores y se niega a reemplazar un `.env` ya existente. El archivo
está ignorado por Git. Guarda el código de acceso por un canal privado.

Edita `.env` antes de iniciar el servicio:

```dotenv
PUBLIC_BASE_URL=https://media.example.com
COOKIE_SECURE=true
ALLOWED_HOSTS=media.example.com
GOOGLE_SITES_ORIGINS=https://sites.google.com
```

Si el sitio de Google Sites usa un dominio personalizado, añade también su origen
HTTPS a `GOOGLE_SITES_ORIGINS`, separado por comas. Usa solo el origen (esquema y
dominio, sin ruta). No cambies `MEDIA_PROXY` a una dirección pública: Compose lo
fija al proxy interno. El `.env.example` tiene valores para desarrollo local.

Construye y arranca:

```sh
docker compose -f compose.web.yml config --quiet
docker compose -f compose.web.yml up --build -d
docker compose -f compose.web.yml ps
curl --fail http://127.0.0.1:8000/health
```

El resultado esperado del health check es `{"status":"ok"}`. Comprueba también
que el proxy TLS pueda cargar `https://media.example.com/` y que el navegador
muestre el formulario de acceso. No compartas el código salvo con las personas
autorizadas.

Para actualizar una imagen después de revisar cambios:

```sh
git fetch origin
git switch feat/google-sites-web
git pull --ff-only origin feat/google-sites-web
docker compose -f compose.web.yml up --build -d
```

Para parar el servicio, usa `docker compose -f compose.web.yml down`. El volumen
`web_jobs` conserva datos temporales entre reinicios, pero el estado de las tareas
está en memoria y se pierde al reiniciar. `docker compose ... down -v` también
borra el volumen de archivos temporales.

## Google Sites

1. En Google Sites, abre **Insertar → Incorporar → Por URL**.
2. Pega `https://media.example.com/` y confirma la vista previa.
3. Publica el sitio y prueba el inicio de sesión dentro de la página publicada.
4. Si el navegador bloquea cookies de terceros o la integración, deja visible el
   enlace **Abrir en una pestaña nueva** del servicio y comparte esa URL directa.

El backend envía `Content-Security-Policy: frame-ancestors` para `sites.google.com`
y los orígenes configurados, y omite `X-Frame-Options`. La aplicación usa una
cookie `SameSite=None; Secure` cuando está publicada con HTTPS. Aun así, las
políticas del navegador sobre cookies insertadas pueden variar; el enlace directo
es la alternativa compatible. Antes de desplegar no se puede confirmar desde este
repositorio que una cuenta concreta de Google Sites acepte una URL o que su
navegador permita esas cookies.

## Límites del servicio

- Solo enlaces HTTPS a videos individuales, públicos y accesibles sin cuenta.
- Hasta 20 enlaces por envío; no se procesan listas, emisiones en directo ni
  contenido privado, no listado, con DRM o que requiera autenticación.
- Salida MP4 a una altura disponible o audio MP3; FFmpeg y FFprobe vienen en la
  imagen Docker, igual que un runtime Node compatible con yt-dlp.
- Predeterminados: archivo de hasta 100 MiB, trabajo de hasta 600 segundos,
  duración de medio de hasta 30 minutos, un trabajo concurrente, ocho trabajos
  pendientes, almacenamiento temporal de hasta 1 GiB y borrado de archivos
  después de una hora.
- Los archivos y el historial de trabajo viven en memoria/almacenamiento temporal.
  Un reinicio pierde el historial y elimina los trabajos de la instancia activa.
- La cola e historial son locales a un único proceso; no escales a varias réplicas
  sin añadir coordinación y almacenamiento compartido.

Estos topes se ajustan mediante variables documentadas en `.env.example`, dentro
de los rangos validados en `web_service/config.py`. El límite de disco del host
debe ser mayor que la concurrencia multiplicada por el tamaño temporal permitido.

## Costes y límites de hosting

Google Sites puede ofrecerse sin un cargo adicional en cuentas personales; las
funciones de Workspace dependen del plan de la organización. La aplicación web no
se aloja dentro de Google Sites: el backend necesita un host Linux independiente.

Un Docker Compose en un equipo propio no añade una factura de hosting, aunque sí
consume electricidad, conexión y transferencia. En una nube/VPS suelen cobrarse
el cómputo continuo, el disco, la transferencia de salida, el dominio y, según el
proveedor, las copias de seguridad o el proxy TLS. El tráfico de video puede ser
el coste dominante porque el backend descarga el medio y luego lo sirve al
navegador. Los planes gratuitos suelen dormir, limitar transferencia o detener
procesos largos; valida sus condiciones antes de confiarles descargas de hasta
600 segundos. Los precios y cuotas cambian por proveedor y región, así que consulta
la calculadora vigente del proveedor que elijas antes de publicar.

El servicio no se ha desplegado ni probado con una descarga real. La publicación
del código y la aprobación del PR no crean por sí mismas un host público.
