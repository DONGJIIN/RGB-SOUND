from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from comtypes.client import CreateObject

from flask import Flask, jsonify, request, send_from_directory

from . import __version__
from .config import validate_config
from .serial_worker import available_ports


def create_app(store, serial_worker, audio) -> Flask:
    static_dir = Path(__file__).resolve().parent / "static"
    app = Flask(__name__, static_folder=None)

    @app.get("/")
    def index():
        return send_from_directory(static_dir, "index.html")

    @app.get("/static/<path:name>")
    def static_file(name: str):
        return send_from_directory(static_dir, name)

    @app.get("/api/status")
    def status():
        state = serial_worker.snapshot()
        state["audioError"] = audio.last_error
        state["version"] = __version__
        return jsonify(state)

    @app.get("/api/config")
    def get_config():
        return jsonify(store.get())

    @app.put("/api/config")
    def put_config():
        try:
            previous = store.get()
            saved = store.replace(request.get_json(force=True))
            if saved["serial"] != previous["serial"]:
                serial_worker.reconnect()
            elif saved["lighting"] != previous.get("lighting"):
                serial_worker.update_lighting(saved["lighting"])
            return jsonify(saved)
        except (ValueError, TypeError) as error:
            return jsonify({"error": str(error)}), 400

    @app.post("/api/lighting/preview")
    def preview_lighting():
        try:
            candidate = store.get()
            candidate["lighting"] = request.get_json(force=True)
            lighting = validate_config(candidate)["lighting"]
            serial_worker.update_lighting(lighting)
            return jsonify({"ok": True, "lighting": lighting})
        except (ValueError, TypeError):
            return jsonify({"error": "灯效设置无效"}), 400

    @app.get("/api/ports")
    def ports():
        return jsonify(available_ports())

    @app.get("/api/audio-targets")
    def audio_targets():
        return jsonify(audio.list_targets())

    @app.post("/api/reconnect")
    def reconnect():
        serial_worker.reconnect()
        return jsonify({"ok": True})

    @app.post("/api/startup")
    def startup():
        enabled = bool((request.get_json(silent=True) or {}).get("enabled", True))
        try:
            set_startup(enabled)
            return jsonify({"ok": True, "enabled": enabled})
        except OSError as error:
            return jsonify({"error": str(error)}), 500

    return app


def set_startup(enabled: bool) -> None:
    startup = Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/Startup"
    shortcut = startup / "RGB-SOUND.lnk"
    legacy_command = startup / "RGB-SOUND.cmd"
    legacy_command.unlink(missing_ok=True)
    if not enabled:
        shortcut.unlink(missing_ok=True)
        return
    if getattr(sys, "frozen", False):
        target = sys.executable
        arguments = "--start-hidden"
        working_directory = str(Path(sys.executable).parent)
    else:
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        target = str(pythonw)
        arguments = f'"{Path(sys.argv[0]).resolve()}" --start-hidden'
        working_directory = str(Path(sys.argv[0]).resolve().parent)

    shell = CreateObject("WScript.Shell", dynamic=True)
    link = shell.CreateShortcut(str(shortcut))
    link.TargetPath = target
    link.Arguments = arguments
    link.WorkingDirectory = working_directory
    link.WindowStyle = 7
    link.Description = "RGB-SOUND 音频控制器"
    link.Save()


def open_workspace_folder() -> None:
    folder = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path.cwd()
    subprocess.Popen(["explorer.exe", str(folder)])
