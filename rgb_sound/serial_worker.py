from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, asdict

import serial
from serial.tools import list_ports


@dataclass
class DeviceState:
    connected: bool = False
    port: str | None = None
    message: str = "正在查找设备"
    values: tuple[int, int, int, int] = (0, 0, 0, 0)
    frames: int = 0
    last_frame_at: float | None = None
    effect_message: str | None = None
    effect_event_at: float | None = None

    def as_dict(self) -> dict:
        value = asdict(self)
        value["values"] = list(self.values)
        return value


def available_ports() -> list[dict]:
    return [
        {
            "device": item.device,
            "description": item.description or item.device,
            "vid": item.vid,
            "pid": item.pid,
            "serialNumber": item.serial_number,
        }
        for item in list_ports.comports()
    ]


def parse_frame(line: str) -> tuple[int, int, int, int] | None:
    parts = [part.strip() for part in line.strip().split("|")]
    if len(parts) != 4:
        return None
    try:
        values = tuple(int(part) for part in parts)
    except ValueError:
        return None
    if any(value < 0 or value > 65535 for value in values):
        return None
    return values  # type: ignore[return-value]


def parse_effect_event(line: str) -> str | None:
    parts = [part.strip().upper() for part in line.strip().split("|")]
    if len(parts) != 2 or parts[0] != "FX":
        return None
    if parts[1] not in {"BREATHING", "CHASE", "RAINBOW"}:
        return None
    return parts[1]


def choose_port(preference: str) -> str | None:
    ports = list(list_ports.comports())
    if preference and preference.lower() != "auto":
        return preference if any(port.device.lower() == preference.lower() for port in ports) else None
    if not ports:
        return None
    known_vids = {0x1209, 0x1A86, 0x4348}
    preferred = [port for port in ports if port.vid in known_vids or "CH55" in (port.description or "").upper()]
    return (preferred or ports)[0].device


class SerialWorker:
    def __init__(
        self,
        get_config: Callable[[], dict],
        on_values: Callable[[tuple[int, int, int, int]], None],
    ):
        self.get_config = get_config
        self.on_values = on_values
        self.state = DeviceState()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._reconnect = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="serial-reader", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._reconnect.set()
        if self._thread:
            self._thread.join(timeout=2)

    def reconnect(self) -> None:
        self._reconnect.set()

    def snapshot(self) -> dict:
        with self._lock:
            return self.state.as_dict()

    def _set_state(self, **changes) -> None:
        with self._lock:
            for key, value in changes.items():
                setattr(self.state, key, value)

    def _run(self) -> None:
        while not self._stop.is_set():
            config = self.get_config()["serial"]
            port = choose_port(config["port"])
            if not port:
                self._set_state(connected=False, port=None, message="未找到串口设备")
                self._stop.wait(2)
                continue
            self._reconnect.clear()
            try:
                with serial.Serial(port, config["baudRate"], timeout=1) as connection:
                    self._set_state(connected=True, port=port, message="串口已连接，等待旋钮数据")
                    while not self._stop.is_set() and not self._reconnect.is_set():
                        raw = connection.readline()
                        if not raw:
                            continue
                        line = raw.decode("ascii", errors="ignore")
                        effect = parse_effect_event(line)
                        if effect is not None:
                            message = {
                                "BREATHING": "灯效：呼吸灯",
                                "CHASE": "灯效：跑马灯",
                                "RAINBOW": "灯效：幻彩灯",
                            }[effect]
                            now = time.time()
                            self._set_state(effect_message=message, effect_event_at=now)
                            continue
                        frame = parse_frame(line)
                        if frame is None:
                            continue
                        now = time.time()
                        with self._lock:
                            self.state.values = frame
                            self.state.frames += 1
                            self.state.last_frame_at = now
                            self.state.message = "设备工作正常"
                        self.on_values(frame)
            except (serial.SerialException, OSError) as error:
                self._set_state(connected=False, port=port, message=f"连接失败：{error}")
                self._stop.wait(2)
            finally:
                self._set_state(connected=False)
