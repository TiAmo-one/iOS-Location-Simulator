# -*- coding: utf-8 -*-
"""
main.py - iOS 定位模拟器 CLI (iOS 17+)

命令行版本的 iOS 定位模拟器。
通过 USB 连接 iPhone，使用 pymobiledevice3 建立 RSD 隧道，
通过 DVT 协议模拟 GPS 定位。支持交互式输入坐标和 config.yaml 预设坐标。

用法:
    python main.py          # 使用 config.yaml 中的坐标
    或启动后手动输入坐标
"""
import asyncio
import logging
import logging.handlers
import os
import sys
import traceback
from datetime import datetime

from driver import connect
from driver.location import LocationSession
from init import init
import run
import config


def setup_logging():
    """
    配置双输出日志系统。

    - 文件输出 (DEBUG 级别): logs/ios_loc_YYYYMMDD_HHMMSS.log (UTF-8 编码)
    - 控制台输出 (INFO 级别): 简洁格式，仅显示消息内容
    - 第三方库日志级别设为 WARNING 以减少噪音

    Returns:
        str: 日志文件路径
    """
    # 确保日志目录存在
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    # 按时间戳命名日志文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"ios_loc_{timestamp}.log")

    # 获取根日志记录器
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # File: DEBUG level, UTF-8
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)-7s] %(name)s: %(message)s"))
    root.addHandler(fh)

    # Console: INFO level, minimal format
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(ch)

    # Quiet noisy libs
    for name in ["pymobiledevice3", "asyncio", "zeroconf", "qh3", "urllib3",
                 "parso", "humanfriendly", "blib2to3"]:
        logging.getLogger(name).setLevel(logging.WARNING)

    return log_file


async def main_async():
    """
    CLI 主异步流程。

    流程: 初始化 → 建隧道 → 开 DVT 会话 → 设置定位 → 等待用户输入
    按 Ctrl+C 可随时退出，退出时自动清除定位并断开连接。
    """
    log_file = setup_logging()
    logger = logging.getLogger("main")
    logger.info("iOS Location Simulator (log: %s)", os.path.basename(log_file))

    # 资源引用，用于 finally 块清理
    lockdown = None
    tunnel_rsd = None
    tunnel_ctx = None
    session = None

    try:
        # 第一步: 设备初始化检查（管理员权限、连接、解锁、开发者模式）
        lockdown = await init.init()

        # 第二步: 建立 RSD 隧道（用于 iOS 17+ 的 DVT 通信）
        print("Setting up connection...")
        tunnel_rsd, tunnel_ctx = await connect.setup_tunnel(lockdown)

        # 第三步: 打开持久化 DVT 定位会话
        session = LocationSession(tunnel_rsd)
        await session.open()
        logger.info("Ready")

        # 第四步: 根据配置模式运行
        mode = getattr(config.config, "mode", "static")
        if mode == "static":
            # 静态模式: 固定到一个坐标
            target = getattr(config.config, "targetLocation", None)
            if target is None:
                # 交互式输入: 手动输入 BD-09 坐标
                print("Enter coords (lat,lng, BD-09):")
                user_input = input().strip()
                parts = user_input.split(",")
                target_lat = float(parts[0].strip())
                target_lng = float(parts[1].strip())
            else:
                # 从 config.yaml 读取预设坐标
                target_lat = float(target["lat"])
                target_lng = float(target["lng"])

            # 提示用户退出方式
            print("Press Ctrl+C to exit")
            await run.run_static(tunnel_rsd, target_lat, target_lng)

    except KeyboardInterrupt:
        # 用户按 Ctrl+C，静默退出
        pass
    except Exception as e:
        logger.error("Error: %s", e)
        logger.debug(traceback.format_exc())
        print(f"Error: {e}")
    finally:
        # 资源清理: 先清定位 → 关 DVT → 关隧道
        if session:
            try:
                # 清除设备上的模拟定位
                await session.clear()
            except Exception:
                pass
            try:
                # 关闭 DVT 会话
                await session.close()
            except Exception:
                pass
        # 拆除 RSD 隧道
        if tunnel_ctx and tunnel_rsd:
            try:
                await connect.teardown_tunnel(tunnel_rsd, tunnel_ctx)
            except Exception:
                pass
        print("Bye")


def main():
    """CLI 程序入口：启动 asyncio 事件循环。"""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
