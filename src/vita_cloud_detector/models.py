from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class OutputPaths:
    cloud_classes: Path
    unusable_mask: Path
    clear_mask: Path
    valid_mask: Path
    summary: Path
    preview: Path | None


@dataclass(frozen=True)
class DetectionResult:
    paths: OutputPaths
    summary: dict[str, Any]
