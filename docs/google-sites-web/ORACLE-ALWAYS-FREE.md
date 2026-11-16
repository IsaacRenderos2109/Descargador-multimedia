# Preparación para Oracle Cloud Always Free (A1 ARM64)

## Estado: preparado; despliegue detenido por falta de verificación de costo

No se creó una cuenta, una instancia, un volumen, una IP pública, un presupuesto
ni ningún otro recurso de Oracle. Tampoco se desplegó la aplicación y no hay una
URL pública.

En esta revisión, Codex no tiene identidad ni credenciales OCI. La política de
red activa permite api.github.com, pero no los sitios oficiales de Oracle o
DuckDNS; las consultas a esos sitios respondieron 403. Hay un borrador que
propone agregarlos para revisión, pero no se aplica hasta que el propietario lo
publique y se inicie un entorno con esa configuración. No pude confirmar cuotas,
capacidad regional, requisito de tarjeta ni precios actuales de IPv4,
almacenamiento, transferencia o DuckDNS.

**No crees recursos mientras alguno de esos datos sea desconocido.** No cambies
la cuenta a Pay As You Go ni uses créditos promocionales. Si Oracle pide una
tarjeta, una actualización de cuenta o muestra un cargo distinto de USD 0,
detente. Si A1 no tiene capacidad Always Free en la región de inicio, detente;
no elijas una shape pagada.

## Auditoría ARM64

| Componente | Resultado comprobado | Límite de la comprobación |
| --- | --- | --- |
| Python 3.12.14 slim Bookworm | Docker publica linux/arm64/v8. | No se ejecutó en hardware ARM durante esta revisión. |
| Node 26.13.1 Bookworm slim | Docker publica linux/arm64/v8; la etapa solo copia /usr/local/bin/node. | La ejecución ARM64 en la imagen final no se comprobó en A1. |
| yt-dlp y yt-dlp-ejs | Paquetes Python; la resolución multiplataforma terminó correctamente. | No se hizo una descarga real. |
| Dependencias Python | pip descargó todas las wheels fijadas para CPython 3.12/AArch64, incluidas pydantic-core, pycryptodomex, brotli y websockets. | Comprueba que existen artefactos AArch64, no que la app corra en Oracle. |
| FFmpeg y FFprobe | Se instalan con apt desde Debian Bookworm; los paquetes Debian tienen arquitectura ARM64. | apt install ARM64 no se ejecutó localmente. |
| SQLite | Usa sqlite3 de la biblioteca estándar, sin una base administrada. | No se validó _sqlite3 dentro de una imagen A1 real. |
| Proxy CONNECT | Python estándar; no usa binarios x86 ni módulos Qt. | El build ARM64 completo necesita un worker ARM64 o emulación QEMU. |
| Caddy | La imagen oficial caddy:2-alpine ofrece linux/arm64/v8; el manifiesto observado era 2.11.9. | La guía instala Caddy en el host; no se ejecutó en Oracle. |

El Docker Builder de Codex solo anuncia linux/amd64. El intento de compilar
linux/arm64/v8 terminó con exec format error al ejecutar /bin/sh de la imagen
ARM64. Es una limitación de emulación del builder, no una incompatibilidad
demostrada del Dockerfile. El workflow añade una compilación ARM64 con QEMU en
GitHub Actions; esta tampoco equivale a ejecutar el servicio en una VM A1 real.

compose.oracle-a1.yml selecciona ARM64 y limita el backend y el proxy a 2 CPU
en conjunto (1.5 y 0.5). Se combina con compose.web.yml y conserva aislamiento
de red, autenticación, límites de memoria/procesos/CPU, proxy de salida,
almacenamiento temporal y limpieza. El named volume web_jobs reside en el disco
de arranque de la VM; no requiere un volumen de bloque OCI. No se agregan bases
administradas ni balanceadores.

## Reglas de costo antes de crear una VM

Las condiciones de Always Free pueden cambiar. En la consola OCI de la cuenta
existente, revisa cada punto en la región de inicio:

1. La cuenta sigue en Free Tier y no ofrece ni requiere actualizar a Pay As You
   Go. No introduzcas una tarjeta para superar este control.
2. Hay una imagen Linux ARM64 y la shape aparece explícitamente como Always Free
   eligible para esta cuenta y región.
3. Ampere A1 tiene cuota y capacidad disponibles. Una estimación de shape no
   garantiza que haya capacidad en un host.
4. Candidata: A1 Flex de 2 OCPU y 12 GB de RAM, solo si la consola confirma que
   cabe dentro de la cuota gratuita actual. Usa una asignación menor si se
   necesita y comprueba que los contenedores sigan cabiendo.
5. El disco de arranque, IP pública dinámica, red, transferencia y cada servicio
   auxiliar deben indicar USD 0 y estar incluidos en el nivel gratuito actual.
   No agregues volumen de bloques, IP reservada, backups pagados, balanceador
   ni otra shape.
6. DuckDNS permite registrar y actualizar el subdominio sin plan, tarjeta ni
   renovación de pago. Si no puedes comprobar costo cero, no lo uses.
7. El costo no puede depender de créditos promocionales temporales.

IPv4 pública, discos, egreso y capacidad regional pueden tener reglas y cuotas
propias. **Un presupuesto que envía alertas no es un tope y no garantiza USD 0.**
Como no se pudo consultar la consola y no hay identidad OCI en este entorno,
estos controles siguen sin verificar. No crear recursos es el único resultado
que hoy se puede confirmar bajo el presupuesto estricto.

## Procedimiento condicionado, desde navegador

Ejecuta estos pasos solo después de pasar todos los controles de costo. No hace
falta instalar programas en Windows ni en otro dispositivo local.

### A. Crear una instancia candidata

1. Abre la consola web de Oracle y selecciona la región de inicio. Revisa uso,
   cuotas y capacidad de Ampere A1.
2. Abre Compute → Instances → Create instance. Elige Linux ARM64 y A1 Flex de
   2 OCPU/12 GB, o un tamaño menor que el panel marque Always Free eligible.
3. Revisa por separado el costo de shape, disco, IP pública, red y transferencia.
   Si no ves USD 0 explícito para cada concepto, cancela; no pulses Create.
4. Usa solo el disco de arranque incluido en el costo cero. No agregues block
   volumes, backups, load balancers ni IP reservadas.
5. Configura una subnet pública solo si la consola confirma costo cero para la
   red y la IPv4 dinámica. Permite TCP 80/443 y limita SSH a una IP
   administrativa. No abras 8000 ni 3128. Si no hay consola remota en navegador,
   detente en vez de instalar herramientas localmente.
6. Usa la consola/Cloud Shell de Oracle para conectar. Si exige actualizar la
   cuenta o contratar algo, detente. Todo comando debe ejecutarse en el terminal
   remoto, nunca en el equipo del usuario.

### B. Instalar la app en el servidor remoto

Instala Docker Engine y Compose v2.33.1 o posterior siguiendo la guía oficial
actual para la distribución ARM64 que se haya verificado como gratuita. Clona
la rama publicada y prepara credenciales solo en la VM:

    sudo mkdir -p /opt/video-downloader
    sudo chown "$USER" /opt/video-downloader
    git clone --depth 1 --branch feat/oracle-always-free-arm64 https://github.com/IsaacRenderos2109/Descargador-multimedia.git /opt/video-downloader
    cd /opt/video-downloader
    python3 scripts/create_web_env.py
    docker compose -f compose.web.yml -f compose.oracle-a1.yml config --quiet
    docker compose -f compose.web.yml -f compose.oracle-a1.yml build

No pongas .env en GitHub, en el historial de Cloud Shell, capturas o logs.
Edita .env en el terminal remoto y establece estos valores:

    PUBLIC_BASE_URL=https://[subdominio].duckdns.org
    COOKIE_SECURE=true
    ALLOWED_HOSTS=[subdominio].duckdns.org
    GOOGLE_SITES_ORIGINS=https://sites.google.com

Conserva el MEDIA_PROXY interno de Compose. No compartas ACCESS_CODE ni
SESSION_SECRET; entrega el código de acceso a usuarios autorizados por un canal
privado.

### C. DuckDNS y Caddy

1. Registra un subdominio DuckDNS. Si solicita tarjeta, plan o cargo, cancela.
2. Crea un usuario de sistema y un archivo fuera del repositorio:

    sudo useradd --system --no-create-home --shell /usr/sbin/nologin duckdns
    sudo install -d -o root -g duckdns -m 0750 /etc/video-downloader
    sudoedit /etc/video-downloader/duckdns.env

El archivo debe contener DUCKDNS_DOMAIN=[solo-el-prefijo] y
DUCKDNS_TOKEN=[token]. Guarda y cierra el editor. Después ejecuta:

    sudo chown root:duckdns /etc/video-downloader/duckdns.env
    sudo chmod 0640 /etc/video-downloader/duckdns.env

No pegues el token en un comando ni en el chat.

3. Instala las unidades y activa el actualizador:

    sudo install -m 0644 deploy/oracle/duckdns-update.service /etc/systemd/system/
    sudo install -m 0644 deploy/oracle/duckdns-update.timer /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable --now duckdns-update.timer
    sudo systemctl start duckdns-update.service
    sudo systemctl status duckdns-update.service --no-pager

La unidad no imprime el token en logs ni en argumentos del proceso; actualiza el
registro periódicamente.

4. Instala Caddy en el host con sus instrucciones oficiales ARM64 para la
   distribución seleccionada. Copia deploy/oracle/Caddyfile a
   /etc/caddy/Caddyfile y cambia replace-me.duckdns.org por el nombre real.
   Permite TCP 80/443; Caddy los usa para HTTPS automático. Ejecuta
   sudo systemctl reload caddy y verifica sudo systemctl status caddy.

5. Arranca y revisa los contenedores:

    cd /opt/video-downloader
    docker compose -f compose.web.yml -f compose.oracle-a1.yml up -d
    docker compose -f compose.web.yml -f compose.oracle-a1.yml ps
    curl --fail http://127.0.0.1:8000/health
    curl --fail https://[subdominio].duckdns.org/health

Si algo falla, revisa journalctl -u caddy y
docker compose -f compose.web.yml -f compose.oracle-a1.yml logs --tail=100.
No compartas .env, el archivo DuckDNS ni logs que puedan revelar credenciales.

### D. Alertas y control de costo

Antes de iniciar la app, revisa cuotas, uso y panel de costos. Si la consola
permite crear alertas sin cambiar el tipo de cuenta ni activar un servicio
pagado, configura avisos de cualquier costo distinto de cero y revisa Usage/Cost
Analysis cada semana. Las alertas informan; pueden llegar después de consumir.
Si no existe una barrera para mantener la cuenta Free Tier y bloquear cualquier
recurso pagado, el presupuesto estricto no se puede garantizar: no continúes.

Mantén una sola instancia. Vigila CPU, memoria, disco de arranque, web_jobs y
tráfico saliente. La app limita temporales a 1 GiB, pero el named volume comparte
el disco de arranque y no es una cuota de disco independiente. No crees backups,
volúmenes ni instancias adicionales. Al dejar de usar el servicio, detén los
contenedores y elimina los recursos solo después de confirmar que nada puede
seguir generando cargos; revisa Cost Analysis después.

## Google Sites

Solo después de pasar los health checks HTTPS:

1. Edita el Google Site desde el navegador.
2. Elige Insertar → Incorporar → Por URL y pega
   https://[subdominio].duckdns.org/.
3. Publica el Site y prueba autenticación, análisis, progreso y descarga desde
   escritorio y móvil.
4. Añade un enlace visible “Abrir Video Downloader” a la misma URL HTTPS para
   navegadores que limiten cookies dentro de iframes.

El backend configura frame-ancestors mediante GOOGLE_SITES_ORIGINS y cookies
Secure cuando COOKIE_SECURE=true. No se ha probado la inserción en Google Sites:
todavía no existe URL desplegada.

## Límites y estado comprobado

- No se evaden DRM, autenticación ni restricciones de plataforma. Usa solo
  contenido autorizado.
- Las pruebas usan mocks y medios sintéticos; no hubo descargas reales.
- El build ARM64 local no corrió por falta de QEMU. La CI lo compila con QEMU,
  pero la verificación final requiere una ejecución real en A1 y sigue detenida
  por las condiciones de cuenta y costo no verificables desde este entorno.

## Fuentes oficiales para confirmar antes de continuar

Los sitios siguientes no pudieron consultarse desde este entorno; sus precios,
disponibilidad y procedimientos deben verificarse en el navegador al momento de
usar la cuenta:

- [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/)
- [Oracle OCI Free Tier FAQ](https://www.oracle.com/cloud/free/faq/)
- [Oracle OCI Free Tier services](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm)
- [Oracle OCI pricing](https://www.oracle.com/cloud/price-list/)
- [DuckDNS](https://www.duckdns.org/)
- [Caddy: instalación para Debian/Ubuntu](https://caddyserver.com/docs/install#debian-ubuntu-raspbian)
- [Docker Engine: instalación para Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
