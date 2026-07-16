# -*- coding: utf-8 -*-
"""共享日志配置 — CLI 和 GUI 共用。

提供统一的文件日志输出和第三方库静默配置，
避免 main.py 和 main_gui.py 中的重复代码。
"""
import logging
import os
from datetime import datetime


def setup_file_logging(log_dir: str, prefix: str = "ios_loc") -> str:
    """配置文件日志输出。

    Args:
        log_dir: 日志目录路径
        prefix: 日志文件名前缀

    Returns:
        str: 日志文件完整路径
    """
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"{prefix}_{timestamp}.log")

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s"
    ))
    root.addHandler(fh)

    return log_file


def quiet_third_party():
    """静默第三方库的 DEBUG 日志噪音。"""
    for name in [
        "pymobiledevice3", "asyncio", "zeroconf", "qh3", "urllib3",
        "parso", "humanfriendly", "blib2to3", "PIL", "matplotlib",
        "PyQt6", "qt", "QWebEngine",
    ]:
        logging.getLogger(name).setLevel(logging.WARNING)