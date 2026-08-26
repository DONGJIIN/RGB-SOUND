from __future__ import annotations

import argparse
import threading
from pathlib import Path
import os
import socket

from waitress import create_server

from .audio import AudioController
from .config import ConfigStore
from .serial_worker import SerialWorker
from .server import create_app


def service_is_running(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.25):
            return True
    except OSError:
        return False


def open_desktop_window(url: str, *, start_hidden: bool = False, with_tray: bool = True) -> None:
    import webview

    storage = Path(os.environ.get("APPDATA", Path.home())) / "RGB-SOUND" / "webview"
    window = webview.create_window(
        "RGB-SOUND 音频控制台",
        url,
        width=1280,
        height=860,
        min_size=(900, 650),
        background_color="#090b10",
        text_select=True,
        hidden=start_hidden,
        confirm_close=with_tray,
    )
    tray = None
    lifecycle = {"quitting": False}

    if with_tray:
        import pystray
        from PIL import Image, ImageDraw

        icon_image = Image.new("RGBA", (64, 64), "#111820")
        draw = ImageDraw.Draw(icon_image)
        draw.rounded_rectangle((4, 4, 60, 60), radius=15, fill="#72f1b8")
        draw.text((24, 20), "R", fill="#07140f")

        def show_window(_icon=None, _item=None):
            window.show()
            window.restore()

        def quit_app(icon, _item=None):
            lifecycle["quitting"] = True
            icon.stop()
            window.destroy()

        def minimize_to_tray():
            if lifecycle["quitting"]:
                return True
            threading.Thread(target=window.hide, daemon=True).start()
            return False

        window.events.closing += minimize_to_tray
        tray = pystray.Icon(
            "RGB-SOUND",
            icon_image,
            "RGB-SOUND 音频控制台",
            pystray.Menu(
                pystray.MenuItem("打开控制台", show_window, default=True),
                pystray.MenuItem("完全退出", quit_app),
            ),
        )
        tray.run_detached()

    try:
        webview.start(private_mode=False, storage_path=str(storage))
    finally:
        if tray:
            tray.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="RGB-SOUND four-knob audio controller")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=17321, type=int)
    parser.add_argument("--no-browser", action="store_true", help="只启动后台服务，不显示桌面窗口")
    parser.add_argument("--start-hidden", action="store_true", help="启动到系统托盘")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"
    if service_is_running(args.host, args.port):
        if not args.no_browser:
            open_desktop_window(url, start_hidden=False, with_tray=False)
        return

    store = ConfigStore()
    audio = AudioController()
    worker = SerialWorker(store.get, lambda frame: audio.apply_frame(frame, store.get()))
    app = create_app(store, worker, audio)
    worker.start()

    server = create_server(app, host=args.host, port=args.port, threads=6)
    try:
        if args.no_browser:
            server.run()
        else:
            server_thread = threading.Thread(target=server.run, name="local-web-server", daemon=True)
            server_thread.start()
            open_desktop_window(url, start_hidden=args.start_hidden, with_tray=True)
    finally:
        server.close()
        worker.stop()
