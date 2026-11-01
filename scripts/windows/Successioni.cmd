@echo off
rem Avvia l'interfaccia di Successioni (solo su questo PC, indirizzo 127.0.0.1) e apre il browser.
rem Chiudere questa finestra termina il programma: i dati sono salvati a ogni modifica.
setlocal
set "BASE=%~dp0"
title Successioni - lasciare aperta questa finestra durante il lavoro
"%BASE%python\python.exe" -s "%BASE%app\avvia_successioni.py" gui %*
if errorlevel 1 (
  echo.
  echo Avvio non riuscito. Eseguire Diagnosi.cmd e conservare il rapporto mostrato.
  pause
)
endlocal
