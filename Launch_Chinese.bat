@echo off
chcp 65001 >nul
cd /d "%~dp0"
"C:\Users\zfyu2\AppData\Local\Programs\Python\Python312\python.exe" -u start_chinese.py
if errorlevel 1 pause
