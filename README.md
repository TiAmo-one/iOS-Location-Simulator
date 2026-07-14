# iOS Location Simulator

基于 pymobiledevice3 的 iOS 17+ 定位模拟器，支持 GUI 地图选点和 CLI 命令行两种模式。

## 功能

- 🗺️ **GUI 地图选点**: Leaflet 地图点击选择目标坐标
- 📍 **实时模拟**: 通过 DVT 协议实时修改 iPhone/iPad GPS 定位
- 🔧 **随时更新**: 连接后可随时修改坐标，实时生效
- ♻️ **一键恢复**: 关闭程序自动恢复真实 GPS

## 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10+ (管理员) / macOS (root) |
| iOS 版本 | 17.0 及以上 |
| 开发者模式 | 必须开启 |
| 连接方式 | USB 数据线（需解锁并信任） |

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

```bash
conda activate 你的环境名
pip install -r requirements.txt

# 一键打包（推荐）
.\build.bat

# 或手动打包
python -m PyInstaller ios_loc_sim.spec --clean --noconfirm
```

输出为 `dist/iOS_Location_Simulator.exe`（单文件），复制到任意电脑即可运行，无需安装 Python。

> 如需预编译版本，请查看 [Releases](https://github.com/TiAmo-one/iOS-Location-Simulator/releases) 页面下载。

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

## License

本项目基于 GitHub 开源项目修改，仅供学习研究使用。