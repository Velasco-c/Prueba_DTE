"""Contrato de carga.

Un loader sabe ESCRIBIR en un destino y nada más: no limpia ni valida.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable


class BaseLoader(ABC):
    def __init__(self, table: str, natural_key: list[str]) -> None:
        self.table = table
        self.natural_key = natural_key

    @abstractmethod
    def load(self, records: Iterable[dict]) -> int:
        """Carga los registros y devuelve la cantidad afectada."""
        raise NotImplementedError
