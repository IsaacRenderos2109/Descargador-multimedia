# Seguridad del backend web

- El acceso requiere un código aleatorio y crea una sesión firmada, aislada por
  navegador y expirada. Se limita la frecuencia de login y de creación de tareas.
- Todas las operaciones que cambian estado comprueban `Origin`; el backend usa
  `TrustedHostMiddleware`, CSP y cookies `HttpOnly`.
- Las URLs se validan con el validador existente del escritorio, se requieren
  esquemas HTTPS y se rechazan listas. Los formatos se obtienen de yt-dlp; el
  worker vuelve a validar el identificador y la URL antes de descargar.
- La aplicación solo comparte una red Docker interna con un proxy CONNECT. Ese
  proxy permite destinos de YouTube/Google Video, resuelve el hostname, rechaza
  IP privadas/no globales y conecta a la dirección resuelta. El contenedor web no
  tiene una ruta de salida directa.
- yt-dlp no recibe cookies ni credenciales, no activa formatos DRM y no intenta
  evadir autenticación, geobloqueos u otras restricciones de acceso.
- Cada trabajo corre en un proceso separado con límite de tiempo, CPU y tamaño;
  se cancelan también sus procesos secundarios. La app valida eventos, rutas y
  tamaños de archivos antes de servirlos.
- El contenedor corre sin root, con sistema de archivos de solo lectura, sin
  capacidades Linux, sin privilegios nuevos y con límites básicos de memoria,
  CPU y procesos.
- Los archivos temporales se aíslan por sesión y caducan. No se guardan URLs,
  cookies del navegador, credenciales de YouTube ni un historial permanente.

Las restricciones de frecuencia y cola se mantienen en memoria y se aplican por
instancia. Sitúa el servicio tras TLS y un proxy inverso, no expongas el puerto
interno ni el proxy de salida, protege el `.env`, revisa logs del host y limita el
acceso al código de entrada. Una declaración de autorización en la interfaz es
responsabilidad del usuario; no verifica derechos de autor automáticamente.
