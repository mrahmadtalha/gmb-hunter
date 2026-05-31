@echo off
title GMB Hunter Dashboard
color 0A
echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║         GMB HUNTER — Dashboard                   ║
echo  ║         Opening http://localhost:5000            ║
echo  ╚══════════════════════════════════════════════════╝
echo.
cd /d "%~dp0"
call .venv\Scripts\activate.bat
start http://localhost:5000
python dashboard.py
pause