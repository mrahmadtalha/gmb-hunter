@echo off
title GMB Hunter - Jobs List
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python scheduler.py --list
pause