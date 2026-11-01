@echo off
rem Verifica una copia di backup (o la cartella dati) in sola lettura.
rem Uso: trascinare la cartella del backup su questo file, oppure: Verifica-backup.cmd "D:\Backup\Successioni-2026-11-01"
setlocal
set "BASE=%~dp0"
title Successioni - verifica backup
if "%~1"=="" (
  echo Trascinare su questo file la cartella del backup da verificare.
  pause
  exit /b 1
)
"%BASE%python\python.exe" -s "%BASE%app\verifica_backup.py" %*
echo.
pause
endlocal
