# -*- coding: utf-8 -*-
"""CLI 入口 — 命令行版 iOS 定位模拟器。"""
import asyncio
import logging
import os
import sys
import traceback

from driver import connect
from driver.location import LocationSession
from init import init
from utils import logging as utils_logging
import run
import config


async def main_async():
    """CLI 主流程：初始化 → 隧道 → DVT → 设置定位 → 等待退出。"""
    log_file = utils_logging.setup_file_logging("logs", "ios_loc")
    utils_logging.quiet_third_party()
    logger = logging.getLogger("main")
    logger.info("iOS Location Simulator (log: %s)", os.path.basename(log_file))

    lockdown = None
    tunnel_rsd = None
    tunnel_ctx = None
    session = None

    try:
        lockdown = await init()

        print("Setting up connection...")
        tunnel_rsd, tunnel_ctx = await connect.setup_tunnel(lockdown)

        session = LocationSession(tunnel_rsd)
        await session.open()
        logger.info("Ready")

        mode = getattr(config.config, "mode", "static")
        if mode == "static":
            target = getattr(config.config, "targetLocation", None)
            if target is None:
                print("=" * 55)
                print("Enter target coordinates (BD-09 coordinate system):")
                print("  Format: latitude,longitude")
                print("  Example: 30.528024,120.733557")
                print("  Tip: open https://api.map.baidu.com/lbsapi/getpoint/index.html")
                print("       click on map to get BD-09 coords, then copy-paste here")
                print("=" * 55)
                user_input = input().strip()
                parts = user_input.split(",")
                target_lat = float(parts[0].strip())
                target_lng = float(parts[1].strip())
            else:
                target_lat = float(target["lat"])
                target_lng = float(target["lng"])

            print("Press Ctrl+C to exit")
            await run.run_static(tunnel_rsd, target_lat, target_lng)

    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error("Error: %s", e)
        logger.debug(traceback.format_exc())
        print(f"Error: {e}")
    finally:
        if session:
            try:
                await session.clear()
            except Exception:
                pass
            try:
                await session.close()
            except Exception:
                pass
        if tunnel_ctx and tunnel_rsd:
            try:
                await connect.teardown_tunnel(tunnel_rsd, tunnel_ctx)
            except Exception:
                pass
        print("Bye")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()