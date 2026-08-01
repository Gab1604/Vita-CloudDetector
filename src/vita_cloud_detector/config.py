from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class DetectorConfig:
    """Runtime configuration for OmniCloudMask inference and scene decisions."""

    resolution: float = 10.0
    unusable_threshold: float = 0.40
    model_version: float = 4.0
    patch_size: int = 1000
    patch_overlap: int = 300
    batch_size: int = 1
    inference_device: str | None = None
    mosaic_device: str | None = None
    inference_dtype: str = "fp32"
    no_data_value: float = 0.0
    export_preview: bool = True

    def __post_init__(self) -> None:
        if self.resolution <= 0:
            raise ValueError("resolution must be greater than zero")
        if not 0.0 <= self.unusable_threshold <= 1.0:
            raise ValueError("unusable_threshold must be between 0 and 1")
        if self.patch_size < 32:
            raise ValueError("patch_size must be at least 32 pixels")
        if self.patch_overlap < 0 or self.patch_overlap >= self.patch_size:
            raise ValueError("patch_overlap must be >= 0 and smaller than patch_size")
        if self.batch_size < 1:
            raise ValueError("batch_size must be at least 1")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
