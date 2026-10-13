"""Punto de entrada del ETL.

Ejemplos de uso esperado:
    python main.py load-empadronados --fecha 2026-03-02
    python main.py load-empadronados --fecha 2026-03-03
"""
from __future__ import annotations

import argparse

from src.utils.logger import get_logger

logger = get_logger("main")


def cmd_load_empadronados(args: argparse.Namespace) -> None:
    from src.pipelines.empadronados_pipeline import build_empadronados_pipeline

    build_empadronados_pipeline(args.fecha).run()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ETL electoral")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("load-empadronados", help="Carga incremental del padrón")
    p.add_argument("--fecha", required=True, help="Fecha de proceso YYYY-MM-DD")
    p.set_defaults(func=cmd_load_empadronados)

    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    args.func(args)
