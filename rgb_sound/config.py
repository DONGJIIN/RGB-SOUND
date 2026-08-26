from __future__ import annotations

import json
import os
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "schemaVersion": 5,
    "serial": {
        "port": "auto",
        "baudRate": 9600,
        "rawMin": 0,
        "rawMax": 1023,
        # Fixed project convention: counterclockwise = louder.
        "invert": False,
    },
    "channels": [
        {"id": 0, "name": "主音量", "color": "#72f1b8", "enabled": True, "targets": ["master"]},
        {"id": 1, "name": "浏览器", "color": "#53a7ff", "enabled": True, "targets": ["process:chrome.exe", "process:msedge.exe"]},
        {"id": 2, "name": "音乐", "color": "#a987ff", "enabled": True, "targets": ["process:spotify.exe"]},
        {"id": 3, "name": "其他应用", "color": "#ff9f6e", "enabled": True, "targets": ["unmapped"]},
    ],
    "behavior": {"changeThreshold": 0.25, "updateIntervalMs": 10, "openBrowser": True},
}


def config_path() -> Path:
    override = os.environ.get("RGB_SOUND_CONFIG")
    if override:
        return Path(override)
    root = Path(os.environ.get("APPDATA", Path.home())) / "RGB-SOUND"
    return root / "config.json"


class ConfigStore:
    def __init__(self, path: Path | None = None):
        self.path = path or config_path()
        self._lock = threading.RLock()
        self._data = deepcopy(DEFAULT_CONFIG)
        self.load()

    def load(self) -> dict[str, Any]:
        with self._lock:
            if self.path.exists():
                try:
                    loaded = json.loads(self.path.read_text(encoding="utf-8"))
                    self._data = validate_config(loaded)
                except (OSError, ValueError, TypeError):
                    self._data = deepcopy(DEFAULT_CONFIG)
            self.save()
            return self.get()

    def get(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._data)

    def replace(self, value: dict[str, Any]) -> dict[str, Any]:
        checked = validate_config(value)
        with self._lock:
            self._data = checked
            self.save()
            return self.get()

    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            payload = json.dumps(self._data, ensure_ascii=False, indent=2)
            temporary.write_text(payload, encoding="utf-8")
            try:
                temporary.replace(self.path)
            except OSError:
                # Roaming profiles can expose a redirected directory that looks local
                # while its children resolve to different volumes.
                self.path.write_text(payload, encoding="utf-8")
                temporary.unlink(missing_ok=True)


def validate_config(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("配置必须是对象")
    result = deepcopy(DEFAULT_CONFIG)
    source_version = int(value.get("schemaVersion", 1))
    result["schemaVersion"] = 5
    serial = value.get("serial", {})
    result["serial"] = {
        "port": str(serial.get("port", "auto")),
        "baudRate": max(300, min(2_000_000, int(serial.get("baudRate", 9600)))),
        "rawMin": int(serial.get("rawMin", 0)),
        "rawMax": int(serial.get("rawMax", 1023)),
        # Schema 5 permanently adopts the user's requested direct ADC direction.
        # Reset old direction settings once so stale configs cannot reverse it.
        "invert": False if source_version < 5 else bool(serial.get("invert", False)),
    }
    if result["serial"]["rawMax"] <= result["serial"]["rawMin"]:
        raise ValueError("rawMax 必须大于 rawMin")

    channels = value.get("channels")
    if not isinstance(channels, list) or len(channels) != 4:
        raise ValueError("必须配置 4 个旋钮")
    checked_channels = []
    for index, channel in enumerate(channels):
        if not isinstance(channel, dict):
            raise ValueError(f"旋钮 {index + 1} 配置无效")
        targets = channel.get("targets", [])
        if not isinstance(targets, list) or any(not isinstance(item, str) for item in targets):
            raise ValueError(f"旋钮 {index + 1} 的目标无效")
        checked_channels.append({
            "id": index,
            "name": str(channel.get("name", f"旋钮 {index + 1}"))[:32],
            "color": str(channel.get("color", DEFAULT_CONFIG["channels"][index]["color"])),
            "enabled": bool(channel.get("enabled", True)),
            "targets": list(dict.fromkeys(targets)),
        })
    result["channels"] = checked_channels

    behavior = value.get("behavior", {})
    result["behavior"] = {
        "changeThreshold": 0.25 if source_version < 4 else max(0.1, min(10.0, float(behavior.get("changeThreshold", 0.25)))),
        "updateIntervalMs": 10 if source_version < 4 else max(10, min(1000, int(behavior.get("updateIntervalMs", 10)))),
        "openBrowser": bool(behavior.get("openBrowser", True)),
    }
    return result
