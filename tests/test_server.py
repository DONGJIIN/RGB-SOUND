import json

from rgb_sound.config import ConfigStore
from rgb_sound.server import create_app


class FakeSerialWorker:
    def __init__(self):
        self.reconnects = 0
        self.lighting_updates = []

    def snapshot(self):
        return {"connected": True, "frames": 1, "values": [0, 0, 0, 0]}

    def reconnect(self):
        self.reconnects += 1

    def update_lighting(self, lighting):
        self.lighting_updates.append(lighting)


class FakeAudio:
    last_error = None

    def list_targets(self):
        return [{"id": "master", "label": "系统主音量", "kind": "special", "active": True}]


def test_config_api_migrates_legacy_config_and_keeps_lighting(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    worker = FakeSerialWorker()
    client = create_app(store, worker, FakeAudio()).test_client()

    legacy = store.get()
    legacy["schemaVersion"] = 5
    legacy.pop("lighting")
    response = client.put("/api/config", data=json.dumps(legacy), content_type="application/json")

    assert response.status_code == 200
    saved = response.get_json()
    assert saved["schemaVersion"] == 6
    assert saved["lighting"]["mode"] == "breathing"
    assert worker.reconnects == 0


def test_lighting_preview_is_validated_and_does_not_reconnect(tmp_path):
    worker = FakeSerialWorker()
    client = create_app(ConfigStore(tmp_path / "config.json"), worker, FakeAudio()).test_client()
    response = client.post("/api/lighting/preview", json={
        "mode": "solid", "color": "#12ABef", "brightness": 150,
        "speed": 0, "showVolumeProgress": False,
    })

    assert response.status_code == 200
    assert worker.reconnects == 0
    assert worker.lighting_updates[-1] == {
        "mode": "solid", "color": "#12abef", "brightness": 100,
        "speed": 1, "showVolumeProgress": False,
    }
    invalid = client.post("/api/lighting/preview", data="null", content_type="application/json")
    assert invalid.status_code == 400
    assert invalid.get_json()["error"] == "灯效设置无效"


def test_saved_lighting_updates_in_place_but_serial_change_reconnects(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    worker = FakeSerialWorker()
    client = create_app(store, worker, FakeAudio()).test_client()
    config = store.get()
    config["lighting"]["mode"] = "solid"
    assert client.put("/api/config", json=config).status_code == 200
    assert worker.lighting_updates[-1]["mode"] == "solid"
    assert worker.reconnects == 0

    config = store.get()
    config["serial"]["port"] = "COM99"
    assert client.put("/api/config", json=config).status_code == 200
    assert worker.reconnects == 1


def test_frontend_assets_include_legacy_fallback_and_cache_buster(tmp_path):
    client = create_app(ConfigStore(tmp_path / "config.json"), FakeSerialWorker(), FakeAudio()).test_client()
    html = client.get("/").get_data(as_text=True)
    javascript = client.get("/static/app.js").get_data(as_text=True)

    assert "app.js?v=1.5.0" in html
    assert "DEFAULT_LIGHTING" in javascript
    assert "config.lighting||{}" in javascript
