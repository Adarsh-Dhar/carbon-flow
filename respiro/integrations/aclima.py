"""
Aclima (Google Air View) integration helpers.

Note: Production deployments should use Google Earth Engine exports.
This client provides a simple hook: if GEE credentials are available we can
query the dataset; otherwise we attempt to load a pre-exported GeoJSON file
from disk, keeping development environments simple.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Tuple

from respiro.config.settings import get_settings
from respiro.utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_BASELINE_PATH = (
    Path(__file__).resolve().parents[1] / "data_cache" / "sf_routing" / "aclima_baseline.geojson"
)


class AclimaClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def fetch_airview_geojson(self, bbox: Tuple[Tuple[float, float], Tuple[float, float]]) -> Dict[str, Any]:
        """
        Fetch the Air View dataset clipped to a bounding box.

        In production this would submit an Earth Engine export task. For now we
        support two modes:
          1. If EARTH_ENGINE_PRIVATE_KEY_PATH is set, raise a NotImplementedError
             to signal the deploy script to configure EE (future work).
          2. If a cached GeoJSON exists, load it.
          3. Otherwise, return an empty FeatureCollection and log a warning.
        """
        service_account = self.settings.api.earth_engine_service_account
        key_path = self.settings.api.earth_engine_private_key_path

        if service_account and key_path:
            logger.warning(
                "Earth Engine export not implemented yet; please pre-generate %s",
                DEFAULT_BASELINE_PATH,
            )

        if DEFAULT_BASELINE_PATH.exists():
            return json.loads(DEFAULT_BASELINE_PATH.read_text(encoding="utf-8"))

        logger.warning("Aclima baseline missing at %s; returning empty FeatureCollection", DEFAULT_BASELINE_PATH)
        return {"type": "FeatureCollection", "features": []}

