@echo off
chcp 65001 >nul
title [StudyBuddy] API Dashboard

echo.
echo  ========================================
echo   StudyBuddy - Learning System Launcher
echo  ========================================
echo.
echo  Starting service...
echo  Browser will open automatically.
echo.
echo  Press Ctrl+C to stop
echo  ========================================
echo.

cd /d "%~dp0"
python data_api.py
