# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — 支持单文件和文件夹两种打包模式。

用法:
    build.bat            → 单文件 exe（便携，启动需解压）
    build.bat folder     → 文件夹模式（启动秒开）

通过环境变量 COLLECT_MODE=1 切换文件夹模式。
"""

import os, sys, glob, importlib.util
from importlib.metadata import distributions
from PyInstaller.utils.hooks import copy_metadata

collect_mode = os.environ.get("COLLECT_MODE", "0") == "1"

# ---- 隐藏导入 ----
hiddenimports = [
    "yaml",
    "pymobiledevice3.exceptions",
    "pymobiledevice3.lockdown",
    "pymobiledevice3.remote.common",
    "pymobiledevice3.remote.remote_service_discovery",
    "pymobiledevice3.remote.tunnel_service",
    "pymobiledevice3.remote.remote_service",
    "pymobiledevice3.remote.remote_xpc",
    "pymobiledevice3.remote.utils",
    "pymobiledevice3.remote.bonjour",
    "pymobiledevice3.remote.siphash",
    "pymobiledevice3.remote.xpc_message",
    "pymobiledevice3.services.amfi",
    "pymobiledevice3.services.dvt.instruments.dvt_provider",
    "pymobiledevice3.services.dvt.instruments.location_simulation",
    "pymobiledevice3.dtx_service_provider",
    "pymobiledevice3.service_connection",
    "pymobiledevice3.lockdown_service_provider",
    "pymobiledevice3.usbmux",
    "pymobiledevice3.bonjour",
    "pymobiledevice3.utils",
    "pymobiledevice3.osu.os_utils",
    "pymobiledevice3.pair_records",
    "pymobiledevice3.ca",
]

# ---- 数据文件 ----
datas = [("config.yaml", ".")]
for dist in distributions():
    try:
        datas += copy_metadata(dist.metadata["Name"])
    except Exception:
        pass

# ---- 二进制 DLL ----
binaries = []
conda_lib_bin = os.path.join(sys.prefix, "Library", "bin")
if os.path.isdir(conda_lib_bin):
    for pattern in ["libssl-*.dll", "libcrypto-*.dll", "*expat*.dll",
                     "*ffi*.dll", "sqlite3.dll", "zlib*.dll"]:
        for dll in glob.glob(os.path.join(conda_lib_bin, pattern)):
            binaries.append((dll, "."))

try:
    spec = importlib.util.find_spec("pytun_pmd3")
    if spec and spec.origin:
        pytun_root = os.path.dirname(spec.origin)
        wintun_dir = os.path.join(pytun_root, "wintun", "bin")
        if os.path.isdir(wintun_dir):
            site_packages = os.path.dirname(pytun_root)
            for root, dirs, files in os.walk(wintun_dir):
                for f in files:
                    if f.endswith(".dll"):
                        binaries.append((os.path.join(root, f), os.path.relpath(root, site_packages)))
except Exception:
    pass

# ---- Analysis ----
a = Analysis(
    ["main_gui.py"], pathex=[], binaries=binaries, datas=datas,
    hiddenimports=hiddenimports, hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "pandas", "PIL", "cv2", "scipy"],
    win_no_prefer_redirects=False, win_private_assemblies=False,
    cipher=None, noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

if collect_mode:
    # 文件夹模式：exe 不含数据，数据由 COLLECT 放到旁边
    exe = EXE(
        pyz, a.scripts, [], [], [], [],
        name="iOS_Location_Simulator", debug=False, strip=False,
        bootloader_ignore_signals=False, upx=True, upx_exclude=[],
        runtime_tmpdir=None, console=False, disable_windowed_traceback=False,
        argv_emulation=False, target_arch=None,
        codesign_identity=None, entitlements_file=None, icon=None,
    )
    coll = COLLECT(
        exe, a.binaries, a.zipfiles, a.datas,
        strip=False, upx=True, upx_exclude=[],
        name="iOS_Location_Simulator",
    )
else:
    # 单文件模式：全部打包进 exe
    exe = EXE(
        pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
        name="iOS_Location_Simulator", debug=False, strip=False,
        bootloader_ignore_signals=False, upx=True, upx_exclude=[],
        runtime_tmpdir=None, console=False, disable_windowed_traceback=False,
        argv_emulation=False, target_arch=None,
        codesign_identity=None, entitlements_file=None, icon=None,
    )