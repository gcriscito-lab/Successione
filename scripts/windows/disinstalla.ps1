# Rimuove il programma Successioni e i suoi collegamenti. NON cancella la cartella dati (archivio e allegati)
# ne' i backup: il percorso viene mostrato alla fine. Avviato da Disinstalla.cmd da una copia in %TEMP%.
# Solo caratteri ASCII (Windows PowerShell 5.1).
param([Parameter(Mandatory = $true)][string]$Programma)
$ErrorActionPreference = 'Stop'
Start-Sleep -Seconds 1
$Programma = (Resolve-Path $Programma).Path.TrimEnd('\')
if (-not (Test-Path (Join-Path $Programma 'app\avvia_successioni.py'))) {
    Write-Host "Cartella non riconosciuta come installazione di Successioni: $Programma"
    Read-Host 'Premere Invio per chiudere' | Out-Null
    exit 1
}
$inUso = Get-Process -Name python, pythonw -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -and $_.Path.StartsWith($Programma, [System.StringComparison]::OrdinalIgnoreCase) }
if ($inUso) {
    Write-Host "Successioni e' in uso: chiudere la sua finestra e Claude Desktop, poi riprovare."
    Read-Host 'Premere Invio per chiudere' | Out-Null
    exit 2
}
$dati = $null
try {
    $info = & (Join-Path $Programma 'python\python.exe') -s (Join-Path $Programma 'app\avvia_successioni.py') info | Out-String
    $dati = ($info | ConvertFrom-Json).cartella_dati
} catch { }
$risposta = Read-Host "Rimuovere il programma da $Programma ? I dati NON vengono cancellati. (s/n)"
if ($risposta -ne 's') { exit 0 }
foreach ($c in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))) {
    foreach ($n in 'Successioni.lnk', 'Successioni - Diagnosi.lnk') {
        $p = Join-Path $c $n
        if (Test-Path $p) { Remove-Item -Force $p }
    }
}
Remove-Item -Recurse -Force $Programma
Write-Host 'Programma rimosso.'
if ($dati) { Write-Host "Archivio e allegati sono rimasti in: $dati" }
Write-Host "Eventuale voce 'successioni' in claude_desktop_config.json: rimuoverla da Claude Desktop (Impostazioni > Sviluppatore)."
Read-Host 'Premere Invio per chiudere' | Out-Null
exit 0
