import numpy as np
import pytest

from vita_cloud_detector import DetectorConfig, class_statistics, strict_valid_mask


def test_detector_config_rejects_invalid_threshold() -> None:
    with pytest.raises(ValueError):
        DetectorConfig(unusable_threshold=1.1)


def test_strict_valid_mask_requires_all_three_bands() -> None:
    image = np.ones((3, 2, 2), dtype=np.float32)
    image[1, 0, 1] = 0.0

    valid = strict_valid_mask(image)

    assert valid.tolist() == [[True, False], [True, True]]


def test_class_statistics() -> None:
    mask = np.array([[0, 1], [2, 3]], dtype=np.uint8)
    valid = np.ones((2, 2), dtype=bool)

    result = class_statistics(mask, valid)

    assert result["valid_pixels"] == 4
    assert result["class_counts"]["clear"] == 1
    assert result["cloud_only_fraction"] == pytest.approx(0.5)
    assert result["unusable_fraction"] == pytest.approx(0.75)
