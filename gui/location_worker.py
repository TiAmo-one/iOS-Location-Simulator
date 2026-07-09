# -*- coding: utf-8 -*-
"""
gui/location_worker.py - iOS 定位控制后台线程。

后台工作线程：在独立线程中运行 asyncio 事件循环，
管理 iOS 设备连接和定位模拟的完整生命周期。

架构设计:
    - 继承 QThread 实现真正的后台线程
    - 在线程内运行 asyncio 事件循环（不阻塞 Qt UI）
    - 使用 queue.Queue 实现线程间命令传递（线程安全）
    - 通过 pyqtSignal 与主窗口通信状态变化

生命周期:
    1. start() → run() → _async_run()
    2. 连接循环: 重试直到成功或遇到不可恢复错误
    3. 隧道建立 → DVT 会话打开 → 进入命令循环
    4. stop() → 清定位 → 关会话 → 关隧道 → 发 disconnected 信号
"""
import asyncio
import logging
import traceback
import queue

from PyQt6.QtCore import QThread, pyqtSignal

from pymobiledevice3.exceptions import NoDeviceConnectedError

from driver import connect
from driver.location import LocationSession
from init import init, AdminRequiredError, DeveloperModeDisabledError

logger = logging.getLogger("Worker")


class LocationWorker(QThread):
    """
    定位控制后台线程。

    负责所有与 iOS 设备的通信操作，包括：
        - USB 连接和设备状态检查
        - RSD 隧道建立（remotepairing / TCP）
        - DVT 会话管理（Developer Verification & Testing）
        - 定位坐标设置（LocationSimulation）
        - 资源清理（清除定位 → 关 DVT → 拆隧道）
    """

    # ---- 信号: 与主窗口通信 ----
    status_signal = pyqtSignal(str)          # 状态变化（显示在状态栏）
    error_signal = pyqtSignal(str, str)      # 错误 (标题, 消息): 弹窗
    waiting_device_signal = pyqtSignal()     # 等待设备连接
    device_locked_signal = pyqtSignal()      # 设备已锁定
    dev_mode_off_signal = pyqtSignal()       # 开发者模式未开启
    connected_signal = pyqtSignal()          # 连接成功（隧道 + DVT 就绪）
    disconnected_signal = pyqtSignal()       # 断开连接
    location_set_signal = pyqtSignal(float, float)  # 定位已设置 (纬度, 经度)

    def __init__(self):
        super().__init__()
        # 命令队列: 主线程通过此队列发送指令给工作线程
        # 使用 queue.Queue (线程安全) 而非 asyncio.Queue (非线程安全)
        self._cmd_queue = queue.Queue()
        # _active: True 表示 DVT 会话已打开，可以接收 set 命令
        self._active = False
        # _stop: True 表示请求停止，工作线程应在方便时退出
        self._stop = False

    def run(self):
        """
        QThread 入口: 启动 asyncio 事件循环。

        此方法在独立线程中执行，不阻塞 Qt UI 线程。
        Qt 主线程通过调用 set_location() 和 stop() 来控制本线程。
        """
        try:
            # asyncio.run() 创建新的事件循环并运行直到协程完成
            asyncio.run(self._async_run())
        except Exception as e:
            # 捕获 asyncio.run() 自身可能的异常
            logger.error("Worker crashed: %s\n%s", e, traceback.format_exc())
            self.error_signal.emit("Internal Error", str(e))

    async def _async_run(self):
        """
        异步主流程：连接 → 隧道 → 会话 → 命令循环 → 清理。

        所有异步操作在此协程中顺序执行。
        每个阶段之间通过 _stop 标志支持优雅退出。
        """
        lockdown = None
        tunnel_rsd = None
        tunnel_ctx = None
        session = None

        try:
            # ================================================================
            # 阶段 1: 连接设备（重试循环，直到成功或不可恢复错误）
            # ================================================================
            self.status_signal.emit("Connecting to device...")
            while not self._stop:
                try:
                    # blocking=False: 设备问题立即抛异常，由本循环处理重试
                    lockdown = await init(blocking=False)
                    break  # 成功，退出循环
                except AdminRequiredError as e:
                    # 权限不足: 不可自动恢复，通知用户并退出
                    self.error_signal.emit("Permission Required", str(e))
                    return
                except NoDeviceConnectedError:
                    # 设备未连接: 等待 2 秒后重试
                    self.waiting_device_signal.emit()
                    self.status_signal.emit("Waiting for device...")
                    await asyncio.sleep(2)
                except connect.DeviceLockedError:
                    # 设备已锁定: 等待 2 秒后重试
                    self.device_locked_signal.emit()
                    self.status_signal.emit("Device locked...")
                    await asyncio.sleep(2)
                except DeveloperModeDisabledError as e:
                    # 开发者模式未开启: 不可自动恢复
                    self.dev_mode_off_signal.emit()
                    self.error_signal.emit("Developer Mode Required", str(e))
                    return
                except RuntimeError as e:
                    # 其他运行时错误: 不可恢复
                    self.error_signal.emit("Error", str(e))
                    return

            # 收到停止信号或连接失败，退出
            if self._stop or lockdown is None:
                return

            # ================================================================
            # 阶段 2: 建立 RSD 隧道 (iOS 17+)
            # ================================================================
            self.status_signal.emit("Setting up tunnel...")
            tunnel_rsd, tunnel_ctx = await connect.setup_tunnel(lockdown)

            # ================================================================
            # 阶段 3: 打开持久化 DVT 会话
            # ================================================================
            self.status_signal.emit("Opening location session...")
            session = LocationSession(tunnel_rsd)
            await session.open()

            # 标记会话已激活，通知主窗口可以发送 set 命令
            self._active = True
            self.connected_signal.emit()
            self.status_signal.emit("Ready")
            logger.info("Location session active")

            # ================================================================
            # 阶段 4: 命令循环（处理来自主线程的 set/stop 命令）
            # ================================================================
            while not self._stop:
                try:
                    # 非阻塞获取命令（没有命令就等待 300ms 后重试）
                    cmd = self._cmd_queue.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.3)
                    continue

                action = cmd.get("action")
                if action == "set":
                    # 设置定位指令: 从队列中取出 WGS-84 坐标
                    lat, lng = cmd["lat"], cmd["lng"]
                    await session.set(lat, lng)
                    # 通知主窗口定位已设置
                    self.location_set_signal.emit(lat, lng)
                    self.status_signal.emit("OK: %.6f, %.6f" % (lat, lng))
                # action == "stop" 已在 _stop 标志中处理，循环自然退出

        except Exception as e:
            # 运行期间异常: 记录日志并通知主窗口
            logger.error("Error: %s\n%s", e, traceback.format_exc())
            self.error_signal.emit("Connection Error", str(e))

        finally:
            # ================================================================
            # 清理阶段: 按顺序安全释放所有资源
            # ================================================================
            self._active = False
            if session:
                self.status_signal.emit("Clearing location...")
                try:
                    # 1. 先清除模拟定位（恢复真实 GPS）
                    await session.clear()
                except Exception:
                    pass
                try:
                    # 2. 再关闭 DVT 会话
                    await session.close()
                except Exception:
                    pass
            if tunnel_ctx and tunnel_rsd:
                try:
                    # 3. 最后拆除 RSD 隧道
                    await connect.teardown_tunnel(tunnel_rsd, tunnel_ctx)
                except Exception:
                    pass
            # 通知主窗口已断开（用于恢复 UI 状态）
            self.disconnected_signal.emit()
            self.status_signal.emit("Disconnected")

    def set_location(self, lat: float, lng: float):
        """
        主线程调用: 发送设置定位指令。

        将 WGS-84 坐标放入线程安全队列，
        后台线程会在命令循环中异步处理。

        Args:
            lat: WGS-84 纬度
            lng: WGS-84 经度
        """
        self._cmd_queue.put({"action": "set", "lat": lat, "lng": lng})

    def stop(self):
        """
        主线程调用: 请求停止工作线程。

        设置 _stop 标志并放入一条 stop 命令以唤醒命令循环。
        工作线程不会立即停止，而是在当前操作完成后再退出。
        """
        self._stop = True
        # 放入一条假命令以唤醒命令循环（否则可能在 sleep 中等待）
        self._cmd_queue.put({"action": "stop"})
