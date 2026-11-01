@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "ESCHALON_RUNTIME=%~dp0Eschalon_CN"
"%~dp0Release\narrative_tail_fix\EschalonBook_Chinese_Launcher.exe"
if errorlevel 1 pause
