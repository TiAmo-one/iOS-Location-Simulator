# -*- coding: utf-8 -*-
"""GUI 入口 — 地图选点版 iOS 定位模拟器。"""
import sys
import logging
import os
from datetime import datetime

from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow
from utils import logging as utils_logging


class _StreamToLogger:
    """将 stdout/stderr 重定向到 Python logging。"""
    def __init__(self, logger, level):
        self._logger = logger
        self._level = level

    def write(self, text: str):
        if text and text.strip():
            self._logger.log(self._level, text.rstrip())

    def flush(self):
        pass


def setup_logging(log_panel, log_dir: str) -> str:
    """配置文件日志 + GUI 面板日志双输出。"""
    log_file = utils_logging.setup_file_logging(log_dir, "ios_gui")
    utils_logging.quiet_third_party()

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s"
    )

    gui_handler = log_panel.create_handler()
    gui_handler.setLevel(logging.INFO)
    gui_handler.setFormatter(formatter)
    logging.getLogger().addHandler(gui_handler)

    return log_file


def main():
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(app_dir, "logs")

    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ioslocsim")

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    log_file = setup_logging(window.log_panel, log_dir)

    logger = logging.getLogger("gui")
    logger.info("=" * 50)
    logger.info("iOS Location Simulator started")
    logger.info("Log file: %s", log_file)
    logger.info("=" * 50)

    sys.stdout = _StreamToLogger(logging.getLogger("stdout"), logging.INFO)
    sys.stderr = _StreamToLogger(logging.getLogger("stderr"), logging.ERROR)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()