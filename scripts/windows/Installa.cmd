@echo off
rem Installa Successioni per l'utente corrente: nessun diritto di amministratore richiesto.
setlocal
set "BASE=%~dp0"
title Successioni - installazione
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%BASE%installa.ps1" %*
echo.
pause
endlocal
