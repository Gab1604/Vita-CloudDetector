# Balkan-1 zero-shot benchmark

## Frozen setup

- Input: original Balkan-1 `L1ORT` GeoTIFF products
- Spectral input: Red, Green, NIR
- L1ORT mapping: `R=3`, `G=2`, `NIR=4`, preview `B=1`
- Target resolution: 10 m UTM
- OmniCloudMask package: 1.7.1
- Model: V4
- Upstream reference commit: `fbc6d3f5665eb3425fb2474cb3e6f574e2e71a1b`
- Precision: FP32
- Requested patch size: 1000
- Patch overlap: 300
- Fine-tuning: none

## Labelled scenes

| Scene | Precision | Recall | Specificity | F1 | IoU | Balanced accuracy | Unusable fraction |
|---|---:|---:|---:|---:|---:|---:|---:|
| 3059 | 0.8425 | 0.9586 | 0.8827 | 0.8968 | 0.8129 | 0.9206 | 0.3014 |
| 3086 | 0.9913 | 0.9736 | 0.9844 | 0.9824 | 0.9653 | 0.9790 | 0.3719 |
| 3116 | 0.5898 | 0.8406 | 0.8125 | 0.6932 | 0.5304 | 0.8265 | 0.3415 |
| 3283 | 0.9167 | 0.8190 | 0.9947 | 0.8651 | 0.7622 | 0.9068 | 0.0279 |
| 3425 | 0.9542 | 0.9991 | 0.9670 | 0.9761 | 0.9534 | 0.9831 | 0.3350 |

## Clear-scene behaviour

| Scene | Visual content | Clear fraction | Unusable fraction | Notes |
|---|---|---:|---:|---|
| 3033 | Clear arid terrain | 1.000000 | 0.000000 | No label; visually verified |
| 3215 | Clear urban scene | 1.000000 | 0.000000 | Specificity 1.0000 |
| 3370 | Clear agricultural/urban scene | 0.999991 | 0.000009 | No label; 19 predicted cloud pixels |
| 3408 | Clear desert/agriculture | 0.997709 | 0.002291 | Specificity 0.9965 |
| 3458 | Clear city/airport/coast | 0.994445 | 0.005555 | Very low false-positive area |

## Annotation caveats

### Scene 3036

The bright regions appear consistent with snow or ice following terrain morphology. OmniCloudMask classified the scene as clear. Previous manual cloud annotations should be reviewed before using this scene in quantitative evaluation.

### Scene 3116

The model identified a large, spatially coherent cloud-shadow region that was visually confirmed but only partially represented in the sparse manual labels. Precision calculated from the sparse label therefore understates the visual quality of the result.

### Clear scenes

When a scene has no positive cloud pixels, recall, F1 and IoU are undefined and should be reported as `N/A`, not interpreted as zero performance. Specificity and false-positive rate are the relevant metrics.

## Interpretation

The benchmark supports the use of OmniCloudMask V4 as the main ViTA cloud-detection baseline. It transferred zero-shot to Balkan-1 and distinguished thick cloud, thin cloud and cloud shadow while maintaining low false-positive rates across urban, coastal, mountainous, desert and agricultural scenes.

The current 40% unusable-scene threshold remains provisional. Future integration should also consider the amount and spatial distribution of clear crop pixels after crop segmentation.
