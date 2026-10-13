"""Validaciones de calidad de datos.  [TEMPLATE — completar]

Un registro que no pasa una validación NO debe desaparecer en silencio: se
descarta, se cuenta y se deja un log con el motivo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable


@dataclass
class ValidationResult:
    valid: list[dict] = field(default_factory=list)
    rejected: list[tuple[dict, str]] = field(default_factory=list)

    @property
    def summary(self) -> dict:
        return {"validos": len(self.valid), "rechazados": len(self.rejected)}


class Validator:
    """Aplica una lista de reglas y separa válidos de rechazados."""

    def __init__(self, rules: list[tuple[str, Callable[[dict], bool]]]) -> None:
        self.rules = rules

    def run(self, records: Iterable[dict]) -> ValidationResult:
        result = ValidationResult()
        for r in records:
            for name, rule in self.rules:
                if not rule(r):
                    result.rejected.append((r, name))
                    break
            else:
                result.valid.append(r)
        return result


# ---------------------------------------------------------------------------
# Reglas mínimas esperadas para el padrón (implementar, una función por regla
# que reciba un registro y devuelva True si es válido):
#   1. id_empadronado no vacío
#   2. estado_registro dentro de: activo, suspendido, fallecido
#   3. fecha_inscripcion con formato YYYY-MM-DD (ya transformada)
# Luego arma la lista [("nombre_de_la_regla", funcion), ...] y pásala a
# Validator(...) en el pipeline.
# ---------------------------------------------------------------------------
