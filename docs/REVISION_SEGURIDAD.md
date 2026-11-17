# Revisión de seguridad

Fecha: 16 de noviembre de 2026. Alcance: código local, dependencias y configuración de despliegue directo. No equivale a una prueba de penetración ni certifica un servidor todavía sin configurar.

## Cambios aplicados

- Acceso de producción protegido mediante autenticación Nginx, con hashes bcrypt externos al código y sin contraseñas predeterminadas. Authorization no se reenvía al backend. El desarrollo local continúa funcionando sin autenticación.
- Cabeceras CSP, nosniff, Referrer-Policy, Permissions-Policy y SAMEORIGIN incluidas también en las rutas que redefinen cabeceras. HSTS en HTTPS y respuestas privadas sin caché.
- Rechazo de macros, objetos, relaciones externas, conexiones, query tables, hojas macro y fórmulas activas como WEBSERVICE, HYPERLINK, RTD, IMAGE y DDE. El servidor no evalúa fórmulas; se controla también el contenido que podría activar Excel al abrir la descarga.
- Validación adicional de rutas ZIP ambiguas, además de los límites de entradas, expansión, XML, filas y celdas. XML endurecido contra entidades y lectura multipart incremental sin UploadFile ni almacenamiento de planillas.
- Rechazo de Origin ajeno y Fetch Metadata cross-site. La autenticación es independiente de esa comprobación.
- Producción exige APP_ENV=production y un PUBLIC_ORIGIN HTTPS sin rutas ni credenciales; el servicio obtiene estas variables desde /etc/procontel/app.env.
- Servicio systemd como usuario sin privilegios, código de solo lectura, directorio temporal privado, sin core dumps y con límites de memoria, CPU y procesos. API enlazada exclusivamente a 127.0.0.1.
- Límites de solicitudes, conexiones y tiempos en Nginx. Buffering de API y registros de acceso desactivados. Los errores API no exponen trazas internas ni contraseñas.
- Archivos de secretos excluidos del repositorio. Datos Excel insertados en boletas como texto, texto PDF escapado y contenido React interpolado sin HTML arbitrario.

## Verificación local

- npm audit: cero vulnerabilidades conocidas reportadas en las dependencias instaladas.
- pip-audit: ninguna vulnerabilidad conocida reportada en el entorno Python local. Resultado técnico en tmp/security-python-audit.json, excluido del repositorio.
- Ruff, mypy y pruebas backend para carga, ZIP/XML peligroso, contenido activo, límites, selección y exportaciones.
- Pruebas de navegador para selección, revisión, bloqueo de descargas y formatos de exportación, en escritorio y móvil.

El resultado de una auditoría de dependencias depende de los avisos conocidos en la fecha de consulta. Repetirla al actualizar o desplegar. También actualizar y revisar Python, Node, Nginx y el sistema operativo del servidor.

## Pendiente en el servidor

Seguir [despliegue directo](../deploy/README.md): instalar dependencias, fijar el dominio, emitir certificado, crear usuarios, instalar servicio y configurar Nginx. Ejecutar nginx -t, comprobar el servicio y correr scripts/verify_production.py. Probar después una planilla sintética desde el navegador.

No se verificaron en este equipo los servicios Linux/systemd ni Nginx real, los certificados del dominio, firewall, puertos externos, permisos efectivos del servidor, reinicio ni carga concurrente. No se dispone del entorno de producción. El despliegue debe superar esas comprobaciones antes de exponerse a usuarios.

Si se utiliza un proxy corporativo adicional, conservar los controles de acceso y evitar acceso directo al backend. Configurar límites por IP real únicamente confiando en los proxies conocidos, no en cabeceras aportadas por cualquier cliente. Proteger swap, temporales, monitorización y respaldos del servidor; no registrar cuerpos ni Authorization.

## Límites funcionales y de acceso

- Los usuarios autorizados acceden a la herramienta completa. Basic Auth no proporciona roles, MFA ni cierre de sesión fiable en todos los navegadores. Para acceso corporativo amplio, utilizar el SSO/MFA de la organización y cuentas individuales.
- El Excel/ZIP contiene la planilla original completa, incluidos empleados no seleccionados. Compartirlo exclusivamente con personal autorizado a ver todos esos datos. Entregar a cada colaborador únicamente su PDF individual.
- La app usa el líquido y los importes originales y trata IVA vacío como cero por requisito funcional. No certifica la conciliación ni sustituye la revisión de RRHH.
- La aplicación no conserva planillas para recuperarlas; las descargas y el navegador sí contienen datos personales y deben protegerse en el equipo del usuario.

Referencias: [NGINX Basic Auth](https://nginx.org/en/docs/http/ngx_http_auth_basic_module.html), [herencia de cabeceras NGINX](https://nginx.org/en/docs/http/ngx_http_headers_module.html), [OWASP: carga de archivos](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html).
