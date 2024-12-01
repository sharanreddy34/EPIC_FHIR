from __future__ import annotations

"""Runtime configuration loader for Epic FHIR pipeline.

Reads default values from `config/epic_fhir_settings.yaml` at the project root
and lets environment variables override them.  Uses `pydantic.BaseSettings` so
it also works seamlessly inside Foundry where secrets are passed via env vars.
"""

from pathlib import Path
from typing import Any, Dict
import os

import yaml
from pydantic import BaseSettings, Field, validator

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONFIG_FILE = _REPO_ROOT / "config" / "epic_fhir_settings.yaml"


class Settings(BaseSettings):
    """Configuration model for the pipeline."""

    base_url: str = Field(..., env="EPIC_BASE_URL")
    batch_size: int = Field(200, env="BATCH_SIZE")
    max_pages: int = Field(100, env="MAX_PAGES")

    # Spark configuration nested under `spark.conf` in YAML
    spark_conf: Dict[str, Any] = Field(default_factory=dict, exclude=True)

    class Config:
        env_file = ".env"
        case_sensitive = False

    @validator("spark_conf", pre=True, always=True)
    def _default_spark_conf(cls, v: Dict[str, Any] | None) -> Dict[str, Any]:
        """Provide sensible default Spark configuration if none supplied."""
        return v or {
            "spark.sql.extensions": "io.delta.sql.DeltaSparkSessionExtension",
            "spark.sql.catalog.spark_catalog": "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        }


# ---------------------------------------------------------------------------
# Module global singleton – load once at import time
# ---------------------------------------------------------------------------

def _load_yaml_settings() -> Dict[str, Any]:
    if not _CONFIG_FILE.exists():
        return {}
    with _CONFIG_FILE.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


_settings = Settings(**_load_yaml_settings())


def get_settings() -> Settings:
    """Return cached Settings instance."""

    return _settings 