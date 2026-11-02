# Lancia i compiti C1..C6 con FreeLLMAPI locale, uno alla volta (C1 e C6 toccano gli stessi file: mai in parallelo).
# La chiave si digita nel terminale (Read-Host) e vive solo in questa sessione PowerShell: non viene scritta da nessuna parte.
# Uso, dalla radice del repository:   .\scripts\agenti_gratuiti\lancia_tutti.ps1 [-Modello <nome>] [-Compiti C2,C3,C4,C5,C1,C6]
param(
    [string]$Modello = "",
    [string[]]$Compiti = @("C2", "C3", "C4", "C5", "C1", "C6")
)
$ErrorActionPreference = "Stop"
$py = ".\.venv\Scripts\python.exe"
$env:FREELLMAPI_BASE_URL = "http://127.0.0.1:31415/v1"
$chiave = Read-Host "Chiave FreeLLMAPI (rigenerata)" -AsSecureString
$env:FREELLMAPI_KEY = [System.Net.NetworkCredential]::new("", $chiave).Password

$elenco = @(& $py scripts\agenti_gratuiti\lancia.py --modelli | ForEach-Object { "$_".Trim() } | Where-Object { $_ })
Write-Host "Modelli disponibili:"; $elenco | ForEach-Object { Write-Host "  $_" }
if (-not $Modello) {
    # Scelta automatica: "auto" (il gateway sceglie il modello disponibile) se presente, altrimenti il primo dell'elenco.
    if ($elenco -contains "auto") { $Modello = "auto" } elseif ($elenco.Count -gt 0) { $Modello = $elenco[0] }
    else { $Modello = Read-Host "Nessun elenco ottenuto: nome del modello" }
}
Write-Host "Modello usato: $Modello"
$env:FREELLMAPI_MODEL = $Modello

foreach ($c in $Compiti) {
    Write-Host "=== $c ==="
    & $py scripts\agenti_gratuiti\lancia.py $c
}
Remove-Item Env:FREELLMAPI_KEY
Write-Host "Fatto. Risultati in build\agenti\<compito>-<data>\ (consegna.patch, CONSEGNA.md)."
