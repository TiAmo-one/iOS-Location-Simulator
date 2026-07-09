# -*- coding: utf-8 -*-
"""
main_gui.py - iOS 定位模拟器 GUI 入口
=====================================
基于 PyQt6 的可视化界面，通过 Leaflet 地图选点，
利用 pymobiledevice3 与 iOS 17+ 设备通信实现定位模拟。

启动方式:
    conda activate pos
    python main_gui.py        # GUI 模式（推荐）
    python main.py            # CLI 命令行模式

依赖:
    - PyQt6 + PyQt6-WebEngine    # GUI 框架 + 地图渲染
    - pymobiledevice3 >= 9.0     # iOS 设备通信库
    - Leaflet.js (CDN)           # 开源地图（WGS-84 坐标系）

原理:
    1. 通过 USB 连接 iPhone/iPad（需要开发者模式）
    2. 通过 RSD(RemoteServiceDiscovery) + remotepairing 建立 TCP 隧道
    3. 在隧道上创建 DVT(Developer Verification & Testing) 会话
    4. 通过 DVT 的 LocationSimulation 接口修改设备 GPS 坐标
    5. 保持 DVT 会话持续开放以维持模拟定位

注意事项:
    - 必须以管理员身份运行（创建虚拟网卡需要管理员权限）
    - 设备需要 iOS 17.0+，已开启开发者模式
    - 只能连接一台设备
    - 退出程序前会尝试清除模拟定位，恢复真实 GPS
"""

import sys
import logging
import os
from datetime import datetime

# ---------- PyQt6 必须在导入其他 GUI 模块之前导入 ----------
from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow


def setup_logging() -> str:
    """
    配置日志系统：仅文件输出（GUI 模式下控制台不输出日志）。
    
    日志文件保存在 ./logs/ 目录，文件名包含时间戳。
    第三方库（pymobiledevice3、asyncio 等）的日志级别设为 WARNING 以减少噪音。
    
    Returns:
        str: 日志文件的完整路径
    """
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"ios_gui_{timestamp}.log")

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # 文件处理器：UTF-8 编码，DEBUG 级别，带时间戳和模块名
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s"
    ))
    root.addHandler(fh)

    # 静默第三方库的日志噪音
    for name in ["pymobiledevice3", "asyncio", "zeroconf", "qh3", "urllib3",
                 "parso", "humanfriendly", "blib2to3", "PIL", "matplotlib",
                 "PyQt6", "qt"]:
        logging.getLogger(name).setLevel(logging.WARNING)

    return log_file


def main():
    """应用程序主入口。"""
    log_file = setup_logging()
    logger = logging.getLogger("gui")
    logger.info("GUI 启动 (日志: %s)", os.path.basename(log_file))

    # Windows: 设置任务栏图标 ID（避免显示 Python 默认图标）
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ioslocsim")

    # 创建 Qt 应用
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # 跨平台统一的现代化风格

    # 创建并显示主窗口
    window = MainWindow()
    window.show()

    # 进入 Qt 事件循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
