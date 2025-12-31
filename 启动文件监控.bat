@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动文件监控自动同步工具...
python main.py
pause

