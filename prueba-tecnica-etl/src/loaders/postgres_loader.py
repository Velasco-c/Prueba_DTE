"""Loader de PostgreSQL para el padrón electoral."""
from __future__ import annotations

from typing import Iterable

from psycopg2 import sql
from psycopg2.extras import execute_values

from src.loaders.base import BaseLoader
from src.utils.db import get_connection
from src.utils.logger import get_logger

logger = get_logger(__name__)


class IncrementalLoader(BaseLoader):
    """Actualización diaria del padrón.

    Cada archivo es una fotografía completa del padrón a una fecha. Debe
    manejar:
      - altas: empadronados que no existían en la tabla -> se insertan
      - cambios: empadronados que ya existían con datos distintos (p. ej. un
        traslado de centro/mesa) -> se actualizan
      - bajas: empadronados que pasan a suspendido / fallecido -> se actualiza
        su estado (no se borra a nadie)

    Usa UPSERT sobre el destino configurado. El loader solo escribe en
    `self.table`; no modifica tablas auxiliares ni catálogos.
    """

    def __init__(self, table: str, natural_key: list[str], fecha: str) -> None:
        super().__init__(table, natural_key)
        self.fecha = fecha

    def load(self, records: Iterable[dict]) -> int:
        # Si una llave aparece varias veces en el mismo archivo, conserva la
        # última fila, igual que una actualización más reciente del padrón.
        unique_records: dict[tuple, dict] = {}
        for record in records:
            key = tuple(record.get(field) for field in self.natural_key)
            unique_records[key] = record

        if not unique_records:
            return 0

        rows = list(unique_records.values())
        columns = list(rows[0])
        if not self.natural_key or not set(self.natural_key).issubset(columns):
            raise ValueError("Los registros deben incluir la llave natural configurada")
        if any(set(record) != set(columns) for record in rows):
            raise ValueError("Todos los registros deben tener las mismas columnas")

        table_parts = self.table.split(".")
        if len(table_parts) == 2:
            table_identifier = sql.Identifier(*table_parts)
        elif len(table_parts) == 1:
            table_identifier = sql.Identifier(table_parts[0])
        else:
            raise ValueError(f"Nombre de tabla inválido: {self.table}")

        update_columns = [column for column in columns if column not in self.natural_key]
        insert_sql = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
            table_identifier,
            sql.SQL(", ").join(map(sql.Identifier, columns)),
        )
        conflict_sql = sql.SQL(" ON CONFLICT ({}) ").format(
            sql.SQL(", ").join(map(sql.Identifier, self.natural_key))
        )
        if update_columns:
            conflict_sql += sql.SQL("DO UPDATE SET {} ").format(
                sql.SQL(", ").join(
                    sql.SQL("{} = EXCLUDED.{}").format(
                        sql.Identifier(column), sql.Identifier(column)
                    )
                    for column in update_columns
                )
            )
        else:
            conflict_sql += sql.SQL("DO NOTHING")

        values = [tuple(record.get(column) for column in columns) for record in rows]
        with get_connection() as connection:
            with connection.cursor() as cursor:
                query = (insert_sql + conflict_sql).as_string(connection)
                execute_values(
                    cursor,
                    query,
                    values,
                    page_size=1000,
                )

        logger.info("UPSERT en %s: %d registros", self.table, len(rows))
        return len(rows)


