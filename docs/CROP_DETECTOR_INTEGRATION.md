# Crop-detector integration contract

This document defines the interface between ViTA Cloud Detector and the future crop detector.

## Inputs

The cloud stage receives:

- georeferenced multispectral image;
- Blue, Green, Red and NIR channels when available;
- valid image footprint / no-data information.

OmniCloudMask uses Red, Green and NIR. Blue is retained for visual products and may be passed to later modules.

## Cloud-stage outputs

All raster outputs share the same CRS, transform, width and height.

### `cloud_classes.tif`

| Value | Meaning |
|---:|---|
| 0 | Clear |
| 1 | Thick cloud |
| 2 | Thin cloud |
| 3 | Cloud shadow |
| 255 | No-data |

### `unusable_mask.tif`

| Value | Meaning |
|---:|---|
| 0 | Usable pixel |
| 1 | Thick cloud, thin cloud or cloud shadow |
| 255 | No-data |

### `clear_mask.tif`

| Value | Meaning |
|---:|---|
| 0 | Not clear |
| 1 | Clear and valid |
| 255 | No-data |

### `valid_mask.tif`

| Value | Meaning |
|---:|---|
| 0 | Invalid / outside footprint |
| 1 | Valid input pixel |

### `summary.json`

Contains:

- per-class counts and fractions;
- cloud-only fraction;
- total unusable fraction;
- keep/discard decision;
- runtime configuration;
- sensor and source metadata;
- output paths.

## Decision logic

Current provisional rule:

```text
unusable_fraction >= 0.40  -> discard scene
unusable_fraction < 0.40   -> run crop detector
```

The 40% threshold is not final. A later policy may also consider the amount and spatial distribution of clear crop pixels.

## Crop detector requirements

The crop detector should receive:

- the aligned source bands required by its model;
- `clear_mask.tif`;
- `valid_mask.tif`.

Cloud and shadow pixels should be excluded through an explicit mask. Replacing them with black values without also supplying a validity mask risks making the crop model interpret masked pixels as ordinary image content.

The crop percentage should be calculated only over clear, valid pixels:

```text
eligible_pixels = valid_mask AND clear_mask
crop_percentage = crop_pixels / eligible_pixels
```

## Phase-1 combined outputs

The integrated onboard stage should preserve:

- categorical cloud mask;
- binary unusable mask;
- clear mask;
- valid mask;
- crop mask / crop probabilities;
- per-class cloud percentages;
- crop percentage over eligible pixels;
- keep/discard/downlink decision;
- CRS and geotransform;
- configuration and model-version metadata.

## Phase 2

Ground processing should use only pixels satisfying:

```text
valid AND clear AND crop
```

Those pixels can then be used for NDVI, GNDVI, SAVI and crop-condition scoring.
