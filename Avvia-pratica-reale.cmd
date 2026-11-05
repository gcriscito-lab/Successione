@echo off
setlocal
title Successioni - ARCHIVIO PRATICHE REALI
rem Archivio dedicato alle pratiche reali, separato da quelli di prova (%LOCALAPPDATA%\Successioni e %USERPROFILE%\Successioni-prova).
rem Il server MCP per Claude deve usare lo STESSO archivio: SUCCESSIONI_DATA=%USERPROFILE%\Successioni-reale (vedi docs/GUIDA_PRIMA_PRATICA_REALE.md).
set "SUCCESSIONI_DATA=%USERPROFILE%\Successioni-reale"
if not exist "%SUCCESSIONI_DATA%" mkdir "%SUCCESSIONI_DATA%"
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Ambiente Python del progetto non trovato in .venv.
  pause
  exit /b 1
)
echo Archivio: %SUCCESSIONI_DATA%
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\windows\avvia_successioni.py" gui %*
if errorlevel 1 pause
endlocal
