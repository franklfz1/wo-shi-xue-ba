@echo off
chcp 65001 >nul
echo ==========================================
echo   我是学霸 — 一键安装脚本 (Windows)
echo ==========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+
    echo 下载地址：https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] 安装 Python 依赖...
pip install -r requirements.txt
if errorlevel 1 (
    echo [警告] 部分依赖安装失败，请检查上方日志
    pause
    exit /b 1
)
echo [1/4] Python 依赖安装完成
echo.

echo [2/4] 检查 FFmpeg...
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo [提示] 未检测到 FFmpeg，视频制作功能将不可用
    echo 安装方式：winget install ffmpeg
) else (
    echo [2/4] FFmpeg 已安装
)
echo.

echo [3/4] 初始化教学产物目录...
python artifacts_init.py --init
echo [3/4] 产物目录初始化完成
echo.

echo [4/4] 安装完成！
echo.
echo ==========================================
echo   接下来：
echo   1. 在 WorkBuddy 中打开本项目
echo   2. 说"初始化"一键完成系统配置
echo   3. 说"切换成数学老师"开始学习
echo ==========================================
echo.
pause
