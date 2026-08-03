from __future__ import annotations

import argparse
import json
from pathlib import Path

from .balkan1 import run_balkan1
from .config import DetectorConfig
from .sentinel2 import run_sentinel2
from .sentinel2_geotiff import run_sentinel2_geotiff


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--input", required=True, type=Path, help="Input product path")
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory where masks and summary files are written",
    )
    parser.add_argument("--resolution", type=float, default=10.0)
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.40,
        help="Discard scene when unusable fraction is greater than or equal to this value",
    )
    parser.add_argument("--model-version", type=float, default=4.0)
    parser.add_argument("--patch-size", type=int, default=1000)
    parser.add_argument("--patch-overlap", type=int, default=300)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument(
        "--device",
        default=None,
        choices=["cpu", "cuda", "mps"],
        help="Inference device. Omit to let PyTorch choose automatically.",
    )
    parser.add_argument(
        "--mosaic-device",
        default=None,
        choices=["cpu", "cuda", "mps"],
        help="Device used to mosaic patch predictions. Defaults to inference device.",
    )
    parser.add_argument(
        "--dtype",
        default="fp32",
        choices=["fp32", "fp16", "bf16"],
    )
    parser.add_argument(
        "--no-preview",
        action="store_true",
        help="Skip preview.png generation",
    )


def _build_config(args: argparse.Namespace) -> DetectorConfig:
    return DetectorConfig(
        resolution=args.resolution,
        unusable_threshold=args.threshold,
        model_version=args.model_version,
        patch_size=args.patch_size,
        patch_overlap=args.patch_overlap,
        batch_size=args.batch_size,
        inference_device=args.device,
        mosaic_device=args.mosaic_device,
        inference_dtype=args.dtype,
        export_preview=not args.no_preview,
    )


def _print_result(summary: dict) -> None:
    statistics = summary["statistics"]
    compact = {
        "decision": summary["decision"],
        "unusable_fraction": statistics["unusable_fraction"],
        "cloud_only_fraction": statistics["cloud_only_fraction"],
        "class_fractions": statistics["class_fractions"],
        "valid_pixels": statistics["valid_pixels"],
        "inference_seconds": summary["inference_seconds"],
        "outputs": summary["outputs"],
    }
    print(json.dumps(compact, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vita-cloud-detector",
        description="Cloud and cloud-shadow detection for Balkan-1 and Sentinel-2",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    balkan = subparsers.add_parser("balkan1", help="Process a Balkan-1 L1ORT GeoTIFF")
    _add_common_arguments(balkan)
    balkan.add_argument(
        "--reference",
        type=Path,
        default=None,
        help="Optional reference raster defining the exact output grid",
    )

    sentinel = subparsers.add_parser("sentinel2", help="Process a Sentinel-2 SAFE product")
    _add_common_arguments(sentinel)

    sentinel_geotiff = subparsers.add_parser(
        "sentinel2-geotiff",
        help="Process a Sentinel-2 multiband GeoTIFF exported from Google Earth Engine",
    )
    _add_common_arguments(sentinel_geotiff)
    sentinel_geotiff.add_argument("--red-band", type=int, default=1)
    sentinel_geotiff.add_argument("--green-band", type=int, default=2)
    sentinel_geotiff.add_argument("--nir-band", type=int, default=3)
    sentinel_geotiff.add_argument("--blue-band", type=int, default=4)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config = _build_config(args)

    if args.command == "balkan1":
        result = run_balkan1(
            input_path=args.input,
            output_dir=args.output_dir,
            config=config,
            reference_path=args.reference,
        )
    elif args.command == "sentinel2":
        result = run_sentinel2(
            input_path=args.input,
            output_dir=args.output_dir,
            config=config,
        )
    elif args.command == "sentinel2-geotiff":
        result = run_sentinel2_geotiff(
            input_path=args.input,
            output_dir=args.output_dir,
            config=config,
            red_band=args.red_band,
            green_band=args.green_band,
            nir_band=args.nir_band,
            blue_band=args.blue_band,
        )
    else:
        parser.error(f"Unsupported command: {args.command}")
        return

    _print_result(result.summary)


if __name__ == "__main__":
    main()
