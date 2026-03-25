@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
echo 正在啟動支票查詢系統...
python main.py
if errorlevel 1 (
    echo.
    echo [錯誤] 程式啟動失敗
    echo 請確認已執行 build.bat 安裝相依套件
    pause
)
