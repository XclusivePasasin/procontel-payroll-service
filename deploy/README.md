# Despliegue directo

La configuración incluida es para un servidor Linux con systemd y Nginx. La app se ejecuta como un proceso Python y Nginx publica el frontend compilado. No hay dependencia de contenedores. En Windows se mantiene el desarrollo local indicado en el README principal; para un servidor Windows se debe adaptar el gestor del servicio y el proxy.

## Preparación

Instalar Python 3.12 o superior del sistema, uv, Node 24, Nginx y `apache2-utils` (`htpasswd`). Copiar el proyecto a `/opt/procontel`; no copiar `node_modules`, `.venv`, `tmp`, archivos de empleados ni secretos del equipo de desarrollo.

Desde `/opt/procontel`:

```bash
uv sync --project backend --frozen --no-dev --python /usr/bin/python3
npm --prefix frontend ci
npm --prefix frontend run build
sudo useradd --system --no-create-home --shell /usr/sbin/nologin procontel
sudo install -d -m 750 -o root -g www-data /etc/procontel
sudo install -m 600 .env.example /etc/procontel/app.env
```

Editar `/etc/procontel/app.env`: usar el dominio HTTPS real en PUBLIC_ORIGIN y mantener APP_ENV=production. El backend no carga `.env` por sí solo: systemd lee este archivo. El intérprete debe estar instalado en una ruta del sistema accesible para el usuario del servicio; no usar un Python ubicado en `/root` o en un directorio personal protegido.

El código y el entorno Python deben ser legibles por `procontel`, sin concederle permisos de escritura. `frontend/dist` debe ser legible por Nginx. Adaptar el grupo `www-data` si la distribución utiliza `nginx`.

## Usuarios autorizados

```bash
sudo htpasswd -cB /etc/procontel/payroll.htpasswd rrhh
sudo chown root:www-data /etc/procontel/payroll.htpasswd
sudo chmod 640 /etc/procontel/payroll.htpasswd
```

La contraseña se solicita de forma oculta; usar al menos 16 caracteres. Para usuarios adicionales omitir `-c`, que recrearía el archivo. No pasar contraseñas como argumentos ni guardar usuarios reales en el repositorio. `scripts/create_access.py` es una alternativa para generar un archivo local de forma interactiva; después instalarlo en la ruta de producción con los permisos anteriores.

## Servicio y HTTPS

```bash
sudo install -m 644 deploy/procontel.service /etc/systemd/system/procontel.service
sudo systemctl daemon-reload
sudo systemctl enable --now procontel
curl --fail http://127.0.0.1:8000/healthz
```

Obtener un certificado válido para el dominio mediante el proveedor/ACME utilizado en el servidor. Antes de habilitar Nginx, cambiar el dominio y las rutas de certificados en `deploy/nginx/procontel.conf`.

```bash
sudo install -m 644 deploy/nginx/security-headers.conf /etc/nginx/snippets/procontel-security.conf
sudo install -m 644 deploy/nginx/procontel.conf /etc/nginx/sites-available/procontel
sudo ln -s /etc/nginx/sites-available/procontel /etc/nginx/sites-enabled/procontel
sudo nginx -t
sudo systemctl reload nginx
```

La ruta `sites-enabled` corresponde a Debian/Ubuntu; adaptar a `conf.d` en otras distribuciones. No sustituir la configuración global del servidor ni desactivar otros sitios. La configuración incluye redirección HTTP→HTTPS, autenticación, cabeceras, límites de solicitudes y proxy sin buffering. Si ya hay un proxy corporativo, integrar esos controles en el proxy existente, evitando una publicación paralela del backend.

Permitir externamente únicamente los puertos necesarios para HTTPS y su redirección HTTP. Uvicorn escucha en 127.0.0.1:8000. No publicar 8000 ni 5173. No registrar cuerpos de solicitudes ni Authorization en el proxy o en herramientas de monitorización.

## Comprobación

```bash
export PUBLIC_ORIGIN=https://tu-dominio-real
python3 scripts/verify_production.py
```

Además, probar carga, selección, calendarios, PDF y Excel con una planilla sintética desde el navegador. Verificar que el acceso anónimo recibe 401 y que 8000 no es accesible desde otra máquina. Medir memoria y concurrencia con la carga prevista. Configurar actualizaciones de seguridad y respaldar únicamente configuración y credenciales de forma protegida.

Para actualizar: sincronizar dependencias con los locks, compilar el frontend, repetir las verificaciones y reiniciar `procontel`. No limpiar ni mover carpetas de otras aplicaciones. Las descargas siguen bajo control del usuario; no existe un repositorio de planillas en el servidor.
