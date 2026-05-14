@echo off
set "ROOT=%~dp0"
if /i "%ROOT:~-8%"=="scripts\" set "ROOT=%ROOT:~0,-8%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%scripts\start_jarvis_dialog.ps1"