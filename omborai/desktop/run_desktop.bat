@echo off
rem OmborAI desktop launcher: ikki marta bosing. Loyihaning o'z .venv ini ishlatadi.
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [OmborAI] .venv yaratilmoqda...
  where py >nul 2>nul
  if errorlevel 1 (
    echo [XATO] Python topilmadi. https://www.python.org/downloads/ dan Python 3.12 yoki 3.13 o'rnating.
    pause
    exit /b 2
  )
  py -3.13 -m venv .venv 2>nul || py -3.12 -m venv .venv
  if errorlevel 1 (
    echo [XATO] Python 3.12 yoki 3.13 topilmadi.
    pause
    exit /b 2
  )
)

call ".venv\Scripts\activate.bat"
python -c "import PySide6, paho.mqtt, keyring, cryptography, sqlcipher3" 2>nul
if errorlevel 1 (
  echo [OmborAI] Bog'liqliklar o'rnatilmoqda ^(sqlcipher3 uchun README: Windows'da manbadan yig'iladi^)...
  python -m pip install -q PySide6 keyring paho-mqtt cryptography
  python -m pip install -q -e .
  python -c "import sqlcipher3" 2>nul
  if errorlevel 1 (
    echo [XATO] sqlcipher3 o'rnatilmadi. desktop\README.md dagi "sqlcipher3 ni Windows'da yig'ish" bo'limiga qarang.
    pause
    exit /b 3
  )
)

python -m omborai_desktop
if errorlevel 1 (
  echo [XATO] Dastur xato bilan tugadi (kod %errorlevel%).
  pause
  exit /b 1
)
endlocal
