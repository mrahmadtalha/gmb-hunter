@echo off
title GMB Hunter - Auto Scheduler
color 0A
echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║         GMB HUNTER — Auto Scheduler              ║
echo  ║         Starting...                              ║
echo  ╚══════════════════════════════════════════════════╝
echo.
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python scheduler.py
pause