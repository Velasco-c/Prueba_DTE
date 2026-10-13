# Decisiones y supuestos

> Plantilla a completar por el candidato. No hace falta que sea larga; sí que
> sea específica: ejemplos reales de los datos, no frases generales.

## 1. Hallazgos en los datos

Una fila por problema que encontraste en los archivos del padrón.

| # | Columna | Qué encontraste | Ejemplo | Qué hiciste | Por qué |
|---|---|---|---|---|---|
| 1 | | | | | |

## 2. Decisiones

Responde en pocas líneas cada una:

- Si dos filas tienen el mismo `id_empadronado` pero difieren, ¿cuál dejaste y por qué?
- ¿Qué haces con un registro inválido (por ejemplo, una fecha que no se puede leer)?
- ¿Cómo evitas duplicados al cargar? ¿Qué pasa si corres la misma fecha dos veces?
- **Pregunta de razonamiento (no hace falta programarla):** si ya cargaste el
  día 04 y luego vuelves a procesar el día 03, ¿qué queda en la base? ¿Es un
  problema? ¿Cómo lo evitarías?

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
