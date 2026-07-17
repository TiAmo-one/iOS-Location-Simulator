# iOS Location Simulator

基于 pymobiledevice3 的 iOS 17+ 定位模拟器，支持 GUI 地图选点和 CLI 命令行两种模式。

## 功能

- 🗺️ **GUI 地图选点**: Leaflet 地图点击选择目标坐标
- 📍 **实时模拟**: 通过 DVT 协议实时修改 iPhone/iPad GPS 定位
- 🔧 **随时更新**: 连接后可随时修改坐标，实时生效
- ♻️ **一键恢复**: 关闭程序自动恢复真实 GPS
- 🌐 **支持离线**: CLI 模式可完全离线运行，GUI 模式离线时自动提示手动输入坐标

## 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10+ (管理员) / macOS (root) |
| iOS 版本 | 17.0 及以上 |
| 开发者模式 | 必须开启 |
| 连接方式 | USB 数据线（需解锁并信任） |

## 离线运行

本软件核心定位模拟功能**不需要网络**，仅通过 USB 数据线即可完成：

| 模式 | 离线可用性 | 说明 |
|------|-----------|------|
| **CLI 命令行** | ✅ 完全支持 | 所有功能均可离线使用，坐标通过 `config.yaml` 预设或手动输入 |
| **GUI 图形界面** | ⚠️ 地图无法显示 | 定位功能正常，但 Leaflet 地图瓦片需要联网加载；离线时界面自动提示手动输入坐标 |

> **提示**: 离线使用 GUI 时，可先打开 [百度拾取坐标](https://api.map.baidu.com/lbsapi/getpoint/index.html) 获取 BD-09 坐标，然后手动粘贴到输入框中。

## 快速开始

### 方式一: 源码运行（需安装 Python）

```bash
# 1. 创建 conda 环境
conda create -n 你的环境名 python=3.13 -y
conda activate 你的环境名

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行
python main_gui.py    # GUI 模式
python main.py        # CLI 命令行模式
```

> Windows 用户无需安装 Visual C++ Build Tools，`lzfse` 已提供预编译 wheel。

### 方式二: 打包为独立 exe

支持两种打包模式，通过 `build.bat` 一键构建：

```bash
conda activate 你的环境名
pip install -r requirements.txt

.\build.bat              # 单文件模式（默认）
.\build.bat folder       # 文件夹模式
```

| 模式 | 命令 | 输出 | 特点 |
|------|------|------|------|
| **单文件** | `build.bat` | `dist/iOS_Location_Simulator.exe` (~176 MB) | 单个 exe，便携易分发，启动需解压（稍慢） |
| **文件夹** | `build.bat folder` | `dist/iOS_Location_Simulator/` (~417 MB) | 文件夹输出，启动秒开，需整体复制 |

> 打包输出无需安装 Python，复制到任意电脑即可运行。
## 项目结构

```
iOSRealRun-cli-17-fix-quic/
├── main_gui.py              # GUI 入口
├── main.py                  # CLI 入口
├── run.py                   # 定位逻辑、坐标转换
├── config.py                # YAML 配置加载
├── config.yaml              # 用户配置文件
├── build.bat                # 一键打包脚本
├── ios_loc_sim.spec         # PyInstaller 打包配置
├── requirements.txt         # Python 依赖
├── wheels/                  # 预编译 wheel 文件
│   └── lzfse-*.whl          #   lzfse (避免 MSVC 编译)
├── .gitignore               # Git 忽略规则
├── README.md
│
├── driver/                  # 驱动层
│   ├── __init__.py
│   ├── connect.py           # USB 连接、RSD 隧道建立
│   └── location.py          # DVT 定位会话管理
│
├── gui/                     # GUI 层
│   ├── __init__.py
│   ├── main_window.py       # 主窗口（地图、按钮、输入框）
│   ├── location_worker.py   # 后台线程（设备通信）
│   └── log_panel.py         # 实时日志面板
│
└── init/                    # 初始化层
    ├── __init__.py
    └── init.py              # 设备就绪检查
```

## 坐标系统

- 地图使用 **WGS-84** 坐标系统（Leaflet / iOS 原生）
- `config.yaml` 中的坐标为 **BD-09**（百度坐标系），程序自动转换
- 转换流程: BD-09 -> GCJ-02（火星坐标）-> WGS-84

## 常见问题

| 问题 | 解决 |
|------|------|
| 启动后无设备 | 检查 USB 连接，确保已解锁并信任 |
| 开发者模式未开启 | 设置 -> 隐私与安全性 -> 开发者模式（需重启） |
| 权限不足 | 右键以管理员身份运行 |
| 定位未生效 | 确保程序保持运行（DVT 会话需持续开放） |
| 打包后 DLL 报错 | PyQt6 必须使用 6.8.1，6.9+ 不兼容 PyInstaller |
| 新电脑无法连接隧道 | 本版本已通过 USB 直连解决，无需 iTunes/Bonjour |
| GUI 地图不显示 | 可能处于离线状态，输入框仍可手动输入坐标；联网后自动恢复 |
| CLI 如何获取坐标 | 打开 [百度拾取坐标](https://api.map.baidu.com/lbsapi/getpoint/index.html)，点击地图复制经纬度 |

## License

本项目基于 GitHub 开源项目修改，仅供学习研究使用。