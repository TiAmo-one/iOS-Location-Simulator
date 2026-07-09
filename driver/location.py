# -*- coding: utf-8 -*-
"""
driver/location.py - 通过 DVT over RSD 实现 iOS 定位模拟。

定位模拟层：通过 DVT(Developer Verification & Testing) 协议控制 iOS 设备 GPS。

关键设计:
    - DVT 会话必须持续打开才能保持模拟定位
    - 关闭 DVT 会话会自动恢复真实 GPS
    - LocationSession 封装了完整的生命周期管理
"""
import logging

from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation

logger = logging.getLogger("location")


class LocationSession:
    """
    持久化定位会话管理器。

    管理 DVT 连接和 LocationSimulation 的完整生命周期。
    会话打开后，定位修改持续有效；关闭会话后自动恢复真实位置。

    使用方式:
        session = LocationSession(rsd)
        await session.open()          # 打开 DVT 通道
        await session.set(lat, lng)   # 设置定位
        # ... 等待 ...
        await session.clear()         # 清除模拟定位
        await session.close()         # 关闭 DVT
    """

    def __init__(self, rsd):
        """
        Args:
            rsd: RemoteServiceDiscovery 客户端（已通过隧道连接）
        """
        # RSD 客户端引用（隧道上的远程服务发现连接）
        self._rsd = rsd
        # DVT 协议提供者（开发者验证和测试工具）
        self._dvt = None
        # 定位模拟器（通过 DVT 发送 GPS 坐标给设备）
        self._loc = None

    async def open(self):
        """
        打开 DVT 连接并初始化定位模拟器。

        这一步会与设备建立 DVT 会话通道，
        然后在此通道上创建 LocationSimulation 服务。
        """
        logger.debug("Opening DvtProvider...")
        # 创建 DVT 提供者（连接 RSD）
        self._dvt = DvtProvider(self._rsd)
        # 建立 DVT 连接
        await self._dvt.connect()
        # 创建定位模拟器实例
        self._loc = LocationSimulation(self._dvt)
        # 初始化定位模拟器（异步上下文管理器）
        await self._loc.__aenter__()
        logger.debug("DVT session open")

    async def set(self, lat: float, lng: float):
        """
        设置模拟 GPS 坐标（WGS-84 坐标系）。

        会话必须已打开（调用了 open() 之后才能调用 set()）。
        设置后设备会立即使用新坐标，直到调用 clear() 或关闭会话。

        Args:
            lat: WGS-84 纬度
            lng: WGS-84 经度
        """
        await self._loc.set(lat, lng)
        logger.info("Location set: %.6f, %.6f", lat, lng)

    async def clear(self):
        """清除模拟定位，恢复设备真实 GPS。"""
        if self._loc:
            await self._loc.clear()
            logger.info("Location cleared")

    async def close(self):
        """
        关闭 DVT 连接和定位模拟器。

        先关闭定位模拟器再关闭 DVT 连接。
        关闭后设备恢复真实 GPS。
        """
        if self._loc:
            try:
                # 退出定位模拟器异步上下文
                await self._loc.__aexit__(None, None, None)
            except Exception:
                pass
            self._loc = None
        if self._dvt:
            try:
                # 关闭 DVT 连接
                await self._dvt.close()
            except Exception:
                pass
            self._dvt = None
        logger.debug("DVT session closed")
