@echo off
title GMB Hunter - Add Job
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python scheduler.py --add
pause