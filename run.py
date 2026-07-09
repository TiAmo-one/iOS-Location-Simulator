# -*- coding: utf-8 -*-
"""
run.py - 定位模拟逻辑。

核心功能:
    1. BD-09 (百度坐标系) → WGS-84 (iOS 使用) 坐标转换
    2. 静态定位保持：持续维持 DVT 会话，支持手动更改坐标

坐标系说明:
    - BD-09: 百度地图使用的坐标系，在中国有偏移
    - GCJ-02: 国测局坐标系（火星坐标系），中国法定坐标系
    - WGS-84: 全球卫星定位系统使用的坐标系，iOS/Google 使用
    百度坐标 → 火星坐标 → WGS-84: 两步转换
"""
import math
import asyncio
import threading
import logging

from driver.location import LocationSession

logger = logging.getLogger("run")


def bd09Towgs84(position):
    """
    百度坐标系 (BD-09) → WGS-84 坐标转换。

    转换流程: BD-09 → GCJ-02 → WGS-84 (两步转换)
    第一步: BD-09 去偏移 → GCJ-02
    第二步: GCJ-02 去偏移 → WGS-84

    Args:
        position: {"lat": 纬度, "lng": 经度} (BD-09)

    Returns:
        {"lat": WGS-84 纬度, "lng": WGS-84 经度}

    参考: 中国坐标系转换标准算法
    """
    # 常量定义
    # x_pi: π × 3000.0/180.0，用于 BD-09 → GCJ-02 步骤
    x_pi = 3.14159265358979324 * 3000.0 / 180.0
    pi = 3.141592653589793238462643383
    # a: 地球长半轴 (WGS-84 椭球体参数)
    a = 6378245.0
    # ee: 第一偏心率平方 (WGS-84 椭球体参数)
    ee = 0.00669342162296594323

    def transform_lat(x, y):
        """GCJ-02 纬度偏移量计算（非线性变换）。"""
        ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
        ret += (20.0 * math.sin(6.0 * x * pi) + 20.0 * math.sin(2.0 * x * pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(y * pi) + 40.0 * math.sin(y / 3.0 * pi)) * 2.0 / 3.0
        ret += (160.0 * math.sin(y / 12.0 * pi) + 320 * math.sin(y * pi / 30.0)) * 2.0 / 3.0
        return ret

    def transform_lon(x, y):
        """GCJ-02 经度偏移量计算（非线性变换）。"""
        ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
        ret += (20.0 * math.sin(6.0 * x * pi) + 20.0 * math.sin(2.0 * x * pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(x * pi) + 40.0 * math.sin(x / 3.0 * pi)) * 2.0 / 3.0
        ret += (150.0 * math.sin(x / 12.0 * pi) + 300.0 * math.sin(x / 30.0 * pi)) * 2.0 / 3.0
        return ret

    # ---- 第一步: BD-09 → GCJ-02 ----
    # BD-09 坐标减去固定偏移
    x = position["lng"] - 0.0065
    y = position["lat"] - 0.006
    # 计算极坐标转换参数
    z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * x_pi)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * x_pi)

    # 得到 GCJ-02 经纬度
    gcj_lng = z * math.cos(theta)
    gcj_lat = z * math.sin(theta)

    # ---- 第二步: GCJ-02 → WGS-84 ----
    # 计算偏移量（GCJ-02 的扭曲量）
    d_lat = transform_lat(gcj_lng - 105.0, gcj_lat - 35.0)
    d_lng = transform_lon(gcj_lng - 105.0, gcj_lat - 35.0)

    # 将弧度偏移转为度数偏移
    rad_lat = gcj_lat / 180.0 * pi
    magic = math.sin(rad_lat)
    magic = 1 - ee * magic * magic
    sqrt_magic = math.sqrt(magic)

    # 经度偏移（考虑纬度对经度距离的影响）
    d_lng = (d_lng * 180.0) / (a / sqrt_magic * math.cos(rad_lat) * pi)
    # 纬度偏移
    d_lat = (d_lat * 180.0) / (a * (1 - ee) / (magic * sqrt_magic) * pi)

    # GCJ-02 减去偏移量得到 WGS-84（公式简化: gcj - offset）
    return {"lat": gcj_lat * 2 - gcj_lat - d_lat, "lng": gcj_lng * 2 - gcj_lng - d_lng}


async def run_static(rsd, lat, lng):
    """
    静态定位模式：固定坐标并持续保持。

    保持 DVT 会话持续开放以确保模拟定位不会因为会话关闭而消失。
    用户可以在运行过程中输入新坐标来动态更新位置。

    Args:
        rsd: RemoteServiceDiscovery 客户端
        lat: BD-09 纬度
        lng: BD-09 经度
    """
    # BD-09 → WGS-84 转换
    wgs = bd09Towgs84({"lat": lat, "lng": lng})
    logger.info("BD-09(%s,%s) -> WGS-84(%.6f,%.6f)", lat, lng, wgs["lat"], wgs["lng"])

    # 打开持久化 DVT 会话
    session = LocationSession(rsd)
    await session.open()
    # 设置初始坐标
    await session.set(wgs["lat"], wgs["lng"])

    print(f"Location set (BD-09): ({lat}, {lng})")
    print("Enter new coords (lat,lng) to change, q to quit")

    # 记录当前 WGS-84 坐标
    current_lat = wgs["lat"]
    current_lng = wgs["lng"]
    # 线程锁保护坐标更新
    lock = threading.Lock()

    try:
        while True:
            try:
                # 在独立线程中读取用户输入（不阻塞 asyncio 事件循环）
                user_input = await asyncio.get_event_loop().run_in_executor(None, input)
            except (EOFError, KeyboardInterrupt):
                break

            user_input = user_input.strip()
            # q 或空输入退出
            if user_input.lower() == "q":
                break
            if not user_input:
                continue

            try:
                # 解析新坐标 (格式: lat,lng)
                parts = user_input.split(",")
                if len(parts) != 2:
                    print("Format: lat,lng")
                    continue
                new_lat = float(parts[0].strip())
                new_lng = float(parts[1].strip())
                # BD-09 → WGS-84 转换
                wgs_new = bd09Towgs84({"lat": new_lat, "lng": new_lng})
                with lock:
                    current_lat = wgs_new["lat"]
                    current_lng = wgs_new["lng"]
                    # 更新设备上的模拟定位
                    await session.set(current_lat, current_lng)
                print(f"Updated (BD-09): ({new_lat}, {new_lng})")
            except ValueError:
                print("Invalid numbers")

    finally:
        # 清理: 先清除定位，再关闭会话
        await session.clear()
        await session.close()
