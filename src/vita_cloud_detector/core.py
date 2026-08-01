from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from omnicloudmask import __version__ as omnicloudmask_version
from omnicloudmask import predict_from_array
from PIL import Image
from rasterio.profiles import Profile

from .config import DetectorConfig
from .models import DetectionResult, OutputPaths

CLASS_NAMES = {
    0: "clear",
    1: "thick_cloud",
    2: "thin_cloud",
    3: "cloud_shadow",
}


def strict_valid_mask(image_rgn: np.ndarray) -> np.ndarray:
    """Return the project strict-valid mask for an R/G/NIR image."""
    if image_rgn.ndim != 3 or image_rgn.shape[0] != 3:
        raise ValueError("image_rgn must have shape (3, height, width) in Red/Green/NIR order")

    tiny = np.finfo(np.float32).tiny
    finite = np.all(np.isfinite(image_rgn), axis=0)
    return finite & np.all(image_rgn > tiny, axis=0)


def class_statistics(mask: np.ndarray, valid: np.ndarray) -> dict[str, Any]:
    if mask.shape != valid.shape:
        raise ValueError("mask and valid must have the same spatial shape")

    valid_count = int(np.count_nonzero(valid))
    counts = {
        class_id: int(np.count_nonzero(valid & (mask == class_id)))
        for class_id in CLASS_NAMES
    }

    def fraction(*class_ids: int) -> float:
        if valid_count == 0:
            return 0.0
        return sum(counts[class_id] for class_id in class_ids) / valid_count

    return {
        "valid_pixels": valid_count,
        "class_counts": {
            CLASS_NAMES[class_id]: counts[class_id] for class_id in CLASS_NAMES
        },
        "class_fractions": {
            CLASS_NAMES[class_id]: fraction(class_id) for class_id in CLASS_NAMES
        },
        "cloud_only_fraction": fraction(1, 2),
        "unusable_fraction": fraction(1, 2, 3),
    }


def _stretch_rgb(rgb: np.ndarray, valid: np.ndarray) -> np.ndarray:
    output = np.zeros((rgb.shape[1], rgb.shape[2], 3), dtype=np.uint8)

    for channel in range(3):
        values = rgb[channel][valid]
        if values.size == 0:
            continue

        low, high = np.quantile(values, [0.02, 0.98])
        if not np.isfinite(low) or not np.isfinite(high) or high <= low:
            continue

        scaled = np.clip((rgb[channel] - low) / (high - low), 0.0, 1.0)
        output[..., channel] = np.round(scaled * 255).astype(np.uint8)

    output[~valid] = 0
    return output


def _make_overlay(rgb_u8: np.ndarray, mask: np.ndarray, valid: np.ndarray) -> np.ndarray:
    overlay = rgb_u8.astype(np.float32)
    alpha = 0.50
    colours = {
        1: np.array([255, 255, 255], dtype=np.float32),
        2: np.array([0, 255, 255], dtype=np.float32),
        3: np.array([255, 0, 255], dtype=np.float32),
    }

    for class_id, colour in colours.items():
        selected = valid & (mask == class_id)
        overlay[selected] = (1.0 - alpha) * overlay[selected] + alpha * colour

    overlay[~valid] = 0
    return np.clip(overlay, 0, 255).astype(np.uint8)


def _write_uint8_raster(
    path: Path,
    array: np.ndarray,
    profile: Profile | dict[str, Any],
    *,
    nodata: int,
    description: str,
) -> None:
    export_profile = dict(profile)
    export_profile.update(
        driver="GTiff",
        count=1,
        dtype="uint8",
        nodata=nodata,
        compress="lzw",
    )

    with rasterio.open(path, "w", **export_profile) as dst:
        dst.write(array.astype(np.uint8, copy=False), 1)
        dst.set_band_description(1, description)


def run_array(
    image_rgn: np.ndarray,
    profile: Profile | dict[str, Any],
    output_dir: Path,
    config: DetectorConfig,
    *,
    preview_rgb: np.ndarray | None = None,
    source_metadata: dict[str, Any] | None = None,
) -> DetectionResult:
    """Run OmniCloudMask on an R/G/NIR array and export integration-ready products."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    image = np.asarray(image_rgn, dtype=np.float32).copy()
    valid = strict_valid_mask(image)
    image[:, ~valid] = config.no_data_value

    start = time.perf_counter()
    prediction = predict_from_array(
        image,
        patch_size=config.patch_size,
        patch_overlap=config.patch_overlap,
        batch_size=config.batch_size,
        inference_device=config.inference_device,
        mosaic_device=config.mosaic_device,
        inference_dtype=config.inference_dtype,
        export_confidence=False,
        no_data_value=config.no_data_value,
        apply_no_data_mask=True,
        model_version=config.model_version,
    )
    inference_seconds = time.perf_counter() - start

    expected_shape = (1, image.shape[1], image.shape[2])
    if prediction.shape != expected_shape:
        raise RuntimeError(
            f"Unexpected OmniCloudMask output shape {prediction.shape}; expected {expected_shape}"
        )

    mask = prediction[0].astype(np.uint8, copy=False)
    unexpected = np.setdiff1d(np.unique(mask[valid]), np.array([0, 1, 2, 3]))
    if unexpected.size:
        raise RuntimeError(f"Unexpected OmniCloudMask classes: {unexpected.tolist()}")

    cloud_classes = mask.copy()
    cloud_classes[~valid] = 255

    unusable = np.zeros(mask.shape, dtype=np.uint8)
    unusable[valid & np.isin(mask, [1, 2, 3])] = 1
    unusable[~valid] = 255

    clear = np.zeros(mask.shape, dtype=np.uint8)
    clear[valid & (mask == 0)] = 1
    clear[~valid] = 255

    valid_export = valid.astype(np.uint8)

    paths = OutputPaths(
        cloud_classes=output_dir / "cloud_classes.tif",
        unusable_mask=output_dir / "unusable_mask.tif",
        clear_mask=output_dir / "clear_mask.tif",
        valid_mask=output_dir / "valid_mask.tif",
        summary=output_dir / "summary.json",
        preview=(output_dir / "preview.png") if config.export_preview else None,
    )

    _write_uint8_raster(
        paths.cloud_classes,
        cloud_classes,
        profile,
        nodata=255,
        description="0=clear,1=thick_cloud,2=thin_cloud,3=cloud_shadow,255=nodata",
    )
    _write_uint8_raster(
        paths.unusable_mask,
        unusable,
        profile,
        nodata=255,
        description="0=usable,1=cloud_or_shadow,255=nodata",
    )
    _write_uint8_raster(
        paths.clear_mask,
        clear,
        profile,
        nodata=255,
        description="0=not_clear,1=clear_valid,255=nodata",
    )
    _write_uint8_raster(
        paths.valid_mask,
        valid_export,
        profile,
        nodata=0,
        description="0=invalid,1=valid",
    )

    statistics = class_statistics(mask, valid)
    decision = (
        "discard"
        if statistics["unusable_fraction"] >= config.unusable_threshold
        else "keep"
    )

    summary: dict[str, Any] = {
        "detector": "ViTA Cloud Detector",
        "omnicloudmask_package_version": omnicloudmask_version,
        "omnicloudmask_model_version": config.model_version,
        "configuration": config.to_dict(),
        "shape": {
            "height": int(image.shape[1]),
            "width": int(image.shape[2]),
        },
        "statistics": statistics,
        "decision": decision,
        "decision_rule": {
            "discard_when_unusable_fraction_gte": config.unusable_threshold,
        },
        "inference_seconds": inference_seconds,
        "source": source_metadata or {},
        "outputs": {
            "cloud_classes": str(paths.cloud_classes),
            "unusable_mask": str(paths.unusable_mask),
            "clear_mask": str(paths.clear_mask),
            "valid_mask": str(paths.valid_mask),
            "preview": str(paths.preview) if paths.preview else None,
        },
    }

    paths.summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if paths.preview is not None and preview_rgb is not None:
        rgb = np.asarray(preview_rgb, dtype=np.float32).copy()
        if rgb.shape != image.shape:
            raise ValueError("preview_rgb must have shape (3, height, width)")
        rgb[:, ~valid] = 0.0
        rgb_u8 = _stretch_rgb(rgb, valid)
        overlay = _make_overlay(rgb_u8, mask, valid)
        Image.fromarray(overlay).save(paths.preview)

    return DetectionResult(paths=paths, summary=summary)
