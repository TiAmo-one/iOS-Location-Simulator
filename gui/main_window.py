# -*- coding: utf-8 -*-
"""
gui/main_window.py - 主窗口界面
===============================
包含地图显示、坐标控制、定位操作按钮的完整 GUI。

布局结构:
    ┌──────────────────────────────────────────┐
    │ Target: Lat: [____] Lng: [____]          │
    │ [Set Location]  [Restore Location]       │
    ├──────────────────────────────────────────┤
    │                                          │
    │        Leaflet 地图 (WGS-84 坐标系)       │
    │        - 点击选坐标                       │
    │        - 标记显示目标/模拟位置             │
    │        - 拖拽/缩放                       │
    │                                          │
    └──────────────────────────────────────────┘
    ┌──────────────────────────────────────────┐
    │ 状态栏: 实时连接状态 / 定位信息            │
    └──────────────────────────────────────────┘

交互逻辑:
    1. 在地图上点击 → 坐标自动填入输入框
    2. 手动输入坐标 → 地图标记跟随更新
    3. 点击 Set Location → 禁用地图 → 连接设备 → 设置定位
    4. 连接成功后按钮变为 Update Location，可随时更新坐标
    5. 点击 Restore Location → 清除定位 → 断开连接 → 恢复地图交互
"""

import logging

from PyQt6.QtWidgets import (
    QWidget,
    QMainWindow, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QStatusBar, QMessageBox
)
from PyQt6.QtCore import Qt, QUrl, pyqtSlot, QObject
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel

from gui.location_worker import LocationWorker
from gui.log_panel import LogPanel

logger = logging.getLogger("GUI")

# ============================================================
#  内嵌 Leaflet 地图 HTML
#  ============================================================
#  使用高德地图瓦片（国内全覆盖，免费，无需 API Key）
#  通过 QWebChannel 实现 JavaScript ↔ Python 双向通信
#  ============================================================
MAP_HTML = r"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<!-- QWebChannel 桥接：让 JS 可以调用 Python 方法 -->
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<style>
*{margin:0;padding:0}html,body{height:100%}#map{height:100%}.leaflet-control-attribution{pointer-events:none}
</style>
</head><body>
<div id="map"></div>
<script>
// ---------- 初始化地图 ----------
// 默认中心点：成都 (30.3116, 104.3192)，缩放级别 15
var map = L.map("map",{center:[30.3116,104.3192],zoom:15});

// 使用高德地图瓦片（国内最全最清晰）
L.tileLayer("https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}",{maxZoom:18,maxNativeZoom:18,subdomains:"1234",attribution:"&copy; 高德地图"}).addTo(map);

var marker = null;       // 当前地图标记
var backend = null;      // Python 端 MapBridge 对象
var mapEnabled = true;   // 地图交互开关

// ---------- QWebChannel 连接 ----------
new QWebChannel(qt.webChannelTransport, function(ch) {
    backend = ch.objects.backend;
});

// ---------- 地图点击事件 ----------
map.on("click", function(e) {
    if (!mapEnabled) return;  // 连接中禁用地图点击
    var lat = e.latlng.lat.toFixed(6);
    var lng = e.latlng.lng.toFixed(6);
    if (marker) map.removeLayer(marker);
    marker = L.marker([lat, lng]).addTo(map)
        .bindPopup("Lat:" + lat + "<br>Lng:" + lng).openPopup();
    // 通知 Python 端坐标已更改
    if (backend) backend.map_clicked(parseFloat(lat), parseFloat(lng));
});

// ---------- Python 可调用的 JS 函数 ----------
function setMarker(lat, lng, title) {
    if (marker) map.removeLayer(marker);
    marker = L.marker([lat, lng]).addTo(map)
        .bindPopup(title || "Location").openPopup();
    map.setView([lat, lng], map.getZoom());
}
function clearMarker() {
    if (marker) { map.removeLayer(marker); marker = null; }
}
function disableMap() { mapEnabled = false; map.dragging.disable(); }
function enableMap()  { mapEnabled = true;  map.dragging.enable();  }
</script>
</body></html>"""


class MapBridge(QObject):
    """
    QWebChannel 桥接对象。
    
    注册到 QWebChannel 后，JavaScript 可通过 backend.map_clicked(lat, lng)
    调用此对象的 map_clicked 槽函数，实现地图点击 → Python 回调。
    
    继承 QObject（而非 QWidget），避免暴露大量无关的 Widget 属性到 JS。
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._callback = None  # 点击回调函数: (lat, lng) -> None

    def set_callback(self, callback):
        """设置地图点击的回调函数。"""
        self._callback = callback

    @pyqtSlot(float, float)
    def map_clicked(self, lat: float, lng: float):
        """JS 调用：用户在地图上点击了坐标。"""
        if self._callback:
            self._callback(lat, lng)


class MainWindow(QMainWindow):
    """
    应用程序主窗口。
    
    负责:
    - 管理 UI 布局（按钮、输入框、地图）
    - 控制 LocationWorker 线程的生命周期
    - 处理用户交互（点击地图、输入坐标、按钮操作）
    - 显示设备连接状态和错误信息
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("iOS Location Simulator")
        self.resize(1100, 750)

        # ---------- 状态变量 ----------
        self._worker = None          # LocationWorker 后台线程
        self._current_lat = 30.3116  # 当前目标纬度（WGS-84）
        self._current_lng = 104.3192 # 当前目标经度（WGS-84）
        self._location_active = False # 是否已成功设置定位
        self._connecting = False      # 是否正在连接中

        self._setup_ui()
        self._setup_map()

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - connect device to begin")

    # ================================================================
    #  UI 构建
    # ================================================================

    def _setup_ui(self):
        """构建用户界面布局。"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # ---- 顶栏：坐标输入 + 操作按钮 ----
        top_bar = QHBoxLayout()

        top_bar.addWidget(QLabel("Target:"))
        self.lat_input = QLineEdit(f"{self._current_lat:.6f}")
        self.lat_input.setFixedWidth(110)
        top_bar.addWidget(QLabel("Lat:"))
        top_bar.addWidget(self.lat_input)

        self.lng_input = QLineEdit(f"{self._current_lng:.6f}")
        self.lng_input.setFixedWidth(110)
        top_bar.addWidget(QLabel("Lng:"))
        top_bar.addWidget(self.lng_input)

        top_bar.addSpacing(15)

        # Set Location / Update Location 按钮（绿色）
        self.set_btn = QPushButton("Set Location")
        self.set_btn.setFixedWidth(130)
        self.set_btn.setStyleSheet(
            "QPushButton{background:#4CAF50;color:white;font-weight:bold;"
            "padding:8px;border-radius:4px}"
            "QPushButton:hover{background:#45a049}"
            "QPushButton:disabled{background:#ccc}"
        )
        self.set_btn.clicked.connect(self._on_set_location)
        top_bar.addWidget(self.set_btn)

        # Restore Location 按钮（红色）
        self.restore_btn = QPushButton("Restore Location")
        self.restore_btn.setFixedWidth(140)
        self.restore_btn.setEnabled(False)
        self.restore_btn.setStyleSheet(
            "QPushButton{background:#f44336;color:white;font-weight:bold;"
            "padding:8px;border-radius:4px}"
            "QPushButton:hover{background:#da190b}"
            "QPushButton:disabled{background:#ccc}"
        )
        self.restore_btn.clicked.connect(self._on_restore_location)
        top_bar.addWidget(self.restore_btn)

        top_bar.addStretch()
        layout.addLayout(top_bar)

        # ---- 地图区域 ----
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view, stretch=1)

        # ---- 日志面板区域 ----
        self.log_panel = LogPanel(max_lines=1500)
        self.log_panel.setFixedHeight(160)
        layout.addWidget(self.log_panel)

        # 坐标输入框变化时同步更新地图标记
        self.lat_input.textChanged.connect(self._on_coord_input_changed)
        self.lng_input.textChanged.connect(self._on_coord_input_changed)

    def _setup_map(self):
        """
        初始化 WebEngine 地图。
        
        通过 QWebChannel 注册 MapBridge，使 JS 可以调用 Python 方法。
        """
        self._channel = QWebChannel()
        self._bridge = MapBridge()
        self._bridge.set_callback(self._on_map_clicked)
        self._channel.registerObject("backend", self._bridge)
        self.web_view.page().setWebChannel(self._channel)
        self.web_view.setHtml(MAP_HTML)

    # ================================================================
    #  用户交互处理
    # ================================================================

    def _on_map_clicked(self, lat: float, lng: float):
        """地图点击回调：将坐标填入输入框。"""
        self._current_lat = lat
        self._current_lng = lng
        # 阻止信号以避免递归更新
        self.lat_input.blockSignals(True)
        self.lng_input.blockSignals(True)
        self.lat_input.setText(f"{lat:.6f}")
        self.lng_input.setText(f"{lng:.6f}")
        self.lat_input.blockSignals(False)
        self.lng_input.blockSignals(False)

    def _on_coord_input_changed(self):
        """坐标输入框文本变化：更新地图上的目标标记。"""
        try:
            lat = float(self.lat_input.text())
            lng = float(self.lng_input.text())
            self._current_lat = lat
            self._current_lng = lng
            self.web_view.page().runJavaScript(
                f"setMarker({lat},{lng},'Target: {lat:.6f},{lng:.6f}');"
            )
        except ValueError:
            pass  # 非法输入时忽略

    # ================================================================
    #  UI 状态控制
    # ================================================================

    def _disable_ui(self):
        """连接中：禁用地图和输入控件，防止用户误操作。"""
        self._connecting = True
        self.set_btn.setEnabled(False)
        self.restore_btn.setEnabled(False)
        self.lat_input.setEnabled(False)
        self.lng_input.setEnabled(False)
        self.web_view.page().runJavaScript("disableMap();")

    def _enable_ui(self):
        """连接成功：恢复地图交互，按钮变为 Update Location。"""
        self._connecting = False
        self.set_btn.setEnabled(True)
        self.restore_btn.setEnabled(True)
        self.lat_input.setEnabled(True)
        self.lng_input.setEnabled(True)
        self.web_view.page().runJavaScript("enableMap();")
        self.set_btn.setText("Update Location")

    def _enable_ui_on_failure(self):
        """连接失败：恢复 UI 到初始状态。"""
        self._location_active = False
        self._connecting = False
        self.set_btn.setText("Set Location")
        self.set_btn.setEnabled(True)
        self.restore_btn.setEnabled(False)
        self.lat_input.setEnabled(True)
        self.lng_input.setEnabled(True)
        self.web_view.page().runJavaScript("enableMap();")

    # ================================================================
    #  按钮事件
    # ================================================================

    def _on_set_location(self):
        """
        Set Location 按钮点击:
        - 首次点击：创建 LocationWorker 线程，开始连接设备
        - 已连接后点击：发送坐标更新命令
        """
        if self._location_active:
            # 已连接：直接更新定位坐标
            lat, lng = self._get_coords()
            if self._worker and self._worker._active:
                self._worker.set_location(lat, lng)
                self.web_view.page().runJavaScript(
                    f"setMarker({lat},{lng},'Simulated');"
                )
            return

        if self._connecting:
            return  # 正在连接中，忽略重复点击

        # 禁用 UI，开始连接
        self._disable_ui()
        self.status_bar.showMessage("Connecting to device...")

        lat, lng = self._get_coords()
        self._pending_location = (lat, lng)  # 连接成功后自动设置此坐标

        # 创建并启动后台工作线程
        self._worker = LocationWorker()
        self._worker.status_signal.connect(self._on_status)
        self._worker.error_signal.connect(self._on_error)
        self._worker.waiting_device_signal.connect(self._on_waiting_device)
        self._worker.device_locked_signal.connect(self._on_device_locked)
        self._worker.dev_mode_off_signal.connect(self._on_dev_mode_off)
        self._worker.connected_signal.connect(self._on_connected)
        self._worker.disconnected_signal.connect(self._on_disconnected)
        self._worker.location_set_signal.connect(self._on_location_set)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_restore_location(self):
        """Restore Location 按钮：停止定位模拟，恢复真实 GPS。"""
        if self._worker:
            self.status_bar.showMessage("Restoring...")
            self._worker.stop()  # 发送停止信号
        self._location_active = False
        self._connecting = False
        self.set_btn.setText("Set Location")
        self.set_btn.setEnabled(True)
        self.restore_btn.setEnabled(False)
        self.lat_input.setEnabled(True)
        self.lng_input.setEnabled(True)

    # ================================================================
    #  Worker 信号回调
    # ================================================================

    def _on_waiting_device(self):
        """设备未连接（worker 每 2 秒重试，状态栏提示）。"""
        self.status_bar.showMessage(
            "Waiting for device - connect via USB, unlock, and trust"
        )

    def _on_device_locked(self):
        """设备已锁定（worker 每 2 秒重试，状态栏提示）。"""
        self.status_bar.showMessage("Device locked - please unlock")

    def _on_dev_mode_off(self):
        """开发者模式未开启（弹窗警告，不可自动恢复）。"""
        self.status_bar.showMessage("Developer mode required")
        QMessageBox.warning(
            self, "Developer Mode Required",
            "Developer Mode is not enabled on your device.\n\n"
            "To enable it:\n"
            "1. Go to Settings > Privacy & Security\n"
            "2. Tap Developer Mode and turn it ON\n"
            "3. Reboot the device and enter your passcode\n"
            "4. Run this program again"
        )

    def _on_connected(self):
        """Worker 成功建立隧道并打开 DVT 会话。"""
        self._location_active = True
        self._enable_ui()
        self.status_bar.showMessage("Connected - setting location...")
        # 设置用户在连接前选择的坐标
        if hasattr(self, "_pending_location"):
            lat, lng = self._pending_location
            self._worker.set_location(lat, lng)
            del self._pending_location

    def _on_location_set(self, lat: float, lng: float):
        """定位已成功设置到设备。更新地图上的模拟标记。"""
        self.web_view.page().runJavaScript(
            f"setMarker({lat},{lng},'Simulated');"
        )
        self.status_bar.showMessage(f"Location active: {lat:.6f}, {lng:.6f}")

    def _on_disconnected(self):
        """Worker 已断开连接（正常退出或错误）。"""
        self.web_view.page().runJavaScript("clearMarker();enableMap();")
        self._location_active = False
        self._connecting = False
        self.set_btn.setText("Set Location")
        self.set_btn.setEnabled(True)
        self.restore_btn.setEnabled(False)
        self.lat_input.setEnabled(True)
        self.lng_input.setEnabled(True)
        self.status_bar.showMessage("Location restored")

    def _on_status(self, msg: str):
        """Worker 状态变化：显示在状态栏。"""
        self.status_bar.showMessage(msg)

    def _on_error(self, title: str, msg: str):
        if not msg:
            msg = "(no details available - check logs for more info)"
        QMessageBox.critical(self, title, msg)
        self._enable_ui_on_failure()
    def _on_worker_finished(self):
        """Worker 线程已结束。"""
        self._worker = None

    # ================================================================
    #  辅助方法
    # ================================================================

    def _get_coords(self) -> tuple:
        """从输入框获取当前坐标，非法时返回默认值。"""
        try:
            return float(self.lat_input.text()), float(self.lng_input.text())
        except ValueError:
            return self._current_lat, self._current_lng

    def closeEvent(self, event):
        """
        窗口关闭事件：确保正确清理资源。
        先停止定位（清除模拟 + 断开连接），再关闭窗口。
        """
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(5000)  # 等待最多 5 秒
        event.accept()

