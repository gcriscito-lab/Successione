# Lavorare in locale sul PC Windows

Guida per continuare lo sviluppo sul proprio computer. La fonte condivisa del lavoro è il branch `claude/successioni-dichiarazioni-app-fhcwbe` su GitHub.

## Primo avvio
```powershell
git clone <indirizzo del repository> Successione        # oppure: git clone Successione.bundle Successione
cd Successione
git checkout claude/successioni-dichiarazioni-app-fhcwbe
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[test]"
python -m pytest -q
```
Atteso: tutti i test passano; quelli che richiedono componenti esterni (controllo ufficiale SUC13 con Java 8, veraPDF, pacchetto Windows costruito) risultano saltati finché non imposti le variabili descritte in `docs/BETA_DA_REVISIONARE.md` e `docs/COLLAUDO_WINDOWS_CODEX_20261102.md`.

Per avviare il programma: `$env:SUCCESSIONI_DATA = "$env:USERPROFILE\Successioni-prova"; python -m successioni.cli gui`.

## Regole di sicurezza (valgono sempre)
1. **Dati**: per lo sviluppo usa solo dati sintetici e una cartella dati separata (`SUCCESSIONI_DATA`). Mai dati reali dello studio nel repository.
2. **Credenziali**: Entratel, certificati e chiavi non vanno mai in chat, nel codice, nei log o nel repository. Si configurano solo sul PC, nelle impostazioni protette.
3. **Permessi**: tieni attive le richieste di conferma di Claude Code, in particolare per Git, rete e cancellazioni. Niente modalità automatiche nelle cartelle con dati dello studio.
4. **Invii**: nessun invio reale durante lo sviluppo. Il primo invio operativo richiede una pratica effettiva verificata e l'autorizzazione specifica del professionista.
5. **Una sola fonte**: prima di lavorare `git pull`; a fine lavoro `git push` sul branch. Non usare `--force`. Le patch di altri strumenti si integrano con `git am` su ramo temporaneo e con i test verdi.

## Dove ripartire
- Stato e prossimi passi: `docs/STATO_LAVORI.md`, `docs/BETA_DA_REVISIONARE.md`, `docs/RISPOSTA_ALLA_REVISIONE.md`.
- Istruzioni al programmatore: `CLAUDE.md`. Specifica e collaudo: `docs/02_SPECIFICA_E_COLLAUDO.md`.
- Compiti piccoli per agenti gratuiti con il lanciatore: `docs/COMPITI_PER_AGENTI_GRATUITI.md`.
- Prove da fare sul PC: `docs/COLLAUDO_RIPRENDIBILE.md`, `docs/PDFA.md` (veraPDF), configurazione del client MCP (`Configura-MCP.cmd` nel pacchetto).

## Cosa resta da collaudare
Client Claude effettivo con l'MCP, Entratel e catasto reale, invio e ricevute, SmartScreen e antivirus, disinstallazione, WSL. Nessun esito locale autorizza l'uso su una pratica reale.
