@echo off
REM Starter billettvarsleren. Dobbeltklikk denne fila for a kjore.
REM Vinduet ma sta apent sa lenge du vil overvake. Lukk/Ctrl+C for a stoppe.

REM Bytt til mappa der denne fila ligger (fungerer uansett hvor du starter fra).
cd /d "%~dp0"

title Fotballfesten billettvarsler

python monitor.py

REM Hvis scriptet stopper (feil eller Ctrl+C), hold vinduet apent sa du ser hvorfor.
echo.
echo === Overvakingen er stoppet. Trykk en tast for a lukke vinduet. ===
pause >nul
