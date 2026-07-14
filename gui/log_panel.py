# -*- coding: utf-8 -*-
"""
gui/log_panel.py - 实时日志面板组件。

提供一个嵌入 GUI 的只读文本面板，通过自定义 logging.Handler
将 Python 日志实时显示在界面上，同时支持日志文件保存。

特性:
    - 线程安全：通过 Qt 信号桥接，支持从任意线程写入
    - 自动滚动：新日志到达时自动滚到底部
    - 行数限制：超过 max_lines 时自动裁剪旧内容
    - 按级别着色：ERROR=红, WARNING=橙, 其他=黑
"""

import logging
from datetime import datetime

from PyQt6.QtWidgets import QPlainTextEdit
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QTextCursor, QTextCharFormat, QColor, QFont


class _LogSignal(QObject):
    """线程安全的日志信号桥接器。

    自定义 logging.Handler 可能在后台线程中 emit()，
    通过 Qt 信号跨线程投递到 GUI 线程安全的 append_log 槽函数。
    """
    log_received = pyqtSignal(int, str)  # (logging level, message)


class LogPanel(QPlainTextEdit):
    """实时日志显示面板。

    继承 QPlainTextEdit，设置为只读模式，通过 LogHandler
    自动接收 Python logging 模块的日志并显示。

    使用方式:
        log_panel = LogPanel()
        handler = log_panel.create_handler()
        logging.getLogger().addHandler(handler)
    """

    # 日志级别对应的颜色
    _LEVEL_COLORS = {
        logging.ERROR:   QColor("#cc0000"),   # 红色
        logging.WARNING: QColor("#e68a00"),   # 橙色
        logging.CRITICAL: QColor("#cc0000"),  # 红色
    }
    _DEFAULT_COLOR = QColor("#1a1a1a")        # 深灰

    def __init__(self, parent=None, max_lines: int = 2000):
        """初始化日志面板。

        Args:
            parent: Qt 父组件
            max_lines: 最大保留行数，超过后自动裁剪前半部分
        """
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(max_lines)
        self.setFont(QFont("Consolas", 9))
        self.setStyleSheet(
            "QPlainTextEdit{border:1px solid #ccc; border-radius:3px; padding:4px;}"
        )

        # 信号桥接器
        self._signal = _LogSignal()
        self._signal.log_received.connect(self._append_log)

    def create_handler(self) -> logging.Handler:
        """创建并返回一个写入此面板的 logging.Handler。

        调用方将此 handler 添加到 root logger 即可。

        Returns:
            LogPanelHandler: 配置好的日志处理器
        """
        return LogPanelHandler(self._signal)


    def _append_log(self, level: int, msg: str):
        """槽函数：接收日志信号并追加到面板（在 GUI 线程中执行）。

        Args:
            level: logging 级别 (DEBUG=10, INFO=20, WARNING=30, ERROR=40)
            msg: 格式化后的日志文本
        """
        color = self._LEVEL_COLORS.get(level, self._DEFAULT_COLOR)
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(msg + "\n", fmt)
        self.ensureCursorVisible()

class LogPanelHandler(logging.Handler):
    """将 Python logging 消息转发到 LogPanel 的 Handler。

    线程安全：通过 emit() 内部的信号投递机制，
    可以安全地从任意线程（包括 QThread）发送日志。
    """

    def __init__(self, signal: _LogSignal):
        super().__init__()
        self._signal = signal
        self.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)-5s] %(name)s: %(message)s"
        ))

    def emit(self, record: logging.LogRecord):
        """接收日志记录，格式化后通过信号发送到 GUI 线程。"""
        try:
            msg = self.format(record)
            self._signal.log_received.emit(record.levelno, msg)
        except Exception:
            self.handleError(record)