from rgb_sound.audio import normalize_raw_value


def test_counterclockwise_adc_direction_is_direct():
    assert normalize_raw_value(0, 0, 1023) == 0.0
    assert normalize_raw_value(1023, 0, 1023) == 1.0
    assert 0.49 < normalize_raw_value(512, 0, 1023) < 0.51


def test_optional_hardware_reversal():
    assert normalize_raw_value(0, 0, 1023, invert=True) == 1.0
    assert normalize_raw_value(1023, 0, 1023, invert=True) == 0.0
