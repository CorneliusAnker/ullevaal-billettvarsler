@echo off
REM Starter Frogner-varsleren (Norge vs England). Dobbeltklikk for a kjore.
REM Vinduet ma sta apent sa lenge du vil overvake. Lukk/Ctrl+C for a stoppe.

cd /d "%~dp0"

title Frogner-varsler (Norge vs England)

python fanpark_monitor.py

echo.
echo === Overvakingen er stoppet. Trykk en tast for a lukke vinduet. ===
pause >nul
