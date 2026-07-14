# -*- coding: utf-8 -*-
"""
main_gui.py - iOS 定位模拟器 GUI 入口。

启动方式:
    python main_gui.py        # GUI 模式（推荐）
    python main.py            # CLI 命令行模式

依赖:
    - PyQt6 + PyQt6-WebEngine    # GUI 框架 + 地图渲染
    - pymobiledevice3 >= 9.0     # iOS 设备通信库
    - Leaflet.js (CDN)           # 开源地图（WGS-84 坐标系）
"""

import sys
import logging
import os
from datetime import datetime

from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow


class _StreamToLogger:
    """将 stdout/stderr 重定向到 Python logging 模块。

    用于捕获 print() 和未处理的异常输出，
    使其同时显示在 GUI 日志面板和日志文件中。
    """
    def __init__(self, logger, level):
        self._logger = logger
        self._level = level
        self._buffer = ""

    def write(self, text: str):
        if text and text.strip():
            self._logger.log(self._level, text.rstrip())

    def flush(self):
        pass


def setup_logging(log_panel, log_dir: str) -> str:
    """配置日志系统：文件 + GUI 面板。

    Args:
        log_panel: LogPanel 实例，用于 GUI 内实时显示
        log_dir: 日志文件保存目录

    Returns:
        str: 日志文件的完整路径
    """
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"ios_gui_{timestamp}.log")

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s"
    )

    # 文件处理器：DEBUG 级别，UTF-8 编码
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    root.addHandler(fh)

    # GUI 面板处理器：INFO 级别，减少噪音
    gui_handler = log_panel.create_handler()
    gui_handler.setLevel(logging.INFO)
    gui_handler.setFormatter(formatter)
    root.addHandler(gui_handler)

    # 静默第三方库日志
    for name in ["pymobiledevice3", "asyncio", "zeroconf", "qh3", "urllib3",
                 "parso", "humanfriendly", "blib2to3", "PIL", "matplotlib",
                 "PyQt6", "qt", "QWebEngine"]:
        logging.getLogger(name).setLevel(logging.WARNING)

    return log_file


def main():
    """应用程序主入口。"""

    # 日志目录：优先 exe 所在目录，否则脚本所在目录
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(app_dir, "logs")

    # Windows: 设置任务栏图标 ID
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ioslocsim")

    # 创建 Qt 应用
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 创建主窗口
    window = MainWindow()

    # 设置日志系统（必须在 window 创建之后，因为需要 log_panel）
    log_file = setup_logging(window.log_panel, log_dir)

    logger = logging.getLogger("gui")
    logger.info("=" * 50)
    logger.info("iOS Location Simulator started")
    logger.info("Log file: %s", log_file)
    logger.info("=" * 50)

    # 重定向 stdout/stderr 到 logger
    sys.stdout = _StreamToLogger(logging.getLogger("stdout"), logging.INFO)
    sys.stderr = _StreamToLogger(logging.getLogger("stderr"), logging.ERROR)

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()