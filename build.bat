@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
echo ============================================
echo  Check Finder - Build
echo ============================================
echo.
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    pause
    exit /b 1
)
echo [Step 1/2] Installing packages...
python build_helper.py install
if errorlevel 1 ( pause & exit /b 1 )
echo.
echo [Step 2/2] Building exe...
python build_helper.py release
if errorlevel 1 ( pause & exit /b 1 )
echo.
echo ============================================
echo  Done! Check output above.
echo ============================================
pause
