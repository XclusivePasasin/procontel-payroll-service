# Procontel · Generador de boletas

React/TypeScript y FastAPI para leer planillas Excel, seleccionar empleados y descargar boletas en PDF o en el Excel original. Los datos fuente no se editan.

## Desarrollo local

Requisitos: Python 3.12+, uv, Node 24 y npm. Desde la raíz:

```powershell
uv sync --project backend --frozen
cd backend
$env:PUBLIC_ORIGIN = "http://127.0.0.1:5173"
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

En otra terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Abrir http://127.0.0.1:5173. El modo local no utiliza credenciales de producción.

## Uso

1. Cargar un archivo `.xlsx` y analizarlo.
2. Seleccionar las boletas, agrupadas por área. Todas se seleccionan inicialmente.
3. Elegir el período común y pulsar **Revisar boletas**.
4. Descargar PDF, Excel o todo en ZIP. Cambiar fechas o empleados bloquea las descargas hasta revisar de nuevo.

PDF y Excel imprimen dos boletas lado a lado en hoja carta horizontal, con separación para corte y espacio para firmas. La última página contiene solamente los empleados restantes.

Se reconocen PLANILLA y HONORARIOS, también con sufijos como FIBRA, MASIVOS y COMERCIAL. Cada hoja de boletas queda inmediatamente después de su origen. El nombre es `BOLETAS DE PAGO {origen}` cuando cabe en 31 caracteres, o `BOLETAS {origen}` con abreviación estable si hace falta.

El ID de empleado es opcional y queda vacío cuando falta; la selección distingue hoja y fila. El IVA vacío se utiliza como cero. Se conservan los importes y el líquido guardados en Excel, sin bloquear por conciliación ni agregar ajustes. La revisión financiera corresponde a RRHH.

**El Excel descargado conserva todas las hojas y todos los empleados originales**, aunque se seleccione una sola boleta. Para entregar a un colaborador, compartir solamente su PDF individual.

## Producción

Consultar [despliegue directo](deploy/README.md) y [revisión de seguridad](docs/REVISION_SEGURIDAD.md). Se incluye servicio systemd y configuración Nginx para Linux; el backend escucha únicamente en loopback. El despliegue exige HTTPS y usuarios autorizados. No requiere contenedores.

## Arquitectura

- Backend: carga incremental en RAM, inspección OOXML, perfiles explícitos, selección por hoja/fila/código, Decimal y generación compartida PDF/Excel. Un proceso descartable por solicitud, con límite de concurrencia y timeout.
- Exportación: parchea únicamente las hojas de boletas y metadatos necesarios del paquete original; conserva fórmulas y cachés fuente sin ejecutarlas.
- Frontend: componentes React, estado en memoria, selección por área y calendarios shadcn. No hay editor de planillas, buscador ni almacenamiento de empleados en localStorage.
- API: POST `/api/v1/analyze`, `/review`, `/preview`, `/generate`; multipart con archivo y opciones JSON. GET `/healthz` para comprobación local. La API reconstruye los datos desde el archivo en cada solicitud.

Límites: carga de 10 MiB, ZIP expandido de 100 MiB, 2.000 entradas, XML de 16 MiB, 1.200 filas por hoja, 100.000 celdas y 1.000 personas por tipo. Dos solicitudes concurrentes y 60 segundos de timeout. Se rechazan macros, enlaces/conexiones externas, fórmulas activas y XML peligroso. No se admiten archivos con macros.

## Verificación

```powershell
uv run --project backend ruff check backend scripts
uv run --project backend mypy backend/app
uv run --project backend pytest backend/tests -q
uv run --project backend pip-audit
cd frontend
npm run lint
npm run format:check
npm run build
npm audit
npm run test:e2e
```

Las pruebas utilizan datos sintéticos. Dependencias fijadas en `backend/uv.lock` y `frontend/package-lock.json`. No agregar planillas, PDFs reales, contraseñas ni secretos al repositorio. Los artefactos locales de comprobación quedan en `tmp/`, ignorado por Git.
