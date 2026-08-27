import json

from rgb_sound import main


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_probe_recognizes_current_and_legacy_rgb_sound(monkeypatch):
    monkeypatch.setattr(main, "urlopen", lambda *_args, **_kwargs: FakeResponse({
        "product": "RGB-SOUND", "version": "1.6.1",
    }))
    assert main.probe_rgb_sound("127.0.0.1", 17321)["version"] == "1.6.1"

    monkeypatch.setattr(main, "urlopen", lambda *_args, **_kwargs: FakeResponse({
        "version": "1.2.0", "frames": 10, "values": [0, 0, 0, 0],
    }))
    assert main.probe_rgb_sound("127.0.0.1", 17321)["version"] == "1.2.0"


def test_probe_rejects_unrelated_listener(monkeypatch):
    monkeypatch.setattr(main, "urlopen", lambda *_args, **_kwargs: FakeResponse({"status": "ok"}))
    assert main.probe_rgb_sound("127.0.0.1", 17321) is None
