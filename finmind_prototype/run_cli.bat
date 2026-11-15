@echo off
rem FinTx terminal interfeysi (Windows). Hech narsa o'rnatish shart emas: faqat Python 3.10+.
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul && (py -3 -m fintx %*) || (python -m fintx %*)
