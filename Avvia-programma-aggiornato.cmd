@echo off
setlocal
title Successioni - versione sorgente aggiornata
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Ambiente Python del progetto non trovato in .venv.
  echo Questa scorciatoia usa i sorgenti, non e' il pacchetto autonomo Windows.
  pause
  exit /b 1
)
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\windows\avvia_successioni.py" gui %*
if errorlevel 1 pause
endlocal
