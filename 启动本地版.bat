@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   废纸回收 Agent 对话助手 - 本地启动
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [错误] 没有找到 python，请先安装 Python 3.9 以上版本。
  echo 下载地址：https://www.python.org/downloads/
  echo 安装时务必勾选 "Add Python to PATH"。
  pause
  exit /b 1
)

echo [1/2] 安装依赖（首次运行需要联网，之后可跳过）...
python -m pip install -q -r requirements.txt

echo [2/2] 启动服务...
echo.
echo   启动后请用浏览器打开： http://localhost:8000
echo   关闭本窗口即停止服务。
echo.
set PYTHONPATH=src
set PORT=8000
python run.py
pause
