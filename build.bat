@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================
echo   iOS Location Simulator - 一键构建
echo ============================================================
echo.

REM ---- 检查 conda 环境是否已激活 ----
python -c "import sys; sys.exit(0 if 'conda' in sys.version or 'CONDA_PREFIX' in __import__('os').environ else 1)" 2>nul
if errorlevel 1 (
    echo [提示] 建议使用 conda 环境，当前未检测到 conda
    echo.
)

echo [1/3] 验证依赖...
python -c "import PyQt6; import pymobiledevice3; print('  依赖检查通过')" 2>nul
if errorlevel 1 (
    echo [错误] 依赖未安装，请先运行:
    echo   conda create -n 你的环境名 python=3.13 -y
    echo   conda activate 你的环境名
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo [2/3] 清理旧构建...
if exist "build" rmdir /s /q "build"
if exist "dist\iOS_Location_Simulator" rmdir /s /q "dist\iOS_Location_Simulator"

echo.
echo [3/3] 开始打包（约 3-7 分钟）...
echo.
python -m PyInstaller ios_loc_sim.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo [失败] 构建出错，请检查上方错误信息
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   构建成功！
echo   输出目录: dist\iOS_Location_Simulator\
echo   可执行文件: dist\iOS_Location_Simulator\iOS_Location_Simulator.exe
echo ============================================================
echo.
echo 将整个 iOS_Location_Simulator 文件夹拷贝到目标电脑即可运行。
echo 运行时必须以管理员身份运行！
echo.
pause
