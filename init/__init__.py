# -*- coding: utf-8 -*-
"""
init/__init__.py - 初始化子包

提供设备初始化入口函数和异常类。

导出:
    - init(): 设备就绪检查（管理员权限 / USB 连接 / 解锁 / iOS 版本 / 开发者模式）
    - AdminRequiredError: 未以管理员身份运行
    - DeveloperModeDisabledError: 开发者模式未开启
"""
from init.init import init, AdminRequiredError, DeveloperModeDisabledError
