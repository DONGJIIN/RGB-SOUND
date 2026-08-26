from rgb_sound.serial_worker import parse_effect_event, parse_frame


def test_parse_valid_frame():
    assert parse_frame("0|255|512|1023\r\n") == (0, 255, 512, 1023)


def test_parse_invalid_frames():
    assert parse_frame("1|2|3") is None
    assert parse_frame("1|two|3|4") is None
    assert parse_frame("1|2|3|-1") is None


def test_parse_effect_events():
    assert parse_effect_event("FX|BREATHING\r\n") == "BREATHING"
    assert parse_effect_event("fx|sync") == "SYNC"
    assert parse_effect_event("FX|RAINBOW") == "RAINBOW"
    assert parse_effect_event("BTN|MASTER|ON") is None
