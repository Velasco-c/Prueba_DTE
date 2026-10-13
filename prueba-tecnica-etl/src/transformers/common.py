"""Transformations of the electoral roll.

Cada transformación es una clase pequeña: recibe los registros (una lista de
diccionarios, uno por fila) y devuelve los registros ya transformados.
`TrimStrings` recorta los espacios de los campos de texto.

Los datos de origen traen inconsistencias reales (mayúsculas, valores escritos
de varias formas, fechas en dos formatos, campos vacíos, duplicados). Mira los
archivos de data/empadronados/ antes de escribir código.
"""
from __future__ import annotations

from datetime import datetime
from typing import Iterable

from src.transformers.base import BaseTransformer


class TrimStrings(BaseTransformer):
    """Ejemplo de referencia ya implementado: recorta espacios."""

    def transform(self, records: Iterable[dict]) -> Iterable[dict]:
        for r in records:
            yield {k: (v.strip() if isinstance(v, str) else v) for k, v in r.items()}


class StandardizeCategories(BaseTransformer):
    """Estandariza valores categóricos: sexo, estado_registro, rango_edad.

    `mapping` tiene la forma {columna: {valor_original: valor_estandar}}.
    Las claves se comparan sin distinguir mayúsculas ni espacios exteriores.
    Los valores vacíos quedan como None; los valores que no están en el
    mapeo se conservan recortados para no perder información de origen.
    """

    def __init__(self, mapping: dict[str, dict[str, str]]) -> None:
        self.mapping = mapping

    def transform(self, records: Iterable[dict]) -> Iterable[dict]:
        normalized_mapping = {
            field: {
                source.strip().casefold(): target
                for source, target in values.items()
            }
            for field, values in self.mapping.items()
        }

        for record in records:
            standardized = record.copy()
            for field, values in normalized_mapping.items():
                value = standardized.get(field)
                if not isinstance(value, str):
                    continue

                value = value.strip()
                if not value:
                    standardized[field] = None
                    continue

                standardized[field] = values.get(value.casefold(), value)

            yield standardized


class ParseDates(BaseTransformer):
    """Convierte fechas en formato mixto (YYYY-MM-DD y DD/MM/YYYY) a YYYY-MM-DD.

    Values that are empty or do not represent a valid date are set to None;
    la fila se conserva y no se carga una fecha inválida como si fuera válida.
    """

    def __init__(self, fields: list[str]) -> None:
        self.fields = fields

    def transform(self, records: Iterable[dict]) -> Iterable[dict]:
        formats = ("%Y-%m-%d", "%d/%m/%Y")

        for record in records:
            standardized = record.copy()
            for field in self.fields:
                value = standardized.get(field)
                if value is None:
                    continue
                if not isinstance(value, str):
                    continue

                value = value.strip()
                if not value:
                    standardized[field] = None
                    continue

                for date_format in formats:
                    try:
                        standardized[field] = datetime.strptime(
                            value, date_format
                        ).date().isoformat()
                        break
                    except ValueError:
                        continue
                else:
                    standardized[field] = None

            yield standardized


class Deduplicate(BaseTransformer):
    """Elimina filas repetidas según la llave (id_empadronado).
    """

    def __init__(self, key: list[str]) -> None:
        self.key = key

    def transform(self, records: Iterable[dict]) -> Iterable[dict]:
        seen: set[tuple] = set()

        for record in records:
            key_values = tuple(record.get(field) for field in self.key)
            if any(
                value is None or (isinstance(value, str) and not value.strip())
                for value in key_values
            ):
                yield record
                continue

            try:
                duplicate = key_values in seen
            except TypeError as exc:
                raise TypeError(
                    "Los campos de deduplicación deben ser hashables"
                ) from exc

            if duplicate:
                continue
            seen.add(key_values)
            yield record
