from __future__ import annotations

import ctypes
import logging
import os
import threading
from collections.abc import Callable
from pathlib import Path


def log_path() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA", os.environ.get("APPDATA", Path.home()))) / "RGB-SOUND"
    root.mkdir(parents=True, exist_ok=True)
    return root / "rgb-sound.log"


def configure_logging() -> Path:
    path = log_path()
    logging.basicConfig(
        filename=path,
        level=logging.INFO,
        encoding="utf-8",
        format="%(asctime)s %(levelname)s %(threadName)s %(message)s",
    )

    def log_thread_error(args: threading.ExceptHookArgs) -> None:
        logging.error("Unhandled thread exception", exc_info=(args.exc_type, args.exc_value, args.exc_traceback))

    threading.excepthook = log_thread_error
    return path


def show_error(message: str) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, message, "RGB-SOUND 启动失败", 0x10)
    except (AttributeError, OSError):
        pass


def run_safely(entrypoint: Callable[[], None]) -> None:
    path = configure_logging()
    try:
        logging.info("RGB-SOUND starting")
        entrypoint()
    except KeyboardInterrupt:
        return
    except Exception as error:
        logging.exception("RGB-SOUND stopped unexpectedly")
        show_error(f"RGB-SOUND 无法启动：\n\n{error}\n\n详细日志：{path}")
