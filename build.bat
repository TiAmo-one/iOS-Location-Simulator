@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

echo ============================================================
echo   iOS Location Simulator - Build
echo ============================================================
echo.

echo [1/3] Checking dependencies...
python -c "import PyQt6; import pymobiledevice3; print('  OK')" 2>nul
if errorlevel 1 (
    echo [ERROR] Dependencies not installed.
    echo Run: pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo [2/3] Cleaning old build...
if exist "build" rmdir /s /q "build"
if exist "dist\iOS_Location_Simulator" rmdir /s /q "dist\iOS_Location_Simulator"

echo.
echo [3/3] Building (3-7 minutes)...
echo.
python -m PyInstaller ios_loc_sim.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo [FAILED] Build error - check messages above.
    pause
    exit /b 1
)

echo.
echo ============================================================
del "dist\iOS_Location_Simulator.exe" 2>nul
echo   Output: dist\iOS_Location_Simulator\
echo ============================================================
echo.
echo Copy the iOS_Location_Simulator folder to any PC and run
echo iOS_Location_Simulator.exe as Administrator.
echo.
pause
