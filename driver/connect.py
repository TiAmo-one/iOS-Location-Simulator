# -*- coding: utf-8 -*-
"""
driver/connect.py - 设备连接、RSD 服务发现、隧道建立。

连接层：负责与 iOS 设备的 USB 通信、RSD 服务发现、TCP 隧道建立。

核心流程:
    1. USB lockdown 连接 (create_using_usbmux)
    2. 检查设备锁定状态、开发者模式
    3. 通过 Bonjour/mDNS 发现 remotepairing 隧道服务
    4. 建立 TCP 隧道 (iOS 17+ 不再支持 QUIC)
    5. 在隧道上创建 RSD 连接

两种模式:
    - blocking=True (CLI): 设备未连接/锁定时等待用户操作
    - blocking=False (GUI): 立即抛出异常，由调用方处理
"""
import logging
import asyncio
import traceback

from pymobiledevice3.lockdown import create_using_usbmux, LockdownClient
from pymobiledevice3.exceptions import NoDeviceConnectedError
from pymobiledevice3.services.amfi import AmfiService
from pymobiledevice3.remote.common import TunnelProtocol
from pymobiledevice3.remote.remote_service_discovery import RemoteServiceDiscoveryService
from pymobiledevice3.remote.tunnel_service import CoreDeviceTunnelProxy

logger = logging.getLogger("connect")


async def get_lockdown_client(blocking: bool = True):
    """
    通过 USB 连接到 iOS 设备，获取 lockdown 客户端。

    Lockdown 是 iOS 设备上运行的 usbmuxd 服务的前端，
    通过它可以获取设备信息（UDID、名称、iOS 版本等）。

    Args:
        blocking: True=等待用户操作（CLI），False=立即抛出异常（GUI）

    Returns:
        LockdownClient: 可用于后续操作（隧道、DVT）

    Raises:
        NoDeviceConnectedError: 非阻塞模式下，未找到设备
        DeviceLockedError: 非阻塞模式下，设备已锁定
    """
    logger.debug("Looking for iOS device via USB (blocking=%s)...", blocking)

    if blocking:
        # 阻塞模式: 循环等待设备连接
        while True:
            try:
                lockdown = await create_using_usbmux()
            except NoDeviceConnectedError:
                # 设备未连接: 提示用户插入 USB 并等待回车
                print("Please connect device and press Enter...")
                await asyncio.get_event_loop().run_in_executor(None, input)
            else:
                break
        # 阻塞模式: 循环等待设备解锁
        while True:
            lockdown = await create_using_usbmux()
            if lockdown.all_values.get("PasswordProtected"):
                # 设备已锁: 提示用户解锁
                print("Please unlock device and press Enter...")
                await asyncio.get_event_loop().run_in_executor(None, input)
            else:
                break
        # 重新获取最新的 lockdown 连接
        lockdown = await create_using_usbmux()
    else:
        # 非阻塞模式: 立即抛出异常供上层（GUI）处理
        lockdown = await create_using_usbmux()
        if lockdown.all_values.get("PasswordProtected"):
            raise DeviceLockedError("Device is locked. Please unlock and try again.")

    logger.info("Device connected: udid=%s, name=%s",
                lockdown.udid, lockdown.all_values.get("DeviceName", "unknown"))
    return lockdown


class DeviceLockedError(Exception):
    """设备已连接但处于锁定状态时抛出。"""
    pass


def get_version(lockdown: LockdownClient):
    """获取设备 iOS 版本号（如 ''26.3''）。"""
    return lockdown.all_values.get("ProductVersion")


async def get_developer_mode_status(lockdown: LockdownClient):
    """检查设备是否开启了开发者模式。返回 True/False。"""
    return await lockdown.get_developer_mode_status()


async def reveal_developer_mode(lockdown: LockdownClient):
    """
    在设备的设置中显示开发者模式选项。

    在某些 iOS 版本上，开发者模式选项默认隐藏。
    调用此函数后，用户可以前往 设置 > 隐私与安全性 看到开发者模式开关。
    """
    await AmfiService(lockdown).reveal_developer_mode_option_in_ui()


async def setup_tunnel(lockdown: LockdownClient, protocol: TunnelProtocol = TunnelProtocol.TCP):
    """建立 RSD 隧道 —— 通过 lockdown USB 直连，不依赖 mDNS。

    使用 `CoreDeviceTunnelProxy` lockdown 服务，直接在 USB 上建立 TCP 隧道，
    完全绕过 mDNS/Bonjour 发现过程，解决 Windows 上 mDNS 跨接口失效的问题。

    Returns:
        (tunnel_rsd, tunnel_ctx) 元组:
        - tunnel_rsd: RSD 客户端，用于 DVT 操作
        - tunnel_ctx: 隧道上下文管理器，用于清理
    """


    logger.info("Starting tunnel via lockdown (USB direct)...")
    proxy = await CoreDeviceTunnelProxy.create(lockdown)
    tunnel_ctx = proxy.start_tcp_tunnel()
    tunnel_result = await tunnel_ctx.__aenter__()

    logger.info("Tunnel: %s:%s (%s)",
                tunnel_result.address, tunnel_result.port,
                tunnel_result.protocol)

    # 在隧道上创建 RSD 客户端
    tunnel_rsd = RemoteServiceDiscoveryService(
        (tunnel_result.address, tunnel_result.port)
    )
    await tunnel_rsd.connect()
    logger.info("RSD over tunnel connected")

    return tunnel_rsd, tunnel_ctx