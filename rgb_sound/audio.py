from __future__ import annotations

import ctypes
import threading
import time
from ctypes import POINTER, cast
from dataclasses import dataclass
from typing import Any

import comtypes
import psutil
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume


@dataclass
class AudioItem:
    id: str
    label: str
    kind: str
    active: bool = True


def normalize_raw_value(raw: int, minimum: int, maximum: int, invert: bool = False) -> float:
    """Map direct ADC data to volume; counterclockwise is the positive direction."""
    value = max(0.0, min(1.0, (raw - minimum) / (maximum - minimum)))
    return 1.0 - value if invert else value


class AudioController:
    FULL_SYNC_INTERVAL = 2.0

    def __init__(self):
        self._lock = threading.RLock()
        self._last_values: list[float | None] = [None] * 4
        self._last_update = 0.0
        self._last_full_sync = 0.0
        self._last_error: str | None = None
        self._speaker_volume_control = None
        self._microphone_volume_control = None

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def toggle_master_mute(self) -> bool:
        """Toggle the default output device mute state and return the new state."""
        with self._lock:
            comtypes.CoInitialize()
            try:
                if self._speaker_volume_control is None:
                    self._speaker_volume_control = self._endpoint_volume(AudioUtilities.GetSpeakers())
                muted = bool(self._speaker_volume_control.GetMute())
                self._speaker_volume_control.SetMute(not muted, None)
                self._last_error = None
                return not muted
            except Exception as error:
                self._speaker_volume_control = None
                self._last_error = str(error)
                raise
            finally:
                comtypes.CoUninitialize()

    def list_targets(self) -> list[dict[str, Any]]:
        comtypes.CoInitialize()
        try:
            fixed = [
                AudioItem("master", "系统主音量", "special"),
                AudioItem("mic", "默认麦克风", "special"),
                AudioItem("system", "Windows 系统声音", "special"),
                AudioItem("current", "当前前台应用", "special"),
                AudioItem("unmapped", "其他未分配应用", "special"),
            ]
            processes: dict[str, AudioItem] = {}
            for session in AudioUtilities.GetAllSessions():
                if not session.Process:
                    continue
                try:
                    name = session.Process.name().lower()
                    label = session.Process.name()
                except (psutil.Error, OSError):
                    continue
                processes[name] = AudioItem(f"process:{name}", label, "application")
            return [item.__dict__ for item in fixed + sorted(processes.values(), key=lambda item: item.label.lower())]
        except Exception as error:
            self._last_error = str(error)
            return [item.__dict__ for item in fixed]
        finally:
            comtypes.CoUninitialize()

    def apply_frame(self, raw_values: tuple[int, int, int, int], config: dict) -> None:
        serial_config = config["serial"]
        behavior = config["behavior"]
        now = time.monotonic()
        if (now - self._last_update) * 1000 < behavior["updateIntervalMs"]:
            return
        minimum, maximum = serial_config["rawMin"], serial_config["rawMax"]
        normalized = []
        for raw in raw_values:
            # RGB-SOUND's fixed convention is counterclockwise = louder.
            # This board's ADC rises counterclockwise, so the value is direct.
            normalized.append(normalize_raw_value(raw, minimum, maximum, serial_config["invert"]))

        changed = []
        full_sync = now - self._last_full_sync >= self.FULL_SYNC_INTERVAL
        threshold = behavior["changeThreshold"]
        for index, value in enumerate(normalized):
            percent = value * 100.0
            previous = self._last_values[index]
            if full_sync or previous is None or abs(percent - previous) >= threshold or percent <= 0.0 or percent >= 100.0:
                changed.append((index, value, percent))
        if not changed:
            return

        with self._lock:
            comtypes.CoInitialize()
            try:
                # Master/microphone-only mappings do not need the comparatively
                # expensive enumeration of every Windows audio session.
                session_targets = {
                    target
                    for index, _, _ in changed
                    if config["channels"][index]["enabled"]
                    for target in config["channels"][index]["targets"]
                    if target not in {"master", "mic"}
                }
                sessions = AudioUtilities.GetAllSessions() if session_targets else []
                assigned = self._assigned_processes(config) if session_targets else set()
                for index, value, percent in changed:
                    channel = config["channels"][index]
                    if channel["enabled"]:
                        self._apply_targets(channel["targets"], value, sessions, assigned)
                    self._last_values[index] = percent
                self._last_update = now
                if full_sync:
                    self._last_full_sync = now
                self._last_error = None
            except Exception as error:
                self._last_error = str(error)
                self._speaker_volume_control = None
                self._microphone_volume_control = None
            finally:
                comtypes.CoUninitialize()

    @staticmethod
    def _assigned_processes(config: dict) -> set[str]:
        return {
            target.removeprefix("process:").lower()
            for channel in config["channels"]
            for target in channel["targets"]
            if target.startswith("process:")
        }

    def _apply_targets(self, targets: list[str], value: float, sessions: list, assigned: set[str]) -> None:
        foreground = self._foreground_process_name() if "current" in targets else None
        for target in targets:
            if target == "master":
                if self._speaker_volume_control is None:
                    self._speaker_volume_control = self._endpoint_volume(AudioUtilities.GetSpeakers())
                self._speaker_volume_control.SetMasterVolumeLevelScalar(value, None)
            elif target == "mic":
                if self._microphone_volume_control is None:
                    self._microphone_volume_control = self._endpoint_volume(AudioUtilities.GetMicrophone())
                self._microphone_volume_control.SetMasterVolumeLevelScalar(value, None)
            elif target.startswith("process:"):
                self._set_sessions(sessions, value, target.removeprefix("process:").lower())
            elif target == "current" and foreground:
                self._set_sessions(sessions, value, foreground)
            elif target == "system":
                self._set_system_sessions(sessions, value)
            elif target == "unmapped":
                for session in sessions:
                    name = self._session_process_name(session)
                    if name and name not in assigned:
                        session.SimpleAudioVolume.SetMasterVolume(value, None)

    @staticmethod
    def _session_process_name(session) -> str | None:
        if not session.Process:
            return None
        try:
            return session.Process.name().lower()
        except (psutil.Error, OSError):
            return None

    def _set_sessions(self, sessions: list, value: float, process_name: str) -> None:
        for session in sessions:
            if self._session_process_name(session) == process_name:
                session.SimpleAudioVolume.SetMasterVolume(value, None)

    @staticmethod
    def _set_system_sessions(sessions: list, value: float) -> None:
        for session in sessions:
            identifier = str(getattr(session, "Identifier", "")).lower()
            display = str(getattr(session, "DisplayName", "")).lower()
            if session.Process is None and ("system" in identifier or "system" in display or "系统" in display):
                session.SimpleAudioVolume.SetMasterVolume(value, None)

    @staticmethod
    def _foreground_process_name() -> str | None:
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            return psutil.Process(pid.value).name().lower()
        except (psutil.Error, OSError):
            return None

    @staticmethod
    def _endpoint_volume(device):
        endpoint = getattr(device, "EndpointVolume", None)
        if endpoint is not None:
            return endpoint
        interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))
