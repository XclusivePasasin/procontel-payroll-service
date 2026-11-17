Especificación implementable: generador de boletas Procontel

Versión 1.2 · 16 de noviembre de 2026 · Incluye edición, estándares de ingeniería y rol integral del agente

## 0. Instrucciones obligatorias para el agente implementador

Actúa como un único agente integral responsable de entregar la solución completa, combinando el criterio de un arquitecto de software senior, especialista senior en Python/FastAPI y React/TypeScript, diseñador UI/UX, analista de procesos de RRHH y especialista en seguridad de aplicaciones. Conecta las decisiones con el trabajo real de RRHH: reducir errores, evitar doble digitación, proteger información salarial y emitir boletas comprensibles y conciliadas. El conocimiento de RRHH orienta el flujo; no autoriza inventar políticas laborales, fórmulas fiscales ni decisiones contables.

El resultado debe ser código de producción limpio, ordenado, modular y mantenible. Estas obligaciones forman parte de los criterios de aceptación, no son recomendaciones opcionales:

### Código limpio y arquitectura

- Aplicar Clean Code, separación de responsabilidades, principios SOLID cuando aporten claridad y composición sobre abstracciones innecesarias. Evitar sobreingeniería, duplicación, funciones extensas y componentes que mezclen procesamiento, presentación y acceso HTTP.
- Mantener extracción Excel, reglas de negocio, correcciones, conciliación, render PDF, ZIP y transporte HTTP en módulos independientes. En React separar componentes visuales, estado del flujo, validaciones y cliente API.
- Usar nombres descriptivos, tipos explícitos en los límites y contratos de datos coherentes. Python con anotaciones de tipos y modelos Pydantic; TypeScript en modo estricto, sin `any` injustificado. Diferenciar importes, cantidades e identificadores.
- Centralizar mapas de columnas, límites, mensajes y configuración; evitar índices mágicos, secretos y rutas del entorno incrustados en código. Comentar decisiones no evidentes, sin repetir lo que expresa el código.
- Tratar errores de forma explícita y uniforme. No ocultar excepciones con respuestas exitosas, valores cero por defecto o bloques catch genéricos que impidan diagnosticar fallos.
- Usar formato y análisis estático automatizados: Ruff y comprobación de tipos para Python; ESLint, comprobación TypeScript y formateador para frontend. Definir comandos reproducibles y ejecutarlos antes de entregar.
- Mantener dependencias mínimas, versiones fijadas, archivos de bloqueo y documentación de ejecución. No incorporar código de ejemplo, archivos temporales, nóminas reales ni módulos sin uso al entregable.

### Seguridad y privacidad desde el diseño

- Aplicar validación de entradas en servidor y mínimo privilegio en despliegue. Ninguna validación o confirmación del navegador sustituye la comprobación del backend.
- Cumplir los controles de carga, límites, aislamiento, memoria, logs y no persistencia de la sección 12. Tratar Excel y valores de celdas como entrada no confiable. No ejecutar contenido del archivo ni permitir acceso a recursos externos.
- Prevenir inyección en HTML, rutas, cabeceras y PDF mediante APIs seguras, escape cuando corresponda y nombres generados por el servicio. No usar `dangerouslySetInnerHTML` con datos de usuario ni construir comandos de sistema desde el archivo.
- Proteger transporte con HTTPS, configurar orígenes y cabeceras de seguridad, aplicar límites de concurrencia y solicitudes, y mantener dependencias revisadas. No añadir login, base de datos ni telemetría salarial para resolver controles que deben implementarse en red e infraestructura.
- Verificar vulnerabilidades de dependencias y resolver hallazgos explotables antes de producción; documentar con precisión cualquier limitación pendiente. Nunca afirmar seguridad absoluta o cumplimiento normativo sin evidencia.

### Experiencia de usuario y criterio de RRHH

- Diseñar una interfaz profesional, accesible y responsive, con lenguaje sencillo para RRHH, jerarquía visual clara y estados de carga, vacío, error, revisión y descarga.
- Facilitar revisión y corrección sin cambios silenciosos: mostrar valores originales/finales, conceptos afectados, diferencias de líquido y confirmaciones requeridas. Mantener visibles las consecuencias de cada edición.
- Aplicar etiquetas asociadas a controles, navegación por teclado, foco visible, contraste adecuado, errores junto al campo y anuncios accesibles de resultados. No depender exclusivamente del color ni de animaciones.
- Evitar exposición innecesaria de DUI y salarios, confirmaciones repetitivas y acciones ambiguas. Mantener separación visual entre planilla y honorarios para evitar entregar el formato incorrecto.
- Respetar los datos y reglas documentados. Cuando una decisión requiera autoridad de RRHH o contabilidad, señalar el punto concreto y habilitar la revisión prevista; no inventar tasas, períodos, deducciones ni datos de personas.

### Verificación y entrega integral

El agente debe implementar, ejecutar y verificar el flujo completo, incluyendo frontend, API, lectura real del perfil, correcciones, preview, PDFs y ZIP. Entregar pruebas significativas de reglas monetarias, validaciones, límites y rutas críticas; comprobar visualmente ambos PDFs y la interfaz en escritorio y móvil. No limitarse a generar archivos de código ni declarar éxito porque compila.

Antes de dar por terminada la solución deben pasar los criterios de la sección 13, el build de frontend, análisis estático y pruebas del backend. Entregar instrucciones claras de instalación, ejecución, configuración y despliegue, y reportar qué se verificó y qué permanece pendiente. Mantener toda la especificación y sus actualizaciones en este único documento de requerimientos.

## 1. Alcance y criterio rector

Aplicación interna React + TypeScript y API Python FastAPI. RRHH carga un `.xlsx`, revisa validaciones y descarga un PDF con todas las boletas de planilla, un PDF con todas las boletas de honorarios o un ZIP con ambos PDFs. No requiere login, base de datos, historial ni almacenamiento persistente de archivos o información salarial. No calcula una nueva nómina ni valida obligaciones fiscales: representa los importes del libro y comprueba su coherencia aritmética.

Fuente inspeccionada: `ejemplo planilla y boleta.xlsx`, recuperada del adjunto de la conversación original. Se revisaron las cuatro hojas, todas las celdas con contenido, fórmulas y valores calculados guardados, combinaciones, dimensiones, formatos numéricos, áreas de impresión y referencias entre hojas. No se ejecutó Excel ni se recalcularon fórmulas. La inspección es estructural; no se afirma fidelidad visual mediante render de Excel. Los textos con tildes se verifican en el XML original antes de corregirlos: la salida de consola puede sustituir caracteres.

Decisión funcional: reutilizar la organización de las boletas, corrigiendo omisiones y signos para que el detalle explique el líquido. No reproducir errores conocidos de las plantillas. Los períodos contradictorios exigen confirmación explícita de RRHH mediante fechas en pantalla. El Excel original no se modifica.

## 2. Inventario real

| Hoja | Dimensión informada | Fuente útil | Registros reales | Función |
|---|---|---|---:|---|
| PLANILLA | A1:AQ33 (43 columnas; contenido hasta AN) | Encabezados A6:AN6; filas 7:13; total fila 14 | 1, fila 7 | Datos de empleados y cálculo salarial |
| BOLETA PLANILLA | A1:G34; contenido principal A:D | A1 selector; B2:B28 y D30 | 1 vista seleccionada | Plantilla basada en VLOOKUP |
| HONORARIOS | A1:AJ27 | Encabezados A6:AJ6; filas 7:10; total fila 11 | 1, fila 7 | Datos de prestadores y cálculo |
| BOLETA HONORARIOS | A1:I32 | A1 selector; B2:B26 y D28; auxiliar I18 | 1 vista seleccionada | Plantilla basada en VLOOKUP |

Todas visibles, sin tablas estructuradas, nombres definidos, validaciones de datos ni imágenes incrustadas. No hay logo que extraer. En las hojas fuente no hay combinaciones. Las boletas combinan B:D para valores, A:D para títulos de sección, A:C para el rótulo del líquido, y reservan bloques para firmas.

PLANILLA imprime A1:AI36, orientación horizontal, escala 41%; omite aportes patronales AK:AN. HONORARIOS imprime A1:AE27, horizontal, escala 41%; omite AG:AJ. Las boletas no tienen área ni configuración explícita de impresión: no usar esos parámetros como contrato PDF.

PLANILLA: notas A18, firmas administrativas en fila 31. HONORARIOS: notas A14, firmas administrativas fila 24. Son contenido del consolidado, no datos de colaboradores ni elementos que deban replicarse en cada recibo.

## 3. Diccionario completo de columnas

`r` representa una fila válida de persona. Importes en USD. Conservar códigos y DUI como texto, incluidos ceros iniciales y guiones. Unidades y cantidades no son importes aunque algunas tengan formato contable en el Excel.

| Campo interno / significado | PLANILLA | HONORARIOS |
|---|---|---|
| sequence / correlativo de búsqueda | A | A |
| employee_id / código | B | B |
| employee_name / nombre | C | C |
| dui / documento | D | D |
| pension_provider / AFP | E | No existe |
| area | F | E |
| role / cargo | G | F |
| contracted_amount / salario contratado | H | G |
| worked_days | I | H |
| base_payment / sueldo quincenal | J | I |
| daytime_overtime_hours | K | J |
| daytime_overtime_amount | L | K |
| nighttime_overtime_hours | M | L |
| nighttime_overtime_amount | N | M |
| night_hours | O | N |
| night_amount / nocturnidad | P | O |
| holiday_days | Q | P |
| holiday_amount | R | Q |
| vacation_days | S | No existe |
| vacation_amount | T | R, encabezado VACACIÓN 30% |
| sick_days | U | S |
| sick_amount / incapacidad que resta | V | T |
| personal_leave_days | W | U |
| personal_leave_amount / permiso que resta | X | V |
| commission | Y | W |
| bonus | Z | X |
| other_deductions | AF | Y |
| accrued_amount / devengado | AA | Z |
| employee_social_security / ISSS | AB | No existe |
| employee_pension / AFP | AC | No existe |
| taxable_amount / salario sujeto | AD | No existe |
| income_tax / renta | AE | AB |
| vat / IVA sumado al pago | No existe | AA |
| travel_or_reimbursements | AG | AC |
| net_payment / líquido | AH | AD |
| employer_training / INCAF | AK | AG |
| employer_social_security | AL | AH |
| employer_pension | AM | AI |
| employer_total | AN | AJ |

PLANILLA AI:AJ y HONORARIOS AE:AF son separadores sin campos funcionales. AK3:AL4 de PLANILLA y AG3:AH4 de HONORARIOS contienen auxiliares de un cálculo patronal con base 1000; no representan personas ni parámetros que el servicio deba aplicar.

Empresa autorizada: PLANILLA!A1 = `PROCONTEL S.A DE C.V`. HONORARIOS!A1 contiene el marcador `nombre empresa`; su boleta toma la empresa de PLANILLA!A1. Adoptar esta misma fuente para ambos tipos y mostrarla en revisión. Si falta o sigue siendo un marcador, exigir empresa en el formulario; no inventarla.

## 4. Fórmulas observadas y relaciones

Las boletas usan A1=1 para buscar la columna A de su fuente; no contienen el universo de recibos. No cambiar A1 y exportar repetidamente: openpyxl no evalúa VLOOKUP. Leer directamente todas las filas de PLANILLA/HONORARIOS.

PLANILLA, fila r:

```text
J = H / 30 * I
L = (H / 30 / 8 * 2) * K
N = (H / 30 / 8 * 2.25) * M
R = H / 30 * Q
AA = J + L + N + P + R + T - V - X + Y + Z
AB = MIN(AA * 0.03, 15)
AC = AA * 0.0725
AD = AA - AB - AC
AE = IF AD<=275: 0
     ELSE IF AD<=447.62: 8.83 + (AD-275)*0.1
     ELSE IF AD<=1019.05: 30 + (AD-447.62)*0.2
     ELSE: 144.28 + (AD-1019.05)*0.3
AH = AD - AE - AF + AG
AK = MIN(AA*0.01, 5)
AL = MIN(AA*0.075, 37.5)
AM = AA*0.0875
AN = AA+AK+AL+AM
```

T7=450 es manual; no hay fórmula de vacaciones en esa celda. P, V, X y otros conceptos pueden ser entradas manuales. No deducir importes a partir de días. No aplicar estas tasas como normativa vigente: son exclusivamente evidencia del archivo.

HONORARIOS:

```text
I7 = 900 (manual; no G/30*H)
K = (G / 30 / 8 * 2) * J
M = (G / 30 / 8 * 2.25) * L
Q = G / 30 * P
Z = I + K + M + O + Q + R - T - V + W + X - Y
AA7 = Z7 * 0.13
AB = Z * 0.10
AD = Z + AA - AB + AC
AG = MIN(Z*0.01, 5)
AH = MIN(Z*0.075, 37.5)
AI = Z*0.0875
AJ = Z+AG+AH+AI
```

AA8:AA10 no contienen fórmula de IVA. No autocompletarla ni extrapolar el 13% a otras filas. Las contribuciones patronales en honorarios existen en el archivo, pero no justifican clasificarlas como deducciones de una boleta ni aplicarlas automáticamente.

## 5. Trazabilidad de plantillas y defectos encontrados

### BOLETA PLANILLA

| Destino original | Fuente / comportamiento real |
|---|---|
| B2, B3, B4 | C, G, F de PLANILLA por correlativo A1 |
| B5, B6 | PLANILLA!A1, PLANILLA!A4 |
| B7:B11 | H, I, K, Q, S |
| B14, B15 | J, L |
| B16, rotulado Bonificación | **Y (comisión), debería distinguir Y y Z** |
| B17, B18, B21 | Aguinaldo, reintegros, otros ingresos: constantes 0 sin fuente |
| B19, B20 | AG, T |
| B22 | SUM(B14:D21) |
| B24:B27 | AB, AC, AE, AF |
| B28 | SUM(B24:D27) |
| D30 | AH |

Rangos VLOOKUP inconsistentes: B2/B3 parten de A6:AH20, B4 de A7:AH12 y otros de A7:AH20. Un empleado posterior a fila 12 puede fallar solo en el área. No heredar esos límites.

Caso real: subtotal de plantilla 915.00, descuentos 232.0835 y líquido 851.6665; 915 - 232.0835 = 682.9165. Faltan 168.75 de horas extras nocturnas N7. También faltan renglones para nocturnidad, asuetos, comisión correctamente identificada, bonificación Z y reducciones V/X.

### BOLETA HONORARIOS

| Destino original | Fuente / comportamiento real |
|---|---|
| B2:B4 | C, F, E de HONORARIOS |
| B5 | PLANILLA!A1, no HONORARIOS!A1 |
| B6 | Texto manual: DEL 16 AL 30 DE JUNIO DE 2026 |
| B7:B10 | G, H, J, P |
| B11, rotulado Días de vacaciones | **R es dinero, no días** |
| B14:B16 | I, K, X |
| B17, B18, B20 | Constantes 0 sin fuente |
| B19, B21 | AC, SUM(B14:D20) |
| B23:B25 | AA (IVA), AB (renta), Y (otros descuentos) |
| B26 | SUM(B23:D25), suma IVA como descuento |
| D28 | AD |
| I18 | B21-B24+B23, auxiliar fuera de boleta |

Todos los VLOOKUP usan A6:AD11, incluyendo la fila total. Caso real: ingresos 900, supuesto descuento 207, líquido 927. El líquido sigue 900 + 117 - 90. El IVA se suma y debe aparecer como adición separada, no descuento. El descuento Y ya se resta en Z: evitar restarlo dos veces.

### Fechas, totales y calidad de fuente

- A2 de ambas fuentes habla de segunda quincena de febrero de 2026; PLANILLA!AB2 menciona primera quincena de enero.
- A4 de ambas fuentes indica 16 a 31 de marzo de 2026; BOLETA HONORARIOS!B6 indica 16 a 30 de junio.
- PLANILLA fila 14 suma rangos distintos: H/J/L hasta fila 12, AA:AH hasta 13, varios conceptos solo hasta 9. HONORARIOS fila 11 también mezcla límites hasta 8, 9 y 10. Los totales pueden omitir empleados al agregar filas.
- HONORARIOS!J11 contiene un punto literal, no horas. Identificar la fila total antes de interpretar sus números.
- La misma persona de muestra figura en ambos tipos con códigos y DUI distintos. No unir ni eliminar registros entre categorías por nombre; emitir advertencia de posible coincidencia, sin revelar documentos completos en mensajes técnicos.
- PLANILLA tiene siete filas candidatas pero solo una persona; HONORARIOS cuatro candidatas y solo una. Fórmulas que devuelven cero no constituyen empleados.

## 6. Contrato de extracción

Perfil versionado `procontel_fixed_v1`. Exigir las dos hojas fuente para conservar el contrato de empresa compartida; las hojas BOLETA son referencias opcionales para detectar inconsistencias, no fuentes monetarias. Reportar si faltan. Solo validar y generar los tipos solicitados, salvo metadatos comunes.

1. Leer el archivo dos veces con openpyxl: `data_only=False` para fórmulas y `data_only=True` para resultados guardados; `keep_links=False`, sin guardar el libro. Ambos desde bytes independientes en memoria.
2. Comprobar encabezados en fila 6 por coordenada y significado esperado. Normalizar mayúsculas, espacios, Unicode y tildes únicamente para comparar encabezados. Aceptar explícitamente NORTURNIDAD y VACACIÓN 30% como alias del perfil. No buscar columnas por parecido ni desplazar automáticamente el mapa.
3. Iniciar filas en 7. Encontrar un único marcador Total Planilla en F de PLANILLA y E de HONORARIOS, mediante comparación normalizada; finalizar antes de él. En el ejemplo: 14 y 11. Admitir filas insertadas antes del total si los encabezados y las columnas siguen iguales; rechazar marcador ausente o ambiguo. No usar max_row, print_area ni límites VLOOKUP como cantidad de empleados.
4. Una fila es vacía si A:D están vacías y todos los importes/cantidades son cero o vacíos; ignorar sus fórmulas precargadas. Si hay nombre/código/correlativo incompleto o importes no cero sin identidad, devolver error de fila, nunca descartarla silenciosamente.
5. Requerir correlativo entero positivo, código y nombre no vacíos; correlativo y código únicos dentro del tipo. DUI no se infiere ni se convierte a número; si falta, advertencia y omitirlo en la boleta. Área/cargo vacíos: advertencia. Mismo código en distintos tipos: advertencia, sin deduplicación cruzada.
6. Para fila válida, exigir importes centrales base, devengado, retenciones aplicables y líquido. Conceptos opcionales manuales vacíos equivalen a cero. Una fórmula sin resultado guardado nunca equivale a cero. IVA vacío en honorarios requiere confirmación explícita por fila o corrección del libro, pues las fórmulas no son uniformes. No suponer IVA obligatorio por tasa.
7. Rechazar errores Excel en campos necesarios, valores no finitos o textos monetarios no numéricos. Cero es válido. Cantidades deben ser no negativas. Importes negativos se rechazan en v1: las reducciones tienen columnas positivas con signo definido; no inventar tratamiento para ajustes negativos.
8. Usar `Decimal(str(value))`; no operar dinero con float. Preservar precisión de origen para conciliación y redondear solo presentación.
9. Retener por campo `sheet`, `cell`, fórmula y valor fuente en memoria para diagnóstico. Nunca registrar esta estructura en logs ni devolver fórmulas completas al navegador.

No ejecutar fórmulas, macros, enlaces externos, eval ni conversiones mediante Office. openpyxl no recalcula; `fullCalcOnLoad=True` no acredita que los valores estén actualizados. Ante caché ausente: instruir a RRHH a abrir, recalcular y guardar en Excel y volver a cargar. Una caché existente puede estar desactualizada de forma coherente: advertir que RRHH debe guardar el libro actualizado; las conciliaciones no prueban frescura. No agregar un motor de nómina o LibreOffice implícitamente.

## 7. Conciliación y modelo monetario de PDF

### Planilla

```text
ingresos_brutos = J+L+N+P+R+T+Y+Z
reducciones_operativas = V+X
devengado_comprobado = ingresos_brutos-reducciones_operativas
descuentos = AB+AC+AE+AF
neto_comprobado = devengado_comprobado-descuentos+AG
```

Comparar devengado con AA, salario sujeto con AA-AB-AC y AD, neto con AH. No recalcular tasas ni exigir J=H/30*I: el libro puede incluir pagos manuales autorizados. Se puede advertir esa diferencia, sin sustituirla.

### Honorarios

```text
ingresos_brutos = I+K+M+O+Q+R+W+X
reducciones_operativas = T+V
otros_descuentos = Y
base_neta = ingresos_brutos-reducciones_operativas-otros_descuentos
neto_comprobado = base_neta+AA-AB+AC
```

Comparar base_neta con Z y neto con AD. Mostrar otros descuentos una sola vez. IVA como adición sobre base_neta; renta como retención. No recalcular tasas ni aplicar ISSS/AFP a honorarios.

Tolerancia de conciliación de origen: diferencia absoluta <= USD 0.01. Mayor diferencia: error bloqueante con hoja, fila, campo e importes esperado/encontrado. Comparar totales fuente por cada columna contra suma de filas válidas como diagnóstico: advertir rangos parciales; no usar esos totales como fuente de boletas ni bloquear si el detalle concilia. Sumar líquidos de personas para el resumen.

Presentación `ROUND_HALF_UP`, dos decimales, `$1,234.56`. Los importes fuente no se sustituyen. Si la suma de renglones ya redondeados difiere del líquido fuente redondeado, incluir un renglón explícito Ajuste de presentación por redondeo con la diferencia; no ocultarla en otro concepto. Limitarlo al residuo explicable por redondeo de los renglones; cualquier otro residuo bloquea. Totales visibles se calculan sobre renglones visibles para que puedan verificarse.

Ejemplo real planilla: bruto 1083.75; ISSS 15.00; AFP 78.57; renta 138.51; neto fuente 851.6665 -> **851.67**. Descuentos visibles 232.08; no requiere ajuste. Honorarios: base 900.00, IVA 117.00, renta 90.00, neto **927.00**.

## 8. Dos plantillas PDF

ReportLab con fuentes locales Unicode incrustadas y generación sobre BytesIO; no capturas del Excel. Carta vertical (612×792 puntos), márgenes 36 puntos, una boleta por página y salto obligatorio entre personas. Contenido legible de 10–11 puntos; rótulos extensos y nombres deben envolver. Si el contenido excede el área, usar página de continuación con identidad y número de página, nunca cortar o reducir a texto ilegible. Pruebas visuales con nombres/cargos extensos.

Encabezado: empresa, BOLETA DE PAGO — PLANILLA u HONORARIOS, período confirmado y moneda USD. Identificación: correlativo, código, nombre, cargo, área; DUI y AFP cuando existan. Contratado y días trabajados. No incluir aportes patronales en el recibo del colaborador. No hay logo adjunto: usar marca tipográfica hasta disponer de un recurso aprobado.

Planilla: cantidades de horas diurnas/nocturnas/nocturnidad, días de asueto/vacaciones/incapacidad/permisos cuando existan; ingresos con base, extras diurnas y nocturnas, nocturnidad, asuetos, vacaciones, comisiones y bonificación. Mostrar bruto, reducciones por incapacidad/permisos, devengado; deducciones ISSS, AFP, renta, otros; adicionar viáticos o reintegros AG; líquido destacado. No dividir AG entre viáticos y reintegros porque la fuente no los separa.

Honorarios: contratado, días y horas disponibles; no mostrar días de vacaciones, pues no existe esa columna. Ingresos base, extras, nocturnidad, asuetos, vacaciones (importe R), comisión, bonificación; reducciones T/V y otros descuentos Y; base neta Z; adición IVA AA; retención renta AB; viáticos o estadías AC; líquido AD destacado. Identificar la base como Importe devengado después de descuentos, evitando afirmar una base fiscal distinta de la del archivo.

Mantener base, subtotales, retenciones y líquido aunque sean cero; renglones opcionales cero pueden omitirse. No emitir Aguinaldo, Otros ingresos o Reintegros separados con datos inventados: los ceros de plantilla no tienen columna fuente. Dos espacios finales: Firma del colaborador / prestador y Firma y sello de la empresa. Sin firmas digitales simuladas. Pie de página con tipo y página, sin hora/servidor ni rutas de archivo.

Orden de boletas: orden físico de filas fuente; no ordenar por nombre. Un PDF consolidado por tipo, no un archivo por persona. ZIP con dos entradas PDF y sin el Excel, datos JSON, carpetas o boletas sueltas. Nombres seguros: `boletas_planilla_YYYYMMDD_YYYYMMDD.pdf`, `boletas_honorarios_YYYYMMDD_YYYYMMDD.pdf`; ZIP `boletas_procontel.zip`, pues los tipos pueden tener períodos diferentes.

## 9. Flujo React

1. Pantalla única, identificación Procontel y aviso Procesamos el archivo durante esta solicitud; no guardamos tu planilla.
2. Selector accesible de archivo `.xlsx`, arrastrar/soltar opcional, tamaño visible y botón Analizar. Seleccionar Planilla, Honorarios o Ambos (por defecto ambos).
3. Resultado: empresa, cantidades por tipo, suma de líquidos, períodos hallados con su procedencia, lista de errores/advertencias con celdas. No mostrar un listado completo de salarios por defecto.
4. Fechas inicio/fin obligatorias por tipo; sugerir A4 cuando sea interpretable, pero exigir confirmación porque el ejemplo contradice otras celdas. Permitir empresa corregida y confirmar expresamente IVA vacío como cero por fila si corresponde. Habilitar vista previa editable de los registros conforme a la sección 9.1.
5. Botones Generar PDF de planilla / Generar PDF de honorarios / Descargar ambos en ZIP según selección. Bloquear si errores del ámbito seleccionado, fechas inválidas o confirmaciones faltantes. Estado de progreso indeterminado, botón deshabilitado durante solicitud y opción cancelar.
6. Descargar Blob, revocar ObjectURL al terminar o reemplazarlo. Botón Limpiar que borra archivo, resultados y confirmaciones; cancelar AbortController. Estado únicamente en memoria React. No localStorage, sessionStorage, IndexedDB, service worker, analítica de formularios ni caché offline.

Usar React + TypeScript, componentes FilePicker, OutputSelector, ValidationSummary, PeriodConfirmation, DownloadActions y un hook useBoletaWorkflow. Validación cliente como ayuda; backend siempre revalida. Al cambiar archivo o selección, invalidar análisis y confirmaciones anteriores. Manejar errores JSON incluso cuando la solicitud espera Blob. No insertar texto de Excel como HTML.

### 9.1 Vista previa y correcciones de RRHH

Después de analizar, ofrecer pestañas Planilla y Honorarios con tabla paginada en memoria: código, nombre, cargo, días trabajados, importe base, devengado, descuentos, líquido y estado. Buscador local por nombre/código y filtro Modificados / Con observaciones. No descargar aún ni enviar datos a servicios de terceros. En móvil usar tarjetas y panel de edición.

Al seleccionar una persona, abrir un panel con todos sus conceptos y una vista previa de la boleta. Mostrar Original del Excel y Valor actual por campo, marcar cambios y actualizar totales generales. Permitir corregir nombre, cargo, área, días y horas, salario contratado, pago base, conceptos monetarios, retenciones y líquido. Código, correlativo, hoja y fila son identidad de origen inmutables en v1. No crear/eliminar personas ni cambiar su tipo; corregir esos casos en el Excel y volver a cargar.

Reglas de edición obligatorias:

- Los cambios son temporales: afectan únicamente la descarga actual; nunca modifican el Excel original. Mostrar este aviso junto al editor.
- Editar días, horas o contratado **no recalcula automáticamente** sueldo, extras, impuestos ni aportes. Es un generador de boletas y la fuente contiene pagos manuales. Mostrar aviso junto al campo y exigir confirmación de que RRHH revisó los importes relacionados. Por ejemplo, cambiar 15 días a 14 conserva el pago base hasta que RRHH lo modifique expresamente.
- Editar un concepto monetario recalcula mediante las identidades de la sección 7 el bruto, devengado/base neta, salario sujeto, subtotales y líquido; las tasas no se vuelven a aplicar. ISSS, AFP, renta e IVA siguen siendo importes explícitos y editables. Al cambiar una base que pueda afectarlos, marcar Requiere revisión de retenciones y exigir confirmación antes de generar.
- Devengado, salario sujeto y subtotales se muestran como derivados de solo lectura; no son overrides independientes. El líquido tiene una acción específica Cambiar líquido, descrita abajo.
- Cada registro modificado requiere un motivo no vacío de 5 a 300 caracteres y una confirmación final Revisé esta corrección. Cambiar nuevamente un campo invalida esa confirmación. El motivo permanece solo en memoria y no se imprime en el recibo ni se registra en logs.
- Botones Restaurar registro y Restaurar todos; al restaurar, eliminar overrides, motivos, objetivos de líquido y confirmaciones asociadas. No usar la tecla Escape o cerrar panel como aceptación implícita.

**Cambio directo de líquido:** no sobrescribir el número final dejando un detalle incompatible. El usuario introduce el líquido deseado con dos decimales. El servidor calcula `ajuste_manual = líquido_deseado - líquido_calculado_redondeado`, después de aplicar todos los demás cambios. Mostrar la diferencia y pedir confirmación; una diferencia positiva se imprime como Ajuste manual a favor, una negativa como Ajuste manual de descuento. Es un concepto nuevo explícito de la aplicación, separado del ajuste por redondeo. El objetivo de líquido se conserva hasta que el usuario lo quite; si cambia otro concepto, volver a calcular la diferencia, mostrarla e invalidar la confirmación. Si RRHH quiere corregir el salario base o una retención en lugar de agregar un ajuste, debe editar ese concepto y quitar el objetivo de líquido.

Este ajuste mantiene el recibo explicable, pero no determina un tratamiento tributario: no modifica automáticamente bases ni retenciones. Exigir confirmación de revisión de estas cuando exista ajuste manual. Mostrar advertencia Corrección fuera del Excel: el archivo original conserva sus importes. El PDF refleja los valores finales y el ajuste, sin publicar el motivo interno.

Dinero editable: strings decimales no negativos con máximo dos decimales y límite de USD 10,000,000 por campo; cantidades: hasta dos decimales, días 0–31 y horas 0–744 por período en v1. Rechazar texto, no finitos, exponentes y desbordamientos. El ajuste manual es firmado y calculado por el backend, nunca aceptado como importe libre del cliente. No permitir líquido final negativo. Cantidades del Excel con límites incompatibles producen observación para corregir, no truncamiento.

**Validación de fuente y correcciones:** conservar diagnóstico original y diagnóstico efectivo separados. Una discrepancia aritmética de origen puede resolverse corrigiendo sus conceptos y confirmando expresamente los totales efectivos; mostrar que difieren del Excel. Un campo manual faltante o un error Excel en un importe primitivo puede reemplazarse explícitamente desde el editor. Fórmula sin caché, estructura desconocida e identidad incompleta siguen bloqueando y requieren corregir el libro; un objetivo de líquido no los oculta. No aceptar un simple cambio de líquido para silenciar un devengado de origen incompatible: exigir corrección de conceptos o aceptación explícita del devengado derivado con motivo. En registros editados, las identidades de la sección 7 usan valores efectivos; comparar con totales de origen pasa a ser advertencia reconocida, mientras la conciliación interna final sigue siendo obligatoria.

La vista previa final debe proceder del mismo generador PDF del servidor que la descarga. Vista previa HTML local es solo orientativa y debe indicarlo. Antes de descargar exigir una validación del servidor sobre los cambios vigentes; si el usuario cambia algo después, invalidar esa revisión y regenerar la vista previa. El resumen final muestra personas corregidas, líquidos originales/finales y diferencia total por tipo.

## 10. API sin estado

### POST /api/v1/analyze

Multipart: `file` y `options` (string JSON con `selection`: planilla | honorarios | ambos). HTTP 200 si se pudo inspeccionar, incluso si hay errores de negocio; respuesta `can_generate`, `schema_version`, `file_sha256`, `company`, `types` (count, net_total como string decimal, períodos con celdas), `records` con campos originales tipados para el editor y `issues`. No devolver archivo ni token de sesión. Hash sirve para detectar cambio de archivo en UI; no se conserva ni registra en servidor. Los registros salariales se devuelven únicamente a este navegador, con no-store, y no se incluyen en telemetría.

Issue: `code`, `severity` error | warning | confirmation, `type`, `sheet`, `cell`, `row`, `field`, `message`; esperado/encontrado solo en respuesta al usuario cuando sea necesario. Ejemplos: PERIOD_CONFLICT, IVA_CONFIRMATION_REQUIRED, TEMPLATE_MAPPING_MISMATCH, ROW_INCOMPLETE, FORMULA_CACHE_MISSING, SOURCE_RECONCILIATION_FAILED, TOTAL_RANGE_INCOMPLETE.

### POST /api/v1/generate

Multipart: mismo `file`, `options` JSON. Reenviar archivo evita almacenamiento entre análisis y descarga. Ejemplo de options:

```json
{
  "selection": "ambos",
  "schema_version": "procontel_fixed_v1",
  "company_override": null,
  "periods": {
    "planilla": {"start": "2026-03-16", "end": "2026-03-31", "confirmed": true},
    "honorarios": {"start": "2026-03-16", "end": "2026-03-31", "confirmed": true}
  },
  "zero_vat_confirmations": []
}
```

Las fechas son ejemplo de uso, no aprobación del período del archivo. Cada confirmación de IVA identifica hoja y fila; validar que existe y solo cubre una celda IVA manual vacía. Fórmula sin caché jamás se soluciona con confirmación. Fecha ISO real, inicio <= fin; permitir períodos diferentes y no inferir mes de fecha actual. Validar longitudes y contenido de company_override.

Backend vuelve a extraer, validar y conciliar. No confiar en `can_generate` cliente ni en totales derivados suministrados por el cliente; admitir únicamente correcciones explícitas mediante el contrato siguiente. Si se piden ambos, fallo de cualquiera implica respuesta JSON completa sin ZIP parcial. Si un tipo solicitado tiene cero personas: error EMPTY_SELECTION; no fabricar un PDF vacío. Un solo tipo válido puede generarse aunque el otro no se haya seleccionado.

### Contrato adicional de edición y vista previa

Agregar a options `file_sha256` obligatorio cuando existan correcciones y `overrides`, por defecto `[]`. Cada override identifica un registro con `type`, `source_row` y `employee_id`; incluye `changes` con una lista blanca de campos primitivos de la sección 3, `target_net` opcional como string decimal, `reason`, `confirmed`, `related_amounts_reviewed`, `taxes_reviewed` y `accept_derived_totals` cuando corresponda. Ejemplo:

```json
{
  "type": "planilla",
  "source_row": 7,
  "employee_id": "C-093",
  "changes": {"worked_days": "14", "base_payment": "420.00"},
  "target_net": "830.00",
  "reason": "Corrección de días y pago revisada por RRHH",
  "confirmed": true,
  "related_amounts_reviewed": true,
  "taxes_reviewed": true,
  "accept_derived_totals": true
}
```

Rechazar hash distinto del archivo recibido (409 FILE_CHANGED), identidad inexistente/discordante, overrides repetidos, campos desconocidos o derivados, confirmaciones faltantes y límites inválidos. Máximo un override por registro y cantidad no mayor al número de registros aceptados. Normalizar y aplicar cambios en copia del modelo original; no escribirlos en workbook. Mantener original, efectivo y cambios separados durante la solicitud.

`POST /api/v1/review`: mismo archivo y options, devuelve JSON con registros efectivos, cambios, ajustes calculados, totales y issues. `POST /api/v1/preview`: mismo contrato más `preview_record` (tipo, fila y código), devuelve application/pdf inline de una persona usando el renderer final; aplica los mismos errores, controles y no-store. No guardar previews ni publicar URL recuperable. La generación final siempre revalida el archivo y los overrides completos; review no crea sesión ni autorización reutilizable. La UI compara su revisión local de cambios con la solicitud vigente para no mostrar una preview anterior como actual.

Para PDF y ZIP, la fuente final es el modelo efectivo validado, nunca los valores originales ignorando overrides. No incluir motivos ni historial de cambios dentro del ZIP. React conserva archivo y cambios exclusivamente en memoria y los reenvía en cada solicitud.

Respuesta 200: application/pdf para un tipo; application/zip para ambos; `Content-Disposition: attachment` con nombre generado, `Cache-Control: no-store, private`, `Pragma: no-cache`, `X-Content-Type-Options: nosniff`. Aplicar no-store también a análisis y errores.

Errores: 400 archivo ilegible/opciones JSON inválidas; 413 límites de carga; 415 formato no admitido; 422 estructura, datos, conciliación o confirmaciones; 429 capacidad/ritmo excedido; 500 error inesperado con mensaje genérico y request_id aleatorio. Timeout de procesamiento 504 en proxy, con mensaje manejable. Cuerpo homogéneo `{ "code": "...", "message": "...", "issues": [], "request_id": "..." }`. Nunca devolver traceback, rutas ni volcado del libro.

GET /healthz sin datos sensibles. No crear endpoints /jobs, /history, /files ni rutas de recuperación. No Redis, Celery ni object storage para v1.

## 11. Arquitectura propuesta

```text
backend/app/
  main.py
  api/routes.py
  schemas/requests.py
  schemas/results.py
  domain/models.py
  domain/reconciliation.py
  domain/presentation_money.py
  excel/loader.py
  excel/profiles/procontel_v1.py
  excel/parser.py
  excel/validators.py
  pdf/common.py
  pdf/planilla.py
  pdf/honorarios.py
  services/analyze.py
  services/generate.py
  services/archive.py
  security/upload_limits.py
  assets/fonts/
backend/tests/
frontend/src/
  components/
  features/boletas/
  api/client.ts
  types/
  App.tsx
```

Modelo común: PaymentRecord(type, source_row, sequence, employee_id, name, dui, area, role, company, period, quantities, amounts, provenance). Estructuras tipadas específicas PayrollRecord y FeesRecord evitan interpretar IVA como ISSS o dinero como días. Campos monetarios Decimal; esquema HTTP de dinero en strings. Mapa de columnas y alias declarativo por perfil, sin índices mágicos dispersos. Funciones puras de extracción/conciliación independientes del PDF y de FastAPI.

Agregar domain/overrides.py para aplicar correcciones y resolver objetivos de líquido; schemas/overrides.py para lista blanca y confirmaciones; servicios review y preview. React incorpora RecordsTable, RecordEditor, ChangeSummary y PdfPreview. Una única función de construcción del modelo efectivo debe usarse en review, preview y generate para evitar diferencias entre pantalla y descarga.

FastAPI/Pydantic para HTTP, openpyxl para lectura, ReportLab para PDF y zipfile para ZIP en BytesIO. Fijar versiones en lockfile y validar sus APIs en documentación oficial durante implementación. No es necesario instalar un evaluador de fórmulas ni Microsoft Office en el servidor.

## 12. Privacidad y operación sin persistencia

Sin login exige limitar la exposición: desplegar en la red interna o acceso de red corporativo; no convertirlo en servicio público anónimo para nóminas. HTTPS y mismo origen para frontend/API; no CORS comodín. Si se habilita CORS, lista cerrada de orígenes y sin credenciales.

Límites iniciales configurables: carga comprimida 10 MiB, contenido ZIP descomprimido 100 MiB, 2000 entradas, 1000 personas por tipo, 60 segundos por solicitud, 2 generaciones concurrentes por instancia. Medir en entorno de destino antes de publicar; no son resultados de benchmark.

Validar extensión, estructura OOXML y contenido real, no solo MIME. Rechazar xls, xlsm, archivos cifrados, macros/objetos incrustados, paquetes rotos y límites ZIP excedidos. Inspeccionar tamaños y leer con límite efectivo acumulado para evitar confiar solo en metadatos ZIP. Rechazar relaciones externas en v1 con mensaje de corregir el archivo; no descargarlas. No extraer ZIP de entrada a disco. No aceptar URLs como fuente de archivo. Limitar filas/celdas declaradas, textos y tamaño XML antes de cargar; parser XML endurecido y dependencias actualizadas.

Para cumplir literalmente sin persistencia, no usar UploadFile/SpooledTemporaryFile sin controlar su desbordamiento a disco. Recibir multipart con parser incremental limitado y contenedor en memoria; contar bytes durante lectura y detener al exceder límite. No usar request.body sin límite de entrada. Proxy con buffering a disco deshabilitado y volumen temporal tmpfs si alguna biblioteca lo requiere; documentar que tmpfs es transitorio en RAM. Sin request-body logging, APM de payloads, crash dumps ni backups de directorios temporales. Para requisitos estrictos de RAM, swap cifrada o deshabilitada según operación y revisión de infraestructura.

Cerrar libros, buffers y streams en finally ante éxito, error o cancelación; liberar al terminar respuesta. No prometer borrado criptográfico de memoria de Python. El navegador y la descarga del usuario conservan datos según sus controles locales; la promesa de no persistencia se refiere al servicio. No incluir datos de personas en URLs, logs, métricas, nombres de archivos, mensajes de error inesperado o request_id. Logs técnicos mínimos: estado HTTP, duración, tamaño y error code; retención operativa separada de nómina.

Procesamiento pesado fuera del event loop, con concurrencia acotada y aislamiento/timeout que permita finalizar trabajo real; cancelar fetch por sí solo no detiene un hilo de Python. Despliegue directo como usuario sin privilegios, código de solo lectura y sin almacenamiento de planillas. Desactivar caché de proxy/CDN para /api. Frontend puede cachear únicamente assets estáticos versionados.

## 13. Pruebas y criterios de aceptación

1. Archivo real: contar 1 planilla y 1 honorarios; excluir ceros precargados y totales. No aprobar generación automática mientras falten fechas confirmadas.
2. Planilla fila 7: base 450, extra diurna 15, extra nocturna 168.75, vacaciones 450, bruto 1083.75, líquido 851.67. El PDF explica todo el líquido.
3. Honorarios fila 7: base 900, IVA +117, renta -90, líquido 927.00; no ISSS/AFP y no días de vacaciones derivados de R.
4. Tras confirmar períodos válidos: cada PDF tiene una boleta; ZIP exactamente dos PDFs, con tipos y personas correctos. Textos extraídos del PDF y revisión visual de ambas plantillas.
5. Insertar personas antes de total, incluyendo fila 13/última candidata; leer todas aunque VLOOKUP original no las alcance. Advertir totales fuente incorrectos, no perder colaboradores.
6. Duplicados dentro del tipo, fila parcial, importe huérfano, total ausente/duplicado, encabezados desplazados, faltantes y plantilla distinta: errores localizables.
7. Cero numérico válido frente a fórmula sin caché, error Excel, NaN, texto en importe e IVA vacío: tratamiento distinto y verificable.
8. Comisión Y y bonificación Z en planilla; comisión W y bonificación X en honorarios: no intercambiarlas. Incapacidad, permisos, viáticos y otros descuentos no cero: conciliación sin dobles descuentos.
9. Casos de redondeo a medio centavo y acumulación de varios conceptos: totales visuales explicables con ajuste identificado; diferencias de origen >0.01 bloquean.
10. Un tipo vacío, tipos con períodos distintos y fallo de uno al pedir ambos: sin salidas parciales inadvertidas. Misma persona en ambos tipos se conserva.
11. Archivos sobredimensionados, ZIP bomb, externos, macros renombradas, XML excesivo, múltiples solicitudes y cancelación: límites efectivos y limpieza de recursos.
12. Inspeccionar filesystem, proxy, logs y navegador después de éxito/error/cancelación: sin Excel, PDFs ni datos salariales persistidos por el servicio. Pruebas de fixtures salariales anonimizadas, nunca subir el Excel real a repositorios públicos.
13. Teclado, lector de pantalla, móvil, reintentos, mensajes JSON al esperar Blob y cambio de archivo: estados coherentes, sin confirmaciones reutilizadas accidentalmente.
14. Editar días conserva importes hasta corrección explícita y exige revisión; editar base actualiza derivados sin recalcular impuestos. Restaurar elimina todos los cambios asociados.
15. Cambiar neto a mayor/menor importe crea ajuste manual con signo correcto; no sustituye retenciones ni oculta incoherencias. Cambiar otro concepto conserva objetivo, recalcula ajuste e invalida confirmación. Separar ajuste manual y residuo de redondeo.
16. Archivo/hash/identidad distintos, overrides duplicados, campos derivados manipulados, importes inválidos y confirmación ausente se rechazan en backend. Cambios en una categoría no alteran la otra.
17. Preview y descarga final muestran mismos valores efectivos, conceptos y líquido. ZIP incluye las correcciones de ambos tipos; original permanece intacto. Ningún motivo, salario o edición queda en logs, almacenamiento navegador o servidor.

## 14. Entrega al agente desarrollador y salida a producción

Implementar primero perfil/parser y pruebas con fixtures anonimizadas; después conciliación, dos PDFs y ZIP; finalmente API y React. Entregar configuración de servicio y proxy para despliegue directo, variables de límites/origen, lockfiles, pruebas automatizadas y README. No cargar el Excel real como asset del frontend ni incorporarlo a los archivos desplegados.

La revisión funcional con RRHH debe confirmar los períodos, la denominación de conceptos y el IVA de cada caso; no necesita cambiar los cálculos del libro para aprobar el diseño de recibo. No deducir que porcentajes o topes observados constituyen política fiscal vigente. Una eventual calculadora de nómina exige un alcance separado con validación contable.

Listo para aceptar cuando el archivo produce, con confirmaciones explícitas, dos documentos que concilian con sus filas fuente; se eliminan captura y pegado en Word; se detectan inconsistencias antes de emitir recibos y no queda información salarial almacenada en el servicio.


## 15. Actualización funcional: selección de boletas sin edición

Esta actualización solicitada por el usuario reemplaza las reglas de edición de la sección 9.1 y el contrato de overrides. Los datos de las personas y sus importes son de solo lectura: toda corrección se realiza en Excel y se vuelve a cargar el archivo. Se elimina el editor, cambios de líquido, motivos y ajustes manuales. La API rechaza campos de edición antiguos.

Después del análisis se muestra automáticamente la lista de personas agrupada por área. Todos los registros están marcados inicialmente. Hay selección global, por área e individual, con estado parcial en los checks de grupos. Un buscador local filtra nombre, código o área sin borrar selecciones ocultas. Las personas sin área se agrupan en «Sin área». Se conserva el tipo Planilla/Honorarios y la identidad estable tipo/fila/código.

Options incorpora `selected_records`: null selecciona todos (análisis inicial); una lista explícita limita los registros que se revisan, previsualizan y generan. Cada elemento usa type, source_row y employee_id. La lista explícita requiere file_sha256 coincidente; se rechazan listas vacías, repetidas, ajenas o de tipos no analizados. La API conserva el orden físico del Excel al generar. No confía en nombres, áreas, importes o totales enviados por el navegador.

La lista completa permanece visible después de revisar una selección parcial. El servidor valida los registros seleccionados y la estructura aplicable; los errores de personas conocidas desmarcadas no bloquean la selección válida. Los errores estructurales o de filas sin identidad no pueden ocultarse con un checkbox. Se mantienen períodos confirmados, confirmación de IVA manual vacío, conciliación, seguridad y no persistencia. Solo se exigen períodos de los tipos con personas marcadas.

Una selección de una persona entrega un PDF con una boleta. Varias personas de un tipo entregan un PDF consolidado; selecciones que incluyen ambos tipos entregan ZIP con dos PDFs. No se fabrican PDFs vacíos para tipos totalmente desmarcados. Cambiar cualquier selección invalida revisión y preview; cero seleccionadas deshabilita revisión/descarga. La preview debe pertenecer a una persona marcada.

Criterios adicionales: defaults todos marcados; marcar/desmarcar por área y persona; selección parcial; búsqueda conserva marcados; descargar una persona excluye las demás; PDF/ZIP reflejan exactamente la selección; archivo/identidades repetidas o desconocidas se rechazan en servidor; no existen acciones de editar datos.

Actualización de interfaz: el Excel corresponde a un único período. Mostrar un solo selector Desde/Hasta y una única confirmación para todas las boletas seleccionadas; sincronizar esas fechas para planilla y honorarios. Al editar cualquier fecha se invalida la confirmación compartida y la revisión anterior.

Ajuste posterior solicitado: quitar el buscador y el checkbox de confirmación de fechas. La acción Validar revisión acepta el período visible; cambiar fechas sigue invalidando la revisión y exige volver a validarla. Mantener los checks de selección de personas y áreas.

## 16. Formato de impresión actualizado

El usuario confirma papel carta y 10 boletas por hoja, aceptando texto reducido. Este requisito sustituye la boleta por página de la sección 8: carta horizontal (792 × 612 puntos), cinco columnas y dos filas, margen exterior de 9 puntos y separación de 6 puntos entre boletas con guías discontinuas para cortar. La última hoja contiene solo el remanente, sin repetir personas. Una selección individual conserva una sola boleta en su posición y tamaño de corte.

Usar el estilo tabular de las referencias: encabezados azules, datos de persona y período, ingresos, subtotal, descuentos, total, líquido verde y espacios para firma. Conservar comisión, extras nocturnas y cualquier concepto de origen necesario para explicar el líquido. IVA en honorarios se suma, no se resta. Aguinaldo, reintegros separados y otros ingresos sin columna fuente muestran raya y nota de ausencia, sin inventar importes. Honorarios no convierte el importe de vacaciones a días. Los datos extensos se envuelven; si no caben, rechazar de forma explícita en lugar de recortar texto. PDF y preview usan el mismo renderer. Imprimir al 100%.


## 17. Nuevo requerimiento: Excel y PDF de dos boletas por página

Esta actualización reemplaza la distribución de 10 boletas de la sección 16. PDF carta horizontal con dos boletas lado a lado, margen de 18 puntos, separación de 12 puntos y guía de corte; conservar espacio para firmas y mostrar todo el detalle. La última página contiene el remanente sin duplicaciones.

Agregar descarga de boletas en Excel además del PDF. Generar un archivo nuevo en memoria, sin modificar el original, con hojas PLANILLA/HONORARIOS únicamente para los tipos y personas seleccionados. Las celdas monetarias y cantidades son numéricas, con formato de USD para importes; identidades y textos se mantienen como texto y nunca se interpretan como fórmulas. No incluir fórmulas, enlaces externos, macros ni copias de las hojas fuente. El Excel reproduce los mismos datos y detalle conciliado del PDF, usa parejas de recibos y configuración de impresión carta horizontal.

Options incorpora output_format: pdf (predeterminado), xlsx o both. xlsx devuelve un libro Excel; pdf mantiene PDF único o ZIP de dos PDFs según selección; both devuelve ZIP con el libro y los PDFs de los tipos seleccionados. Preview sigue siendo PDF y usa dos posiciones por página. Las tres descargas comparten validaciones, selección, períodos y generación en memoria con no-store. La interfaz ofrece PDF, Descargar Excel y Excel + PDF.


## 18. Exportación sobre una copia del Excel original completo

Este requerimiento sustituye el libro separado de la sección 17. La descarga Excel y el ZIP combinado deben contener una copia del Excel original con todas sus hojas y toda la información de empleados. No guardar sobre el archivo cargado. Las boletas se generan en las hojas existentes BOLETA PLANILLA y BOLETA HONORARIOS de los tipos seleccionados. Conservar nombres, posiciones e identificadores; si falta una hoja requerida se agrega. Las hojas de boletas no seleccionadas se conservan sin cambios.

Conservar los valores, fórmulas, resultados guardados, formatos, anchos, comentarios, hojas ocultas y recursos del libro fuera de las hojas de boletas intervenidas. No regrabar el libro original completo con un motor que elimine cachés o características: sustituir solo los XML de las hojas de boletas, agregar estilos sin cambiar los índices previos y actualizar sus áreas de impresión y la cadena de cálculo cuando corresponda. Las hojas PLANILLA/HONORARIOS y demás XML de datos deben permanecer idénticos en el archivo exportado. No ejecutar fórmulas originales ni recalcular nómina.

Excel + PDF entrega ZIP con ese libro completo y los PDFs de las personas seleccionadas; PDF conserva dos boletas por página carta horizontal y espacio de firmas. Aunque se seleccione una sola persona, el Excel adjunto conserva los datos de todos los empleados; las nuevas boletas y los PDFs sí se limitan a la selección. Mantener procesamiento en memoria, no-store y no persistencia. Comprobar preservación byte por byte de datos y equivalencia de fórmulas, cachés y formatos con fixtures sintéticas y el archivo real sin guardarlo.


## 19. Boletas apiladas verticalmente

El usuario aclara que las boletas deben aparecer una debajo de la otra, nunca a la par. Aplicar a ambos formatos: PDF carta vertical (612 × 792 puntos), una columna y dos filas por página con guía horizontal de corte; Excel en una única pareja de columnas A:B, cada registro debajo del anterior y salto de impresión cada dos boletas. Mantener datos, firma amplia, última página parcial y preservación del Excel original completo. Esta distribución reemplaza la disposición horizontal de las secciones 17 y 18.
## Hojas por área y boletas adyacentes

Se reconocen las hojas cuyo nombre sea PLANILLA u HONORARIOS, o empiece por esos nombres seguidos de un espacio. Los formatos de Fibra, Masivos y Comercial se validan mediante perfiles explícitos de encabezados y columnas. No se infieren importes por semejanza de nombres ni se sustituyen errores de fórmulas por cero.

Cada hoja seleccionada genera su pestaña de boletas inmediatamente a la derecha de su origen. El nombre usa `BOLETAS DE PAGO {origen}`; si supera los 31 caracteres admitidos por Excel, usa `BOLETAS {origen}` y, para nombres aún más largos, un sufijo estable. Al regenerar se reemplaza la pestaña correspondiente, sin duplicarla. Los índices de nombres definidos y vistas se ajustan al nuevo orden conservando su asociación original.

La identidad de selección y vista previa incluye `source_sheet`, tipo, fila y código de empleado. Las identidades antiguas sin hoja solo se aceptan si identifican un único registro. Los PDF se separan por hoja de origen y mantienen dos boletas verticales por página carta. La exportación combinada contiene el libro original actualizado y esos PDF.

