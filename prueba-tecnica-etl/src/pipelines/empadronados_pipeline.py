"""Flujo incremental para cargar únicamente electoral.empadronados."""
from __future__ import annotations

from src.config.settings import PROJECT_ROOT, source_config
from src.extractors.csv_extractor import CSVExtractor
from src.loaders.postgres_loader import IncrementalLoader
from src.pipelines.base_pipeline import Pipeline
from src.transformers.base import TransformerPipeline
from src.transformers.common import StandardizeCategories, TrimStrings


def build_empadronados_pipeline(fecha: str) -> Pipeline:
    """Construye el flujo para una fecha de proceso.

    Args:
        fecha: fecha de corte en formato YYYY-MM-DD.

    La fuente y el destino se toman de la configuración `empadronados`;
    este flujo no carga las demás tablas del esquema electoral.
    """
    cfg = source_config("empadronados")
    path = PROJECT_ROOT / cfg["path_pattern"].format(fecha=fecha.replace("-", ""))

    extractor = CSVExtractor(path)
    transformer = TransformerPipeline(
        TrimStrings(),
        StandardizeCategories(
            {
                "sexo": {
                    "m": "M",
                    "masculino": "M",
                    "f": "F",
                    "femenino": "F",
                },
                "estado_registro": {
                    "activo": "activo",
                    "suspendido": "suspendido",
                    "fallecido": "fallecido",
                },
                "rango_edad": {
                    "18-25": "18-25",
                    "18 a 25": "18-25",
                    "26-35": "26-35",
                    "26 a 35": "26-35",
                    "36-45": "36-45",
                    "46-60": "46-60",
                    "61+": "61+",
                    "mayor de 60": "61+",
                },
            }
        ),
    )
    validator = None  # TODO (opcional): Validator([...])
    loader = IncrementalLoader(cfg["target_table"], cfg["natural_key"], fecha)

    pipeline = Pipeline(extractor, transformer, loader, validator)
    pipeline.name = "empadronados"
    return pipeline
