@echo off
rem IPCam Detect Studio - GUI ni ishga tushirish (ikki marta bosing)
cd /d "%~dp0"
where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw gui.py
) else (
    python gui.py
)
