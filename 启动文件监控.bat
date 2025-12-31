@echo off
chcp 65001 >nul
cd /d "%~dp0"
start /min "" pythonw main.py
exit
