@echo off
rem Controlla i prerequisiti (Ghostscript, Java, veraPDF, cartella dati, percorsi, configurazione di Claude).
rem Opzione: Diagnosi.cmd --salva-configurazione  registra i percorsi degli strumenti trovati.
setlocal
set "BASE=%~dp0"
title Successioni - diagnosi
"%BASE%python\python.exe" -s "%BASE%app\diagnosi.py" %*
echo.
pause
endlocal
