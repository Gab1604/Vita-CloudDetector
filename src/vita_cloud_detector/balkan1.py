from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform, reproject, transform_bounds

from .config import DetectorConfig
from .core import run_array
from .models import DetectionResult

# Confirmed Balkan-1 L1ORT mapping:
# 1=Blue, 2=Green, 3=Red, 4=NIR, 5=Panchromatic
BLUE_BAND = 1
GREEN_BAND = 2
RED_BAND = 3
NIR_BAND = 4


def choose_utm_crs(source_crs: CRS, bounds: rasterio.coords.BoundingBox) -> CRS:
    west, south, east, north = transform_bounds(
        source_crs,
        CRS.from_epsg(4326),
        *bounds,
        densify_pts=21,
    )
    longitude = (west + east) / 2.0
    latitude = (south + north) / 2.0

    zone = int(math.floor((longitude + 180.0) / 6.0) + 1)
    zone = max(1, min(zone, 60))
    epsg = 32600 + zone if latitude >= 0 else 32700 + zone
    return CRS.from_epsg(epsg)


def _target_grid(
    source: rasterio.io.DatasetReader,
    reference_path: Path | None,
    resolution: float,
) -> tuple[dict[str, Any], CRS, Any, int, int, str]:
    if reference_path is not None:
        with rasterio.open(reference_path) as reference:
            if reference.crs is None:
                raise ValueError("Reference raster has no CRS")
            profile = reference.profile.copy()
            return (
                profile,
                reference.crs,
                reference.transform,
                reference.width,
                reference.height,
                str(reference_path),
            )

    if source.crs is None:
        raise ValueError("Balkan-1 L1ORT source has no CRS")

    target_crs = choose_utm_crs(source.crs, source.bounds)
    transform, width, height = calculate_default_transform(
        source.crs,
        target_crs,
        source.width,
        source.height,
        *source.bounds,
        resolution=resolution,
    )
    profile = source.profile.copy()
    profile.update(
        crs=target_crs,
        transform=transform,
        width=width,
        height=height,
    )
    return profile, target_crs, transform, width, height, "automatic_utm_grid"


def run_balkan1(
    input_path: Path,
    output_dir: Path,
    config: DetectorConfig | None = None,
    *,
    reference_path: Path | None = None,
) -> DetectionResult:
    """Run the frozen OmniCloudMask V4 pipeline on a Balkan-1 L1ORT GeoTIFF."""
    config = config or DetectorConfig()
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    reference_path = Path(reference_path) if reference_path is not None else None

    if not input_path.exists():
        raise FileNotFoundError(input_path)
    if reference_path is not None and not reference_path.exists():
        raise FileNotFoundError(reference_path)

    with rasterio.open(input_path) as source:
        if source.count < 4:
            raise ValueError(
                f"Expected at least 4 Balkan-1 bands, found {source.count}"
            )
        if source.crs is None:
            raise ValueError("Balkan-1 L1ORT source has no CRS")

        (
            target_profile,
            target_crs,
            target_transform,
            target_width,
            target_height,
            grid_source,
        ) = _target_grid(source, reference_path, config.resolution)

        destination = np.zeros((4, target_height, target_width), dtype=np.float32)
        source_bands = [RED_BAND, GREEN_BAND, NIR_BAND, BLUE_BAND]
        source_nodata = source.nodata if source.nodata is not None else config.no_data_value

        for destination_index, source_band in enumerate(source_bands):
            reproject(
                source=rasterio.band(source, source_band),
                destination=destination[destination_index],
                src_transform=source.transform,
                src_crs=source.crs,
                src_nodata=source_nodata,
                dst_transform=target_transform,
                dst_crs=target_crs,
                dst_nodata=config.no_data_value,
                resampling=Resampling.bilinear,
                num_threads=2,
                init_dest_nodata=True,
            )

        source_metadata = {
            "sensor": "Balkan-1",
            "product": "L1ORT",
            "input_path": str(input_path),
            "input_crs": str(source.crs),
            "target_crs": str(target_crs),
            "target_resolution": config.resolution,
            "grid_source": grid_source,
            "band_mapping": {
                "blue": BLUE_BAND,
                "green": GREEN_BAND,
                "red": RED_BAND,
                "nir": NIR_BAND,
            },
        }

    image_rgn = np.stack(
        [destination[0], destination[1], destination[2]],
        axis=0,
    )
    preview_rgb = np.stack(
        [destination[0], destination[1], destination[3]],
        axis=0,
    )

    return run_array(
        image_rgn=image_rgn,
        profile=target_profile,
        output_dir=output_dir,
        config=config,
        preview_rgb=preview_rgb,
        source_metadata=source_metadata,
    )
