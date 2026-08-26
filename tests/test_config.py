import json

import pytest

from rgb_sound.config import ConfigStore, DEFAULT_CONFIG, validate_config


def test_store_round_trip(tmp_path):
    path = tmp_path / "config.json"
    store = ConfigStore(path)
    config = store.get()
    config["channels"][0]["name"] = "桌面"
    store.replace(config)
    assert json.loads(path.read_text(encoding="utf-8"))["channels"][0]["name"] == "桌面"


def test_requires_four_channels():
    config = dict(DEFAULT_CONFIG)
    config["channels"] = config["channels"][:3]
    with pytest.raises(ValueError, match="4 个旋钮"):
        validate_config(config)


def test_rejects_invalid_calibration():
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    config["serial"]["rawMin"] = 100
    config["serial"]["rawMax"] = 100
    with pytest.raises(ValueError, match="rawMax"):
        validate_config(config)


def test_legacy_direction_setting_is_migrated_to_protocol_default():
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    config.pop("schemaVersion")
    config["serial"]["invert"] = True
    migrated = validate_config(config)
    assert migrated["schemaVersion"] == 6
    assert migrated["serial"]["invert"] is False


def test_older_config_migrates_to_high_sensitivity():
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    config["schemaVersion"] = 3
    config["behavior"]["changeThreshold"] = 3
    config["behavior"]["updateIntervalMs"] = 25
    migrated = validate_config(config)
    assert migrated["schemaVersion"] == 6
    assert migrated["behavior"]["changeThreshold"] == 0.25
    assert migrated["behavior"]["updateIntervalMs"] == 10


def test_lighting_configuration_is_validated():
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    config["lighting"].update({"mode": "sync", "color": "#12ABef", "brightness": 150, "speed": 0})
    checked = validate_config(config)
    assert checked["lighting"] == {
        "mode": "sync", "color": "#12abef", "brightness": 100,
        "speed": 1, "showVolumeProgress": True,
    }
