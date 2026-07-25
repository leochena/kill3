@echo off
cd /d "%~dp0\.."
python runtime\smoke_e2e.py %*
