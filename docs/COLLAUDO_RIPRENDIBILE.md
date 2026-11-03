# Collaudo riprendibile dei collegamenti sul PC Windows del professionista

Aggiornamento 2026-11-02: controllo ufficiale locale Windows positivo e due negativi predisposti verificati;
rapporto `docs/COLLAUDO_WINDOWS_CODEX_20261102.md`. Entratel e invii/ricevute reali restano da collaudare.

Procedure per A10, A13, A14, A15, A18, A19 (`docs/02_SPECIFICA_E_COLLAUDO.md` §12). Ogni passo scrive nello stesso
archivio dell'app (cartella `SUCCESSIONI_DATA`, predefinita `%LOCALAPPDATA%\Successioni`) e stampa un JSON con
`esito` (passato | fallito | da_collaudare | simulazione) e `job_id`. Se una prova si interrompe, si riprende dal
`job_id` (`collaudo stato --job ID`): lo stato non dipende dal processo che l'ha avviata.

Regole: nessuna dichiarazione sintetica va trasmessa; la trasmissione riguarda solo una pratica effettiva verificata e
autorizzata dal professionista. Credenziali, PIN e certificati restano negli strumenti ufficiali: non si scrivono in
questo programma, nei comandi, nei log o in questo documento. Registrare ogni esito nella tabella in fondo.

## 0. Prerequisiti comuni

1. Programma installato (o ambiente di sviluppo con `pip install -e .`) e prompt PowerShell nella sua cartella.
2. Comando base (sotto abbreviato `collaudo`):
   `python -m successioni.collegamenti.collaudo [--archivio C:\Percorso\Archivio] <comando>`
3. Annotare: versione di Windows, versione di Java (`java -version`), versione di Desktop Telematico ed
   Entratel-Multifile installate.

## A10 — Controllo ufficiale richiamato dall'app

**Prerequisiti.** Java installato (quello usato da Desktop Telematico o un JRE 8+; il JNLP dichiara 1.7+). JAR del
controllo SUC13 in una cartella: `collaudo scarica-jar --dest C:\Successioni\controlli-suc13` (scarica i 15 JAR del
JNLP ufficiale e confronta le impronte con quelle del 2026-11-01; un'impronta diversa indica un aggiornamento da
annotare). In alternativa individuare la cartella dei JAR installata da Desktop Telematico (da verificare).

**Comandi.**
```
$env:SUCCESSIONI_JAVA = "C:\...\bin\java.exe"
$env:SUCCESSIONI_CONTROLLI_SUC13 = "C:\Successioni\controlli-suc13"
collaudo ambiente                                   # atteso: "pronto": true, 15 JAR, nessun problema
collaudo controllo --xml src\successioni\collegamenti\fixture\controllo_reale_20261101\frontespizio.xml
collaudo controllo --xml <FILE_POSITIVO> --dcm
collaudo controllo --xml <FILE_CON_ERRORE_PREDISPOSTO>
```

**Dati di prova.** (a) Negativo noto: `frontespizio.xml` (sintetico). (b) Positivo: un XML completo, sintetico
(export dell'app nel perimetro EF/EG/EH oggi coperto) oppure il file di una pratica effettiva autorizzata — il controllo
e' locale, nulla viene inviato. (c) Errore predisposto: copia di (b) con il carattere di controllo del codice
fiscale del defunto alterato.

**Esito atteso.** (a) `esito: fallito`, `stato_controllo: negativo`, riepilogo 1 elaborata / 1 scartata, 7 (***)
e 1 (*) come in `fixture/controllo_reale_20261101/frontespizio.wri`. (b) `esito: passato`, `positivo`, artefatto
`file_controllato_dcm` presente. (c) `fallito` con "(***) ... Codice Fiscale errato". Controprova: controllare gli
stessi file con Desktop Telematico (Controlli atti del registro > SUC) e confrontare riepilogo e righe `1...` dei
`.dgn` (escluse le intestazioni con il percorso). Annotare le avvertenze d'ambiente stampate.

**Se l'esecuzione diretta non e' possibile:** `collaudo controllo` crea comunque il job in `attesa_diagnostico`
(passaggio manuale tracciato). Controllare il file con Desktop Telematico, poi:
`collaudo registra-diagnostico --job ID --dgn F.dgn --log F_logSchema.xml --wri F.wri --ambiente-dichiarato
'{"os":"Windows 11","desktop_telematico":"x.y"}'`. Il requisito di automazione resta aperto.

## A13 — Acquisizione delle risultanze catastali via Entratel

**Prerequisiti.** Accesso Entratel del professionista abilitato al servizio; una pratica effettiva autorizzata
(codice fiscale del defunto); pratica creata nell'app.

**Comandi e passi.**
1. `collaudo catasto-avvia --pratica <ID_PRATICA> --cf <CF_DEFUNTO>` -> `esito: da_collaudare`, stato
   `attesa_utente`, istruzioni nel campo `azione_richiesta`.
2. In Entratel eseguire la ricerca delle risultanze per quel soggetto; annotare percorso del menu, filtri (catasto,
   territorio), paginazione, eventuali avvisi di incompletezza, presenza di graffati e porzioni.
3. Salvare i risultati nel formato offerto, senza modificarli, e registrarli:
   `collaudo catasto-registra --job <JOB> --file <FILE> --formato <pdf|xml|csv|...>` -> file conservato con
   impronta (artefatto `risultanze_originali`).
4. Consegnare allo sviluppo un esempio (anche oscurato nei dati personali) per scrivere il convertitore nel formato
   interno `successioni.catasto.v1`, e l'indicazione se esiste un'interfaccia documentata.

**Esito atteso oggi.** `da_collaudare` con originale conservato. A13 sara' `passato` solo con acquisizione effettiva
dall'app (o convertitore provato sul file reale), ambito e provenienza registrati e controllo di completezza.

## A14 — Importazione ripetuta

**Oggi (simulazione):** `python -m pytest -q tests/test_collegamenti_catasto.py` -> verde; il test
`test_a14_importazione_selettiva_ripetuta_senza_doppioni` prova zero operazioni alla seconda importazione, una sola
modifica sulla rendita aggiornata, campi ignoti conservati, dati manuali non sovrascritti.

**Sul PC (dopo il convertitore):** registrare due volte lo stesso file reale nella stessa pratica e una estrazione
successiva; attesi: nessun bene duplicato, solo i campi cambiati proposti, conflitti elencati per i dati inseriti a
mano, campi sconosciuti segnalati.

## A15 — Ripresa dopo chiusura del client o sessione scaduta

Durante A13 (stato `attesa_utente` o `sessione_scaduta`) chiudere l'app e il client MCP; riaprire e lanciare
`collaudo stato --job <JOB>`: atteso lo stesso stato, le pagine e gli originali gia' acquisiti, nessun risultato
inventato. Per il controllo locale, `ControlloJar.riprendi(job_id)` rileva il processo interrotto con il lock,
recupera i byte congelati e ripete il controllo nello stesso job con una nuova cartella di lavoro. Un controllo
ancora attivo non viene duplicato. `collaudo stato` e' sola lettura; la ripresa e' nell'API dell'adattatore.
Il componente puo' consumare la copia di lavoro quando produce DCM: l'originale nel deposito resta invariato.

## A18 — Invio con esito incerto

**Oggi (simulazione):** `python -m pytest -q tests/test_collegamenti_invio.py -k a18` -> verde: rete interrotta dopo
la ricezione (riconciliazione trova il protocollo, una sola chiamata d'invio), richiesta mai arrivata (nuovo
tentativo solo esplicito dopo prova di mancato invio), processo interrotto durante la chiamata (riconciliazione con
file `.esi`).

**Collaudo reale (solo con pratica effettiva e autorizzazione specifica):**
1. Prerequisito d'integrazione: preparazione e conferma della copia nell'interfaccia (coordinatore); la conferma da
   MCP e' rifiutata per progetto.
2. Preparare e confermare la copia; avviare la trasmissione: stato `attesa_invio_manuale` (il programma non invia).
3. Inviare con Desktop Telematico o Entratel-Multifile il file indicato (stessa impronta).
4. Simulare l'incertezza chiudendo l'app prima di registrare l'esito; riaprire: il tentativo e' ancora in attesa e un
   nuovo invio dalla stessa copia e' rifiutato (`REINVIO_NON_AMMESSO`).
5. Riconciliare: `collaudo riconcilia --tentativo <ID> --esi <file_esiti\esito_....esi>` oppure
   `--protocollo <N> --verificato-su "Ricerca ricevute, data"`.
**Atteso:** stato `trasmesso` con protocollo, un solo invio presso l'Agenzia (verificare in Ricerca ricevute),
`esito: da_collaudare` finche' l'invio non e' eseguito dall'app con un trasporto automatico.

## A19 — Ricevute ed esiti separati

**Oggi (simulazione):** `python -m pytest -q tests/test_collegamenti_invio.py -k a19`.

**Sul PC (dopo una trasmissione reale autorizzata):** scaricare ogni documento (Ricerca ricevute; Ricevute e altre
comunicazioni - Ricerca documenti; oppure Multifile R03/R04 e "Apri ricevute") e registrarlo indicando il tipo letto
nel documento: `collaudo ricevuta --protocollo <N> --tipo trasmissione|registrazione|pagamento|copia_semplice|
richiesta_regolarizzazione|attestazione|volture|da_classificare [--esito ...] --file <FILE>`.
**Atteso:** ogni documento associato al protocollo e alla pratica, originale conservato con impronta; registrazione,
pagamento e volture in dimensioni separate (un pagamento negativo non cancella la registrazione; volture parziali
conservate con l'elenco degli immobili); documenti attesi riconoscibili (`stato_esiti`). Annotare formati e canali
reali di ciascuna ricevuta SUC13.

## Cosa serve dal committente

- PC Windows con Java, Desktop Telematico e (se usato) Entratel-Multifile aggiornati; indicazione della cartella dei
  JAR del controllo installati, se si vogliono usare quelli.
- Un file XML di una pratica effettiva (o il consenso a usare l'export sintetico quando completo) per il caso
  positivo A10; il controllo resta locale.
- Una sessione assistita su Entratel per A13: percorso del servizio, formato e un esempio dei risultati.
- Per A18/A19: una pratica effettiva verificata e l'autorizzazione specifica all'invio; ricevute scaricate.

## Registro degli esiti

| Data | Prova | PC / Java / strumenti | Input (SHA-256) | job_id | Esito | Note |
|---|---|---|---|---|---|---|
| 2026-11-01 | A10 negativo (frontespizio) | container Linux, OpenJDK 21.0.12.1, controllo 2.3.1 | 02d93434bb40... | (archivio di sviluppo) | fallito (negativo atteso) | eseguito dall'adattatore; non e' la prova su Windows |
| 2026-11-01 | A10 schema non valido (minimo) | come sopra | vedi manifest | (archivio di sviluppo) | fallito (negativo atteso) | record (****) |
| | A10 positivo | | | | da_collaudare | |
| | A13 | | | | da_collaudare | |
| | A14 reale | | | | da_collaudare | |
| | A18 reale | | | | da_collaudare | |
| | A19 reale | | | | da_collaudare | |


## Aggiornamento 2026-11-03: PDF/A su questo PC
Installati: Ghostscript 10.08.0 (`gs10080w64.exe`, 65.093.120 byte, firma Authenticode valida, Artifex Software) in `C:\gs\gs10.08.0`; veraPDF 1.30.3
(`verapdf-installer.zip`, 32.971.125 byte, firma GPG `13DD 102B 4DD6 9354 D12D E5A8 3184 8632 78B1 7FE7` verificata) in `C:eraPDF`, componente CLI.
Variabili utente: `SUCCESSIONI_GS`, `SUCCESSIONI_VERAPDF`, `SUCCESSIONI_ICC` (profilo `default_rgb.icc` di Ghostscript). Con queste i test PDF/A (`test_pdfa.py`,
`test_documenti_*`, collaudo A11 con veraPDF) passano: 42 test, nessun saltato. Avvertenza: non anteporre Java 8 al `PATH` (un test lancia un file `.java`, che richiede
Java 11 o successivo); `SUCCESSIONI_JAVA` indica Java 8 per il solo controllo SUC13. Non e' la verifica ufficiale CIVIS.

## Aggiornamento 2026-11-03: pacchetto Windows costruito e avviato (A01 in parte)
Costruito con `python packaging/costruisci_pacchetto.py` da Windows: Python 3.13.17 embeddable (11.441.267 byte, SHA-256 fissato) e 34 wheel da PyPI (29.471.249 byte,
SHA-256 del lock), cartella da 111 MB e zip da 51 MB (`Successioni-0.1.0-win64`). `--verifica`: nessun problema.
Provato **senza installare** (nessun collegamento creato): con il Python incorporato si importano tutti i moduli attesi (mcp, lxml, pypdf, reportlab, PIL, starlette, uvicorn,
pydantic, win32api, successioni); `app\diagnosi.py` riconosce Ghostscript 10.08.0, veraPDF 1.30.3, Java 8 e i 15 JAR SUC13; `avvia_successioni.py gui` serve
l'interfaccia su 127.0.0.1:8765 (HTTP 200, `pdfa.ghostscript` e `pdfa.veraPDF` veri); `avvia_successioni.py mcp` risponde all'handshake con 20 strumenti `successioni_*`,
nessuno di conferma o trasmissione. `tests/test_installazione.py` con `SUCCESSIONI_PACCHETTO_WIN`: 18 passati.
Corretto: il pacchetto cercava Ghostscript solo in `Program Files`; ora anche `C:\gs\gs*\bin` (installazione silenziosa con `/D=`).
**Ancora da collaudare**: `Installa.cmd` (copia in `%LOCALAPPDATA%\Programs\Successioni` e crea collegamenti sul desktop e nel menu Start), SmartScreen e antivirus su un altro PC,
`Disinstalla.cmd`, `Configura-MCP.cmd --scrivi-claude-desktop` con Claude Desktop, avvio da un percorso con spazi e accenti dopo l'installazione.

## Aggiornamento 2026-11-03 (sera): installazione e aggiornamento su questo PC
`installa.ps1` eseguito: programma in `%LOCALAPPDATA%\Programs\Successioni`, collegamenti `Successioni.lnk` (desktop e menu Start) e `Successioni - Diagnosi.lnk`
(menu Start); nessuna voce di registro. Reinstallazione sopra la precedente: **backup automatico dell'archivio** in `%LOCALAPPDATA%\Successioni-backup\prima-di-aggiornare-*`,
programma sostituito, cartella dati `%LOCALAPPDATA%\Successioni` intatta. Dal programma installato: interfaccia su 127.0.0.1:8765 (HTTP 200), Ghostscript e veraPDF veri,
accesso senza token respinto (401), chiusura pulita. Il profilo sRGB di Ghostscript (`srgb.icc`) ora si trova da solo anche in `C:\gs`: tolta la variabile `SUCCESSIONI_ICC`.
Non eseguibile in modo non interattivo e quindi **da provare a mano**: `Disinstalla.cmd` (chiede conferma con `Read-Host`). Resta da collaudare anche SmartScreen/antivirus su un altro PC.
