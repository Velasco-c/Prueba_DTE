"""Loader incremental transaccional para el padrón electoral."""
from __future__ import annotations

from datetime import date, datetime
from typing import Iterable

from psycopg2 import sql
from psycopg2.extras import execute_values

from src.loaders.base import BaseLoader
from src.utils.db import get_connection
from src.utils.logger import get_logger

logger = get_logger(__name__)


class IncrementalLoader(BaseLoader):
    """Aplica fotografías diarias del padrón con UPSERT y marca de agua.

    Los registros ausentes en una fotografía no se borran. Una baja se cuenta
    cuando un registro existente cambia a `suspendido` o `fallecido`.
    """

    def __init__(self, table: str, natural_key: list[str], fecha: str) -> None:
        super().__init__(table, natural_key)
        try:
            self.process_date = date.fromisoformat(fecha)
        except ValueError as exc:
            raise ValueError("fecha debe tener formato YYYY-MM-DD") from exc
        if not natural_key:
            raise ValueError("Se requiere al menos una llave natural")

        self.process_name = table.rsplit(".", 1)[-1]
        self.last_metrics = {
            "altas": 0,
            "cambios": 0,
            "bajas": 0,
            "omitido_por_marca_de_agua": False,
        }

    @staticmethod
    def _table_identifier(table: str) -> sql.Identifier:
        parts = table.split(".")
        if len(parts) not in (1, 2) or any(not part for part in parts):
            raise ValueError(f"Nombre de tabla inválido: {table}")
        return sql.Identifier(*parts)

    def _deduplicate(self, records: Iterable[dict]) -> list[dict]:
        """Conserva la última fila repetida del archivo por llave natural."""
        unique_records: dict[tuple, dict] = {}
        for record in records:
            missing = [field for field in self.natural_key if field not in record]
            if missing:
                raise ValueError(f"Faltan campos de llave natural: {missing}")

            key = tuple(record[field] for field in self.natural_key)
            if any(
                value is None or (isinstance(value, str) and not value.strip())
                for value in key
            ):
                raise ValueError("La llave natural no puede estar vacía")
            try:
                unique_records[key] = record
            except TypeError as exc:
                raise TypeError(
                    "Los campos de llave natural deben ser hashables"
                ) from exc
        return list(unique_records.values())

    def _latest_watermark(self, cursor) -> date | None:
        cursor.execute(
            """SELECT MAX(fecha)
               FROM electoral.carga_log
               WHERE proceso = %s
                 AND fecha ~ '^\\d{4}-\\d{2}-\\d{2}$'""",
            (self.process_name,),
        )
        stored_date = cursor.fetchone()[0]
        return date.fromisoformat(stored_date) if stored_date else None

    def _read_existing(
        self, cursor, connection, rows: list[dict], columns: list[str]
    ) -> dict:
        key_columns = list(self.natural_key)
        selected_columns = list(dict.fromkeys(key_columns + columns))
        values = [tuple(record[field] for field in key_columns) for record in rows]
        query = sql.SQL("SELECT {} FROM {} WHERE ({}) IN (%s)").format(
            sql.SQL(", ").join(map(sql.Identifier, selected_columns)),
            self._table_identifier(self.table),
            sql.SQL(", ").join(map(sql.Identifier, key_columns)),
        )
        existing_rows = execute_values(
            cursor,
            query.as_string(connection),
            values,
            template="(" + ", ".join(["%s"] * len(key_columns)) + ")",
            page_size=1000,
            fetch=True,
        )

        key_indexes = [selected_columns.index(field) for field in key_columns]
        return {
            tuple(row[index] for index in key_indexes): dict(zip(selected_columns, row))
            for row in existing_rows
        }

    def _classify(
        self, rows: list[dict], existing: dict, columns: list[str]
    ) -> dict[str, int]:
        counts = {"altas": 0, "cambios": 0, "bajas": 0}
        compared_columns = [
            column
            for column in columns
            if column not in self.natural_key and column != "created_at"
        ]

        for record in rows:
            key = tuple(record[field] for field in self.natural_key)
            previous = existing.get(key)
            if previous is None:
                counts["altas"] += 1
                continue

            changed = any(
                previous[column] != record.get(column)
                for column in compared_columns
            )
            if not changed:
                continue

            became_inactive = (
                "estado_registro" in record
                and record.get("estado_registro") in {"suspendido", "fallecido"}
                and previous.get("estado_registro")
                not in {"suspendido", "fallecido"}
            )
            counts["bajas" if became_inactive else "cambios"] += 1

        return counts

    def _upsert(self, cursor, connection, rows: list[dict], columns: list[str]) -> None:
        table_identifier = self._table_identifier(self.table)
        update_columns = [
            column
            for column in columns
            if column not in self.natural_key and column != "created_at"
        ]
        insert_sql = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
            table_identifier,
            sql.SQL(", ").join(map(sql.Identifier, columns)),
        )
        conflict_sql = sql.SQL(" ON CONFLICT ({}) ").format(
            sql.SQL(", ").join(map(sql.Identifier, self.natural_key))
        )
        if update_columns:
            assignments = sql.SQL(", ").join(
                sql.SQL("{} = EXCLUDED.{}").format(
                    sql.Identifier(column), sql.Identifier(column)
                )
                for column in update_columns
            )
            conflict_sql += sql.SQL("DO UPDATE SET {} ").format(assignments)
        else:
            conflict_sql += sql.SQL("DO NOTHING")

        values = [tuple(record.get(column) for column in columns) for record in rows]
        execute_values(
            cursor,
            (insert_sql + conflict_sql).as_string(connection),
            values,
            page_size=1000,
        )

    def load(self, records: Iterable[dict]) -> int:
        rows = self._deduplicate(records)
        if rows:
            columns = list(rows[0])
            if not set(self.natural_key).issubset(columns):
                raise ValueError("Los registros deben incluir la llave natural configurada")
            if any(set(record) != set(columns) for record in rows):
                raise ValueError("Todos los registros deben tener las mismas columnas")
        else:
            columns = []

        metrics = {"altas": 0, "cambios": 0, "bajas": 0}
        loaded = 0
        skipped = False
        with get_connection() as connection:
            with connection.cursor() as cursor:
                # Serializa cargas concurrentes del mismo proceso para que la
                # marca de agua y el UPSERT se decidan en el mismo orden.
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(hashtext(%s))",
                    (self.process_name,),
                )
                watermark = self._latest_watermark(cursor)
                if watermark is not None and self.process_date < watermark:
                    skipped = True
                    logger.warning(
                        "Carga omitida: fecha %s anterior a la marca de agua %s",
                        self.process_date,
                        watermark,
                    )
                else:
                    if rows:
                        existing = self._read_existing(cursor, connection, rows, columns)
                        metrics = self._classify(rows, existing, columns)
                        self._upsert(cursor, connection, rows, columns)
                        loaded = len(rows)

                    observation = (
                        f"altas={metrics['altas']}; cambios={metrics['cambios']}; "
                        f"bajas={metrics['bajas']}; filas={loaded}; "
                        f"ejecutado_en={datetime.now().isoformat(timespec='seconds')}"
                    )
                    cursor.execute(
                        """INSERT INTO electoral.carga_log (proceso, observacion, fecha)
                           VALUES (%s, %s, %s)""",
                        (self.process_name, observation, self.process_date.isoformat()),
                    )

        self.last_metrics = {
            **metrics,
            "omitido_por_marca_de_agua": skipped,
        }
        logger.info(
            "UPSERT en %s: filas=%d altas=%d cambios=%d bajas=%d omitido=%s",
            self.table,
            loaded,
            metrics["altas"],
            metrics["cambios"],
            metrics["bajas"],
            skipped,
        )
        return loaded
