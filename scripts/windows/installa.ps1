# Installa Successioni per l'utente corrente. Nessun diritto di amministratore, nessuna voce di registro.
# - copia il pacchetto in %LOCALAPPDATA%\Programs\Successioni (o -Destinazione);
# - se esiste gia' una versione: backup dell'archivio prima di sostituire il programma;
# - conserva configurazione.json; non tocca mai la cartella dati (%LOCALAPPDATA%\Successioni);
# - crea i collegamenti "Successioni" sul desktop e nel menu Start, poi esegue la diagnosi.
# Solo caratteri ASCII: Windows PowerShell 5.1 legge gli script senza BOM con la codifica locale.
param(
    [string]$Destinazione = (Join-Path $env:LOCALAPPDATA 'Programs\Successioni'),
    [switch]$SenzaCollegamenti
)
$ErrorActionPreference = 'Stop'
$Origine = $PSScriptRoot

function Fine([string]$messaggio, [int]$codice) {
    Write-Host $messaggio
    exit $codice
}

if (-not (Test-Path (Join-Path $Origine 'python\python.exe')) -or
    -not (Test-Path (Join-Path $Origine 'app\avvia_successioni.py'))) {
    Fine "Pacchetto incompleto: estrarre tutto lo zip in una cartella e rieseguire Installa.cmd." 1
}

$stessa = $false
if (Test-Path $Destinazione) {
    $stessa = ((Resolve-Path $Origine).Path.TrimEnd('\') -ieq (Resolve-Path $Destinazione).Path.TrimEnd('\'))
}

if (-not $stessa) {
    $pyVecchio = Join-Path $Destinazione 'python\python.exe'
    if (Test-Path $pyVecchio) {
        # Programma in uso (interfaccia aperta o server MCP avviato da Claude Desktop): i file sarebbero bloccati.
        $inUso = Get-Process -Name python, pythonw -ErrorAction SilentlyContinue |
            Where-Object { $_.Path -and $_.Path.StartsWith($Destinazione, [System.StringComparison]::OrdinalIgnoreCase) }
        if ($inUso) {
            Fine "Successioni e' in uso: chiudere la finestra di Successioni e chiudere completamente Claude Desktop, poi rieseguire Installa.cmd." 2
        }
        $info = & $pyVecchio -s (Join-Path $Destinazione 'app\avvia_successioni.py') info | Out-String
        $dati = ($info | ConvertFrom-Json).cartella_dati
        if ($dati -and (Test-Path (Join-Path $dati 'archivio.sqlite3'))) {
            $copia = Join-Path $env:LOCALAPPDATA ('Successioni-backup\prima-di-aggiornare-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
            Write-Host "Backup dell'archivio in $copia ..."
            & $pyVecchio -s (Join-Path $Destinazione 'app\avvia_successioni.py') backup $copia
            if ($LASTEXITCODE -ne 0) { Fine "Backup non riuscito: installazione interrotta, nulla e' stato modificato." 3 }
        }
    }
    New-Item -ItemType Directory -Force -Path $Destinazione | Out-Null
    $conf = Join-Path $Destinazione 'configurazione.json'
    $confSalvata = $null
    if (Test-Path $conf) { $confSalvata = Get-Content -Raw -Encoding UTF8 $conf }
    foreach ($d in 'python', 'app', 'docs') {
        $p = Join-Path $Destinazione $d
        if (Test-Path $p) { Remove-Item -Recurse -Force $p }
    }
    Write-Host "Copia del programma in $Destinazione ..."
    Get-ChildItem -Force $Origine | Copy-Item -Destination $Destinazione -Recurse -Force
    if ($null -ne $confSalvata) {
        [System.IO.File]::WriteAllText($conf, $confSalvata, (New-Object System.Text.UTF8Encoding($false)))
    }
}

# File scaricati da Internet: rimuove il contrassegno che farebbe comparire avvisi a ogni avvio.
Get-ChildItem -Recurse -File $Destinazione | Unblock-File

if (-not $SenzaCollegamenti) {
    $shell = New-Object -ComObject WScript.Shell
    $cartelle = @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))
    foreach ($c in $cartelle) {
        $lnk = $shell.CreateShortcut((Join-Path $c 'Successioni.lnk'))
        $lnk.TargetPath = Join-Path $Destinazione 'Successioni.cmd'
        $lnk.WorkingDirectory = $Destinazione
        $lnk.WindowStyle = 7
        $lnk.IconLocation = (Join-Path $Destinazione 'python\python.exe') + ',0'
        $lnk.Description = 'Successioni - interfaccia locale (127.0.0.1)'
        $lnk.Save()
    }
    $diag = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Programs')) 'Successioni - Diagnosi.lnk'))
    $diag.TargetPath = Join-Path $Destinazione 'Diagnosi.cmd'
    $diag.WorkingDirectory = $Destinazione
    $diag.Save()
    Write-Host "Collegamenti creati: desktop e menu Start (Successioni, Successioni - Diagnosi)."
}

Write-Host ''
Write-Host 'Diagnosi dei prerequisiti:'
& (Join-Path $Destinazione 'python\python.exe') -s (Join-Path $Destinazione 'app\diagnosi.py')
Write-Host ''
Write-Host "Installazione completata in $Destinazione. Avviare Successioni dal collegamento sul desktop."
exit 0
