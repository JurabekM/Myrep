@echo off
rem Zarbxona v3 - kerakli paketlar o'rnatilgan Python'ni o'zi topadi.
rem Bir nechta Python bo'lsa py.exe eng yangisini tanlaydi - bunga ishonmaymiz:
rem har birini sinaymiz. aetherq_core bor muhit afzal (onlayn topshirish uchun).
rem Tartib: %%ZARBXONA_PYTHON%% -> .venv -> "py -0p" ro'yxati -> "where python".
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"

set "TANLANGAN="
set "ZAXIRA="

if defined ZARBXONA_PYTHON (
    set "TANLANGAN=%ZARBXONA_PYTHON%"
    goto ishga
)

if exist "%~dp0.venv\Scripts\python.exe" call :sina "%~dp0.venv\Scripts\python.exe"

for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "py -0p 2>$null | ForEach-Object { if ($_ -match '([A-Za-z]:\\.*?python\.exe)') { $matches[1] } }"`) do (
    call :sina "%%P"
)
for /f "delims=" %%P in ('where python 2^>nul') do call :sina "%%P"

if not defined TANLANGAN set "TANLANGAN=%ZAXIRA%"
if not defined TANLANGAN (
    echo Kerakli paketlar o'rnatilgan Python topilmadi.
    echo O'rnating:  py -m pip install -r requirements.txt
    pause
    exit /b 1
)

:ishga
"%TANLANGAN%" -c "import aetherq_core" >nul 2>&1 || echo eslatma: %TANLANGAN% da aetherq_core yo'q - onlayn topshirish o'chiq, fayl orqali ishlaydi
"%TANLANGAN%" run.py %*
exit /b %ERRORLEVEL%

:sina
"%~1" -c "import PySide6, cryptography, paho.mqtt; from cryptography.hazmat.primitives.asymmetric import mldsa" >nul 2>&1
if errorlevel 1 exit /b 0
if not defined ZAXIRA set "ZAXIRA=%~1"
if defined TANLANGAN exit /b 0
"%~1" -c "import aetherq_core" >nul 2>&1
if not errorlevel 1 set "TANLANGAN=%~1"
exit /b 0
