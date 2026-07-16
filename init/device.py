# -*- coding: utf-8 -*-
"""
init/init.py - 设备就绪检查（支持 GUI 非阻塞模式）。

设备初始化模块：执行连接前的所有必要检查。

检查项:
    1. 管理员权限（Windows: 管理员, macOS: root）
    2. 设备已通过 USB 连接
    3. 设备已解锁（非锁屏状态）
    4. iOS 版本 >= 17.0
    5. 开发者模式已开启

两种模式:
    - blocking=True: CLI 交互模式，等待用户处理问题
    - blocking=False: GUI 模式，抛出异常由调用方弹窗提示
"""
import sys
import ctypes
import os
import logging

from driver import connect

logger = logging.getLogger("init")


class DeveloperModeDisabledError(Exception):
    """开发者模式未开启（设备上需要手动启用）。"""
    pass


class AdminRequiredError(Exception):
    """程序需要管理员/root 权限才能创建虚拟网络接口。"""
    pass


async def init(blocking: bool = True):
    """
    设备初始化入口函数。

    按顺序检查所有前置条件，任一不满足则抛出对应异常。

    Args:
        blocking: True=CLI 模式等待用户操作；False=GUI 模式立即抛出

    Returns:
        LockdownClient: 已连接的设备 lockdown 客户端

    Raises:
        AdminRequiredError: 未以管理员身份运行
        NoDeviceConnectedError: 未检测到 iOS 设备
        connect.DeviceLockedError: 设备已连接但已锁定
        DeveloperModeDisabledError: 开发者模式未开启
    """
    # ---- 1. 检查管理员权限 ----
    if sys.platform == "win32":
        # Windows: 调用 Shell32 API 检查是否以管理员身份运行
        if not ctypes.windll.shell32.IsUserAnAdmin():
            raise AdminRequiredError("Please run as administrator")
    elif sys.platform == "darwin":
        # macOS: 检查 euid（有效用户 ID）是否为 0（root）
        if os.geteuid() != 0:
            raise AdminRequiredError("Please run as root")
    else:
        raise RuntimeError("Only macOS and Windows are supported")

    # ---- 2. 连接设备并检查状态 ----
    lockdown = await connect.get_lockdown_client(blocking=blocking)

    # ---- 3. 检查 iOS 版本 ----
    version = connect.get_version(lockdown)
    logger.info("Device: udid=%s, iOS=%s", lockdown.udid, version)

    # iOS 17 以下不支持 DVT 定位模拟
    if int(version.split(".")[0]) < 17:
        raise RuntimeError(f"iOS {version} is not supported (need 17+)")

    # ---- 4. 检查开发者模式 ----
    dev_mode = await connect.get_developer_mode_status(lockdown)
    if not dev_mode:
        if blocking:
            # CLI 模式: 尝试自动显示开发者模式选项
            await connect.reveal_developer_mode(lockdown)
        raise DeveloperModeDisabledError(
            "Developer Mode is OFF.\n"
            "Go to Settings > Privacy & Security > Developer Mode to enable it.\n"
            "Then reboot the device and enter your passcode."
        )

    return lockdown
