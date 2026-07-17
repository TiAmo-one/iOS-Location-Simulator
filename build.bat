@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

set MODE=%1
if "%MODE%"=="" set MODE=onefile
if /i "%MODE%"=="folder" set COLLECT_MODE=1& set MODE_LABEL=Folder
if /i "%MODE%"=="onefile" set COLLECT_MODE=0& set MODE_LABEL=Single File

echo ============================================================
echo   iOS Location Simulator - Build [%MODE_LABEL%]
echo ============================================================
echo.
echo   onefile  = single .exe (portable, slower startup^)
echo   folder   = folder output (fast startup, needs whole folder^)
echo   Usage: build.bat [onefile^|folder]
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
if exist "dist\iOS_Location_Simulator.exe" del /q "dist\iOS_Location_Simulator.exe"

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
if "%COLLECT_MODE%"=="1" (
    if exist "dist\iOS_Location_Simulator.exe" del /q "dist\iOS_Location_Simulator.exe"
    echo   Output: dist\iOS_Location_Simulator\  (folder)
) else (
    echo   Output: dist\iOS_Location_Simulator.exe  (single file)
)
echo ============================================================
echo.
pause