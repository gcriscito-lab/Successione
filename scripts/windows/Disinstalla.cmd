@echo off
rem Rimuove programma e collegamenti. NON cancella l'archivio delle pratiche (cartella dati).
rem Lo script viene copiato in %TEMP% perche' la cartella del programma sara' eliminata.
setlocal
set "BASE=%~dp0"
copy /y "%BASE%disinstalla.ps1" "%TEMP%\successioni-disinstalla.ps1" >nul
start "Successioni - disinstallazione" powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\successioni-disinstalla.ps1" -Programma "%BASE%."
exit /b 0
