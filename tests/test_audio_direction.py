from rgb_sound.audio import AudioController, normalize_raw_value


def test_counterclockwise_adc_direction_is_direct():
    assert normalize_raw_value(0, 0, 1023) == 0.0
    assert normalize_raw_value(1023, 0, 1023) == 1.0
    assert 0.49 < normalize_raw_value(512, 0, 1023) < 0.51


def test_optional_hardware_reversal():
    assert normalize_raw_value(0, 0, 1023, invert=True) == 1.0
    assert normalize_raw_value(1023, 0, 1023, invert=True) == 0.0


class FakeEndpointVolume:
    def __init__(self, muted: bool):
        self.muted = muted

    def GetMute(self):
        return self.muted

    def SetMute(self, muted, _context):
        self.muted = bool(muted)


def test_master_mute_button_toggles_both_directions(monkeypatch):
    monkeypatch.setattr("rgb_sound.audio.comtypes.CoInitialize", lambda: None)
    monkeypatch.setattr("rgb_sound.audio.comtypes.CoUninitialize", lambda: None)
    controller = AudioController()
    endpoint = FakeEndpointVolume(False)
    controller._speaker_volume_control = endpoint

    assert controller.toggle_master_mute() is True
    assert endpoint.muted is True
    assert controller.toggle_master_mute() is False
    assert endpoint.muted is False
