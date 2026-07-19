# -*- coding: utf-8 -*-
"""定位运行逻辑：静态定位 + 交互式坐标更新。

CLI 模式下负责:
    1. BD-09 → WGS-84 坐标转换（调用 driver.coords）
    2. 打开持久化 DVT 会话
    3. 交互式接收用户输入更新坐标
"""
import asyncio
import threading
import logging

from driver.coords import bd09_to_wgs84
from driver.location import LocationSession

logger = logging.getLogger("run")


async def run_static(rsd, lat: float, lng: float):
    """静态定位模式：固定坐标并持续保持。

    Args:
        rsd: RemoteServiceDiscovery 客户端
        lat: BD-09 纬度
        lng: BD-09 经度
    """
    wgs_lat, wgs_lng = bd09_to_wgs84(lat, lng)
    logger.info("BD-09(%.6f,%.6f) -> WGS-84(%.6f,%.6f)", lat, lng, wgs_lat, wgs_lng)

    session = LocationSession(rsd)
    await session.open()
    await session.set(wgs_lat, wgs_lng)

    print(f"Location set (BD-09): ({lat}, {lng})")
    print("-" * 45)
    print("Enter new coords (lat,lng BD-09) to update,")
    print("or type 'q' to quit")
    print("-" * 45)

    current_lat, current_lng = wgs_lat, wgs_lng
    lock = threading.Lock()

    try:
        while True:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(None, input)
            except (EOFError, KeyboardInterrupt):
                break

            user_input = user_input.strip()
            if user_input.lower() == "q":
                break
            if not user_input:
                continue

            try:
                parts = user_input.split(",")
                if len(parts) != 2:
                    print("Format: lat,lng")
                    continue
                new_lat = float(parts[0].strip())
                new_lng = float(parts[1].strip())
                wgs_lat, wgs_lng = bd09_to_wgs84(new_lat, new_lng)
                with lock:
                    current_lat, current_lng = wgs_lat, wgs_lng
                    await session.set(current_lat, current_lng)
                print(f"Updated (BD-09): ({new_lat}, {new_lng})")
            except ValueError:
                print("Invalid numbers")
    finally:
        await session.clear()
        await session.close()