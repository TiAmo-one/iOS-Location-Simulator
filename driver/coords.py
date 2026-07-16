# -*- coding: utf-8 -*-
"""坐标转换：BD-09 → GCJ-02 → WGS-84。

中国坐标系说明:
    BD-09:  百度地图坐标系（有偏移）
    GCJ-02: 国测局坐标系（火星坐标），中国法定坐标系
    WGS-84: 全球卫星定位坐标系，iOS / Google 使用

转换流程: BD-09 → GCJ-02 → WGS-84（两步转换）
"""
import math

# 常量
_X_PI = 3.14159265358979324 * 3000.0 / 180.0
_PI = 3.141592653589793238462643383
_A = 6378245.0                       # 地球长半轴 (WGS-84 椭球体参数)
_EE = 0.00669342162296594323         # 第一偏心率平方


def _transform_lat(x: float, y: float) -> float:
    """GCJ-02 纬度偏移量计算（非线性变换）。"""
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * _PI) + 20.0 * math.sin(2.0 * x * _PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(y * _PI) + 40.0 * math.sin(y / 3.0 * _PI)) * 2.0 / 3.0
    ret += (160.0 * math.sin(y / 12.0 * _PI) + 320 * math.sin(y * _PI / 30.0)) * 2.0 / 3.0
    return ret


def _transform_lon(x: float, y: float) -> float:
    """GCJ-02 经度偏移量计算（非线性变换）。"""
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * _PI) + 20.0 * math.sin(2.0 * x * _PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(x * _PI) + 40.0 * math.sin(x / 3.0 * _PI)) * 2.0 / 3.0
    ret += (150.0 * math.sin(x / 12.0 * _PI) + 300.0 * math.sin(x / 30.0 * _PI)) * 2.0 / 3.0
    return ret


def bd09_to_wgs84(lat: float, lng: float) -> tuple:
    """百度坐标 (BD-09) → WGS-84 坐标。

    Args:
        lat: BD-09 纬度
        lng: BD-09 经度

    Returns:
        (wgs84_lat, wgs84_lng): WGS-84 经纬度
    """
    # 第一步：BD-09 → GCJ-02
    x = lng - 0.0065
    y = lat - 0.006
    z = math.sqrt(x * x + y * y) - 0.00002 * math.sin(y * _X_PI)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * _X_PI)
    gcj_lng = z * math.cos(theta)
    gcj_lat = z * math.sin(theta)

    # 第二步：GCJ-02 → WGS-84
    d_lat = _transform_lat(gcj_lng - 105.0, gcj_lat - 35.0)
    d_lng = _transform_lon(gcj_lng - 105.0, gcj_lat - 35.0)
    rad_lat = gcj_lat / 180.0 * _PI
    magic = 1 - _EE * math.sin(rad_lat) * math.sin(rad_lat)
    sqrt_magic = math.sqrt(magic)
    d_lng = (d_lng * 180.0) / (_A / sqrt_magic * math.cos(rad_lat) * _PI)
    d_lat = (d_lat * 180.0) / (_A * (1 - _EE) / (magic * sqrt_magic) * _PI)

    return (gcj_lat - d_lat, gcj_lng - d_lng)