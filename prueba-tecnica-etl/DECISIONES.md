# Decisiones y supuestos

> Plantilla a completar por el candidato. No hace falta que sea larga; sí que
> sea específica: ejemplos reales de los datos, no frases generales.

## 1. Hallazgos en los datos

Una fila por problema que encontraste en los archivos del padrón.

| # | Columna | Qué encontraste | Ejemplo | Qué hiciste | Por qué |
|---|---|---|---|---|---|
| 1 | `sexo` | Mayúsculas y abreviaturas mezcladas; también hay valores vacíos | `M`, `m`, `MASCULINO`, vacío | Convertí masculino a `M`, femenino a `F` y vacío a `NULL` | Unifica categorías sin inventar el sexo faltante |
| 2 | `rango_edad` | Dos formas para algunos rangos | `18 a 25` / `18-25`, `mayor de 60` / `61+` | Normalicé a `18-25`, `26-35` y `61+`, respectivamente | Facilita agrupar y comparar |
| 3 | `estado_registro` | Diferencias de mayúsculas | `ACTIVO` / `activo` | Conservé los valores válidos en minúscula | El dominio documentado es `activo`, `suspendido`, `fallecido` |
| 4 | `fecha_inscripcion` | Formatos ISO y `DD/MM/YYYY` | `2004-02-03` / `04/06/2004` | Convertí fechas válidas a `YYYY-MM-DD`; vacías o inválidas quedan `NULL` | Mantiene un único formato y evita cargar fechas imposibles como texto |
| 5 | `id_empadronado` | 25 filas repetidas exactamente por archivo diario | El mismo ID y los mismos campos aparecen dos veces | Conservé la primera fila por llave dentro del archivo | Elimina duplicados de la fuente sin alterar el orden |

## 2. Decisiones

Responde en pocas líneas cada una:

- Si dos filas tienen el mismo `id_empadronado` pero difieren, ¿cuál dejaste y por qué?
  Se conserva la primera fila del archivo. En los duplicados encontrados en estas
  fuentes, las filas eran idénticas; si aparecen conflictos, esta política
  prioriza el orden de la fuente y debería revisarse con una regla de negocio.
- ¿Qué haces con un registro inválido (por ejemplo, una fecha que no se puede leer)?
  La fecha queda como `NULL`; el transformador no elimina la fila.
- ¿Cómo evitas duplicados al cargar? ¿Qué pasa si corres la misma fecha dos veces?
  `id_empadronado` es la llave del `UPSERT`. La misma fecha se puede reprocesar:
  se actualizan las mismas filas y no se insertan duplicados. `load()` devuelve
  la cantidad de llaves únicas procesadas.
- **Pregunta de razonamiento (no hace falta programarla):** si ya cargaste el
  día 04 y luego vuelves a procesar el día 03, ¿qué queda en la base? ¿Es un
  problema? ¿Cómo lo evitarías?
  Queda el estado del día 04. La fecha máxima de `electoral.carga_log` funciona
  como marca de agua y el día 03 se omite para no pisar datos nuevos.

Cada ejecución registra en `carga_log.fecha` la fecha de proceso y en
`observacion` las filas procesadas, altas, cambios, bajas y la hora de ejecución.
Se cuenta como baja un registro existente que cambia a `suspendido` o
`fallecido`; no se borra a quienes faltan en una fotografía.

Consultas para revisar el estado después de cargar:

```sql
SELECT COUNT(*) AS filas,
       COUNT(DISTINCT id_empadronado) AS ids_unicos
FROM electoral.empadronados;

SELECT proceso, fecha, observacion
FROM electoral.carga_log
WHERE proceso = 'empadronados'
ORDER BY fecha, id_log;
```

## 3. Supuestos

| # | Supuesto | Motivo |
|---|---|---|
| 1 | | |

## 4. Qué no alcancé a hacer

| # | Pendiente | Cómo lo abordaría |
|---|---|---|
| 1 | | |

## 5. Análisis de la base de datos (opcional)

Si te sobra tiempo: mira `sql/01_ddl_electoral.sql` y `docs/BASE_DE_DATOS.md` y
anota entre 3 y 5 problemas del modelo, sobre todo los que notaste al cargar el
padrón. Una línea por problema, qué consecuencia tiene y una mejora posible. No
se pide un diagrama ni un modelo nuevo.

| # | Problema | Consecuencia | Mejora posible |
|---|---|---|---|
| 1 | | | |
