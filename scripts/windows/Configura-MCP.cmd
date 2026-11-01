@echo off
rem Mostra la configurazione MCP per Claude Desktop e Claude Code (non modifica nulla).
rem Opzione: Configura-MCP.cmd --scrivi-claude-desktop  aggiorna claude_desktop_config.json con copia di sicurezza.
setlocal
set "BASE=%~dp0"
title Successioni - configurazione MCP
"%BASE%python\python.exe" -s "%BASE%app\configura_mcp.py" %*
echo.
pause
endlocal
