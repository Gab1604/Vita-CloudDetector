from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio

from .config import DetectorConfig
from .core import run_array
from .models import DetectionResult


def run_sentinel2_geotiff(
    input_path: Path,
    output_dir: Path,
    config: DetectorConfig | None = None,
    *,
    red_band: int = 1,
    green_band: int = 2,
    nir_band: int = 3,
    blue_band: int = 4,
) -> DetectionResult:
    """Run OmniCloudMask V4 on a Sentinel-2 GeoTIFF exported from GEE.

    The default expected band order is:

    1. Red   (Sentinel-2 B4)
    2. Green (Sentinel-2 B3)
    3. NIR   (Sentinel-2 B8A)
    4. Blue  (Sentinel-2 B2)
    """
    config = config or DetectorConfig()
    input_path = Path(input_path)
    output_dir = Path(output_dir)

    if not input_path.exists():
        raise FileNotFoundError(input_path)

    selected_bands = [red_band, green_band, nir_band, blue_band]

    with rasterio.open(input_path) as source:
        if source.crs is None:
            raise ValueError("Sentinel-2 GeoTIFF has no CRS")
        if source.transform is None:
            raise ValueError("Sentinel-2 GeoTIFF has no geotransform")
        if min(selected_bands) < 1 or max(selected_bands) > source.count:
            raise ValueError(
                f"Requested bands {selected_bands}, but the GeoTIFF has {source.count} bands"
            )

        data = source.read(selected_bands, out_dtype="float32")
        profile = source.profile.copy()

        source_metadata = {
            "sensor": "Sentinel-2",
            "product": "GEE_multiband_GeoTIFF",
            "input_path": str(input_path),
            "input_crs": str(source.crs),
            "resolution": [abs(source.transform.a), abs(source.transform.e)],
            "band_mapping": {
                "red_B4": red_band,
                "green_B3": green_band,
                "nir_B8A": nir_band,
                "blue_B2": blue_band,
            },
            "input_nodata": source.nodata,
        }

    image_rgn = np.stack([data[0], data[1], data[2]], axis=0)
    preview_rgb = np.stack([data[0], data[1], data[3]], axis=0)

    return run_array(
        image_rgn=image_rgn,
        profile=profile,
        output_dir=output_dir,
        config=config,
        preview_rgb=preview_rgb,
        source_metadata=source_metadata,
    )
