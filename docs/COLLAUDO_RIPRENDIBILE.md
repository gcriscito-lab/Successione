# Collaudo riprendibile dei collegamenti sul PC Windows del professionista

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
(export dell'app quando EF/EG/EH saranno coperti) oppure il file di una pratica effettiva autorizzata — il controllo
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
inventato. Per il controllo: interrompere `collaudo controllo` durante l'esecuzione; il job resta `in_esecuzione`
(diagnosi visibile), un nuovo controllo con un'altra chiave non altera il precedente.

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
