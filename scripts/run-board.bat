@echo off
setlocal
cd /d "%~dp0\.."
set FM_HOST=0.0.0.0
set FM_PORT=8787
if not "%~1"=="" set FM_PORT=%~1
echo Starting free-match board on http://127.0.0.1:%FM_PORT%
echo UI:  http://127.0.0.1:%FM_PORT%/
echo API: http://127.0.0.1:%FM_PORT%/api/v1/meta
python runtime\server.py --host %FM_HOST% --port %FM_PORT%
endlocal
