# ViTA Cloud Detector

Cloud and cloud-shadow detection module for the **ViTA / SpaceChallenges26** Earth-observation pipeline.

The repository provides a reproducible integration layer around [OmniCloudMask](https://github.com/DPIRD-DMA/OmniCloudMask) for:

- **Balkan-1 L1ORT** multispectral GeoTIFF products;
- **Sentinel-2 L1C/L2A SAFE** products;
- generation of categorical and binary cloud masks;
- scene-level cloud statistics and keep/discard decisions;
- future integration with the crop detector.

## Output classes

| Value | Meaning |
|---:|---|
| `0` | Clear |
| `1` | Thick cloud |
| `2` | Thin cloud |
| `3` | Cloud shadow |
| `255` | No-data in exported GeoTIFF masks |

The derived `unusable` mask is the union of classes `1`, `2`, and `3`.

## Frozen baseline

The validated baseline currently used by the project is:

- OmniCloudMask package: **1.7.1**
- OmniCloudMask model: **V4**
- upstream reference commit: `fbc6d3f5665eb3425fb2474cb3e6f574e2e71a1b`
- inference: CPU/CUDA, FP32 by default
- requested patch size: `1000`
- patch overlap: `300`
- no-data value: `0`
- Balkan-1 resolution: `10 m`

The upstream model weights are **not stored in this repository**. They are downloaded by OmniCloudMask on first use.

## Installation

Python 3.10–3.12 is recommended.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

## Balkan-1

Balkan-1 L1ORT band mapping used by the project:

| L1ORT band | Spectral channel |
|---:|---|
| 1 | Blue |
| 2 | Green |
| 3 | Red |
| 4 | NIR |
| 5 | Panchromatic |

OmniCloudMask receives `[Red, Green, NIR] = [3, 2, 4]`.

Run on one L1ORT scene:

```powershell
vita-cloud-detector balkan1 `
  --input "C:\path\to\3425_L1ORT.tif" `
  --output-dir ".\outputs\3425" `
  --resolution 10 `
  --threshold 0.40
```

The Balkan-1 command:

1. chooses the scene UTM CRS automatically;
2. reprojects the L1ORT product to a 10 m grid;
3. applies strict no-data cleaning;
4. runs OmniCloudMask V4;
5. exports categorical and binary masks;
6. reports class percentages and the scene decision.

A reference raster can be supplied to force exact alignment with another product:

```powershell
vita-cloud-detector balkan1 `
  --input "C:\path\to\3425_L1ORT.tif" `
  --reference "C:\path\to\3425_reference.tif" `
  --output-dir ".\outputs\3425"
```

## Sentinel-2

Run on a Sentinel-2 L1C or L2A SAFE product:

```powershell
vita-cloud-detector sentinel2 `
  --input "C:\path\to\S2_scene.SAFE" `
  --output-dir ".\outputs\sentinel2_scene" `
  --resolution 10 `
  --threshold 0.40
```

The Sentinel-2 adapter uses the official OmniCloudMask loader with:

- `B04` — Red;
- `B03` — Green;
- `B8A` — NIR.

## Produced files

Each run creates:

- `cloud_classes.tif` — classes `0/1/2/3`, with `255` for no-data;
- `unusable_mask.tif` — binary mask, `1 = cloud/thin cloud/shadow`;
- `clear_mask.tif` — binary mask, `1 = clear and valid`;
- `summary.json` — percentages, configuration, runtime and decision;
- `preview.png` — visual overlay when preview bands are available.

## Python API

```python
from pathlib import Path
from vita_cloud_detector import DetectorConfig, run_balkan1

result = run_balkan1(
    input_path=Path(r"C:\data\3425_L1ORT.tif"),
    output_dir=Path(r"C:\outputs\3425"),
    config=DetectorConfig(unusable_threshold=0.40),
)

print(result.summary["decision"])
print(result.paths.cloud_classes)
```

## Crop-detector integration

The intended Phase-1 interface is:

```text
multispectral image
        ↓
ViTA Cloud Detector
        ↓
cloud classes + unusable mask + clear mask
        ↓
if unusable >= threshold: discard
else: crop detector
        ↓
crop percentage computed only on clear, valid pixels
```

Cloud pixels should remain excluded through an explicit mask rather than being interpreted as ordinary black image content.

## Balkan-1 validation summary

The zero-shot V4 benchmark showed strong transfer to Balkan-1, including thick cloud, thin cloud and cloud shadow detection. Representative labelled-scene results include:

| Scene | F1 | Recall | Specificity |
|---|---:|---:|---:|
| 3425 | 0.9761 | 0.9991 | 0.9670 |
| 3086 | 0.9824 | 0.9736 | 0.9844 |
| 3059 | 0.8968 | 0.9586 | 0.8827 |
| 3283 | 0.8651 | 0.8190 | 0.9947 |
| 3116 | 0.6932 | 0.8406 | 0.8125 |

Clear-scene tests also showed very low false-positive rates. See [`docs/BALKAN1_BENCHMARK.md`](docs/BALKAN1_BENCHMARK.md) for details and annotation caveats.

## Attribution

This repository is an integration project and does not claim authorship of OmniCloudMask. Cite and acknowledge the upstream project and paper when using the model in research or publications.

## License

The ViTA integration code is released under the MIT License. OmniCloudMask and its model artefacts remain subject to their upstream licensing and attribution terms.
