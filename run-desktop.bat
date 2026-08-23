@echo off
REM DistribOS AI - desktop dasturini ishga tushirish
cd /d "%~dp0"
python run.py %*
if errorlevel 1 pause
