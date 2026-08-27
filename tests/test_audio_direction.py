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


def test_static_knobs_are_periodically_resynchronized(monkeypatch):
    monkeypatch.setattr("rgb_sound.audio.comtypes.CoInitialize", lambda: None)
    monkeypatch.setattr("rgb_sound.audio.comtypes.CoUninitialize", lambda: None)
    monkeypatch.setattr("rgb_sound.audio.AudioUtilities.GetAllSessions", lambda: [])
    controller = AudioController()
    applied = []
    monkeypatch.setattr(controller, "_apply_targets", lambda targets, value, sessions, assigned: applied.append((targets, value)))
    config = {
        "serial": {"rawMin": 0, "rawMax": 1023, "invert": False},
        "behavior": {"changeThreshold": 0.25, "updateIntervalMs": 10},
        "channels": [
            {"enabled": True, "targets": ["master"]},
            {"enabled": False, "targets": []},
            {"enabled": False, "targets": []},
            {"enabled": False, "targets": []},
        ],
    }

    controller.apply_frame((512, 0, 0, 0), config)
    first_count = len(applied)
    controller._last_update = 0
    controller.apply_frame((512, 0, 0, 0), config)
    assert len(applied) == first_count

    controller._last_update = 0
    controller._last_full_sync -= controller.FULL_SYNC_INTERVAL + 0.1
    controller.apply_frame((512, 0, 0, 0), config)
    assert len(applied) == first_count + 1
