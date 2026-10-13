# ETL — Sistema de análisis de resultados electorales

Repositorio base de la prueba técnica para **Ingeniero de Datos Junior**.
El enunciado completo está en [`ENUNCIADO.md`](ENUNCIADO.md).

> **Candidato:** este README es un punto de partida. Antes de entregar, actualiza
> la sección "Cómo ejecutar mi solución" (al final) para que un tercero pueda
> reproducir tu trabajo.

## Contenido del repositorio

```
.
├── ENUNCIADO.md              # qué se pide y cómo se evalúa
├── DECISIONES.md             # (a completar) supuestos, hallazgos y decisiones
├── data/
│   └── empadronados/         # fuente viva, un archivo por día (3 días)
├── docs/
│   ├── BASE_DE_DATOS.md      # DER + diccionario de datos + reglas de negocio
│   └── der_modelo_actual.dbml
├── sql/
│   └── 01_ddl_electoral.sql  # modelo entregado — no modificar
├── src/
│   ├── config/               # settings + config.yaml
│   ├── extractors/           # lectura de fuentes
│   ├── transformers/         # limpieza y estandarización
│   ├── loaders/              # carga incremental a PostgreSQL
│   ├── quality/              # validaciones
│   ├── pipelines/            # composición de los flujos
│   └── utils/                # logging y acceso a base de datos
├── main.py                   # CLI del ETL
├── docker-compose.yml
└── Dockerfile
```

## Requisitos

- Python 3.10+
- PostgreSQL 14+: vía Docker (recomendado, ver [Instalar y configurar Docker](#instalar-y-configurar-docker)) o instalado localmente
- Docker y Docker Compose (opcional si instalas PostgreSQL localmente)

## Puesta en marcha

### 1. Clonar y preparar el entorno

```bash
git clone <url-del-repo>
cd prueba-tecnica-etl

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # ajustar credenciales
```

### 2. Crear la base de datos

**Opción A — con Docker (recomendada; el DDL se ejecuta automáticamente al iniciar):**

Antes, instala y configura Docker siguiendo la sección
[Instalar y configurar Docker](#instalar-y-configurar-docker).

```bash
docker compose up -d postgres
docker compose logs -f postgres   # esperar "database system is ready"
```

**Opción B — PostgreSQL local (sin Docker):**

```bash
createdb electoral_db
psql -d electoral_db -f sql/01_ddl_electoral.sql
```

Si usas un usuario distinto al de `.env.example` (`etl_user`), ajusta
`POSTGRES_USER` y `POSTGRES_PASSWORD` en tu `.env`, o crea ese rol:

```bash
psql -d postgres -c "CREATE USER etl_user WITH PASSWORD 'cambiame' SUPERUSER;"
```

Verificar:

```bash
psql -d electoral_db -c "\dt electoral.*"
```

> No necesitas crear tablas nuevas: para la marca de agua puedes usar
> `electoral.carga_log`. Si creas alguna, documenta cómo se aplica.

### 3. Ejecutar la carga incremental del padrón

Un día a la vez, en orden:

```bash
python main.py load-empadronados --fecha 2026-03-02
python main.py load-empadronados --fecha 2026-03-03
python main.py load-empadronados --fecha 2026-03-04
```

## Estado de las partes

Marca lo que lograste y deja una nota si quedó parcial.

| Parte | Comando / lugar | Estado |
|---|---|---|
| 1. Data Transformation | `src/transformers/` | ✅ completed |
| 2. Carga incremental del padrón | `load-empadronados --fecha` | ✅ completada |
| 3. Análisis de la base de datos (opcional) | `DECISIONES.md`, sección 5 | ⬜ pendiente |

## Cómo ejecutar mi solución

Los pasos siguientes asumen que estás en la carpeta `prueba-tecnica-etl`, que
Docker está iniciado y que `.env` contiene las credenciales de PostgreSQL. Para
repetir los conteos indicados, usa una base vacía.

### 1. Preparar el entorno de Python

El proyecto usa Python 3.12 (como en `Dockerfile`) y las dependencias de
`requirements.txt`:

```bash
python3.12 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
```

### 2. Levantar PostgreSQL

```bash
docker compose up -d postgres
docker compose ps                 # esperar a que postgres aparezca como healthy
docker compose exec postgres psql -U etl_user -d electoral_db -c '\dt electoral.*'  # cambia usuario/base si editaste .env
```

El healthcheck apunta a la base `electoral_db`. El DDL crea el esquema y las
tablas cuando PostgreSQL inicializa un volumen vacío.

### 3. Procesar los archivos en orden

```bash
python main.py load-empadronados --fecha 2026-03-02
python main.py load-empadronados --fecha 2026-03-03
python main.py load-empadronados --fecha 2026-03-04
```

En una base vacía, el resultado esperado es 18,000 filas para el día 02,
18,131 para el día 03 y 18,277 para el día 04. El resumen informa también las
altas, los cambios y las transiciones a `suspendido` o `fallecido`.

### 4. Comprobar idempotencia y marca de agua

Reprocesar el día 04 no crea IDs nuevos ni cambia datos. Reprocesar el día 03
después del 04 se omite porque es anterior a la marca de agua:

```bash
python main.py load-empadronados --fecha 2026-03-04
python main.py load-empadronados --fecha 2026-03-03
```

La carga repetida del 04 debe informar 0 altas, 0 cambios y 0 bajas. La del 03
debe mostrar `omitido_por_marca_de_agua=True` y `cargados=0`.

### 5. Verificar filas únicas y ejecuciones registradas

```bash
docker compose exec postgres psql -U etl_user -d electoral_db -c "SELECT COUNT(*) AS filas, COUNT(DISTINCT id_empadronado) AS ids_unicos, COUNT(*) - COUNT(DISTINCT id_empadronado) AS duplicados FROM electoral.empadronados;"
docker compose exec postgres psql -U etl_user -d electoral_db -c "SELECT proceso, fecha, observacion FROM electoral.carga_log WHERE proceso = 'empadronados' ORDER BY fecha, id_log;"
```

Con las tres fuentes de ejemplo, la primera consulta debe mostrar 18,277 filas,
18,277 IDs únicos y 0 duplicados. `carga_log` guarda la fecha procesada y los
conteos de cada ejecución aceptada; una fecha anterior a la marca de agua se
omite y no se registra como carga procesada.

## Instalar y configurar Docker

Solo se necesita para levantar PostgreSQL con un comando. El ETL en sí se ejecuta
con Python en tu entorno virtual (pasos 1 y 3).

### 1. Instalar

| Sistema | Qué hacer |
|---|---|
| **macOS** | Descarga e instala [Docker Desktop](https://www.docker.com/products/docker-desktop/) (elige Apple Silicon o Intel según tu equipo). Alternativa con Homebrew: `brew install --cask docker`. Abre la app una vez para que termine de configurarse. |
| **Windows 10/11** | Instala [Docker Desktop](https://www.docker.com/products/docker-desktop/). Activa **WSL 2** cuando el instalador lo pida (si no está, abre PowerShell como administrador y ejecuta `wsl --install`, luego reinicia). Abre la app una vez. |
| **Linux (Ubuntu/Debian)** | Sigue la guía oficial de [Docker Engine](https://docs.docker.com/engine/install/ubuntu/) e instala también el plugin `docker-compose-plugin`. Para usar Docker sin `sudo`: `sudo usermod -aG docker $USER` y cierra y vuelve a abrir sesión. |

### 2. Verificar la instalación

Con Docker Desktop abierto y mostrando "running" (en Linux, con el servicio activo):

```bash
docker --version
docker compose version
docker run --rm hello-world
```

Los tres comandos deben ejecutarse sin error. Si `docker compose` no existe,
tu versión es antigua: actualiza Docker (necesitas Compose v2).

### 3. Configurar el proyecto

1. Copia las variables de entorno: `cp .env.example .env`.
2. `docker-compose.yml` lee `POSTGRES_DB`, `POSTGRES_USER` y `POSTGRES_PASSWORD`
   de ese `.env`; el ETL en Python lee las mismas variables. Si cambias una,
   cambia el `.env` y ambos quedan consistentes.
3. Levanta la base: `docker compose up -d postgres`.
4. Comprueba que está lista y con las tablas creadas:

```bash
docker compose ps                  # el servicio debe estar "healthy"
docker compose exec postgres psql -U etl_user -d electoral_db -c "\dt electoral.*"
```

(Si cambiaste el usuario o la base en `.env`, usa esos valores en el comando.)

### Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `Cannot connect to the Docker daemon` | Docker Desktop no está abierto (o el servicio no está activo en Linux). Ábrelo y espera a que diga "running". |
| `port is already allocated` / puerto 5432 ocupado | Ya tienes un PostgreSQL local corriendo. Deténlo, o cambia el puerto publicado en `docker-compose.yml` (por ejemplo `"5433:5432"`) y `POSTGRES_PORT=5433` en `.env`. |
| Cambié el DDL (`sql/01_ddl_electoral.sql`) y no se refleja | El script solo corre cuando el volumen está vacío. Reinicia la base: `docker compose down -v && docker compose up -d postgres`. **Esto borra todos los datos cargados.** |
| El ETL no conecta a la base | Revisa que `POSTGRES_HOST=localhost` y que el puerto y las credenciales del `.env` coinciden con el contenedor. |
| Quiero apagar todo | `docker compose down` (conserva los datos) o `docker compose down -v` (los borra). |
