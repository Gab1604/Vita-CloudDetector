from __future__ import annotations

from pathlib import Path

import numpy as np
from omnicloudmask import load_s2

from .config import DetectorConfig
from .core import run_array
from .models import DetectionResult


def run_sentinel2(
    input_path: Path,
    output_dir: Path,
    config: DetectorConfig | None = None,
) -> DetectionResult:
    """Run the frozen OmniCloudMask V4 pipeline on Sentinel-2 L1C/L2A SAFE data."""
    config = config or DetectorConfig()
    input_path = Path(input_path)
    output_dir = Path(output_dir)

    if not input_path.exists():
        raise FileNotFoundError(input_path)

    image_rgn, profile = load_s2(
        input_path=input_path,
        resolution=config.resolution,
        required_bands=["B04", "B03", "B8A"],
    )
    preview_rgb, preview_profile = load_s2(
        input_path=input_path,
        resolution=config.resolution,
        required_bands=["B04", "B03", "B02"],
    )

    image_rgn = np.asarray(image_rgn, dtype=np.float32)
    preview_rgb = np.asarray(preview_rgb, dtype=np.float32)

    if image_rgn.shape != preview_rgb.shape:
        raise RuntimeError(
            "Sentinel-2 R/G/NIR and true-colour arrays are not aligned: "
            f"{image_rgn.shape} vs {preview_rgb.shape}"
        )
    if profile.get("transform") != preview_profile.get("transform"):
        raise RuntimeError("Sentinel-2 R/G/NIR and true-colour transforms differ")

    source_metadata = {
        "sensor": "Sentinel-2",
        "product": "L1C_or_L2A_SAFE",
        "input_path": str(input_path),
        "target_resolution": config.resolution,
        "omnicloudmask_bands": ["B04", "B03", "B8A"],
        "preview_bands": ["B04", "B03", "B02"],
    }

    return run_array(
        image_rgn=image_rgn,
        profile=profile,
        output_dir=output_dir,
        config=config,
        preview_rgb=preview_rgb,
        source_metadata=source_metadata,
    )
