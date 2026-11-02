# Manuale breve

Stato: **beta tecnica**. Non è utilizzabile su una pratica reale e non trasmette nulla all'Agenzia delle Entrate.
Ogni comando qui sotto è stato verificato con `successioni --help`.

## Avvio
- `successioni gui` apre l'interfaccia nel browser, su un indirizzo locale con un codice (token) personale. Opzioni: `--porta`, `--no-browser`.
- `successioni mcp` avvia il collegamento per l'assistente Claude (vedi `docs/CONFIGURAZIONE_MCP.md`).

## Dove sono i dati
Nella cartella indicata dalla variabile `SUCCESSIONI_DATA`. Per provare il programma usa una cartella separata con **dati inventati**, mai dati reali dello studio.

## Lavorare nell'interfaccia
- Procedura guidata per una nuova pratica; i quadri (EA, EB, EC…) sono nella colonna a sinistra.
- Al centro la tabella dei dati, a destra l'ispettore con tre schede: *Dati*, *Controlli*, *Cronologia*.
- In basso la barra di stato: revisione, salvataggio, rilievi, stato del controllo ufficiale.
- Ogni modifica crea una nuova revisione. Se due persone (o l'assistente e tu) modificano la stessa pratica, la seconda modifica viene respinta con un conflitto e va riapplicata sulla revisione aggiornata.
- Le parole d'esito: **simulazione** (solo logica, dati inventati), **controllo locale** (componenti ufficiali eseguiti sul tuo PC), **verifica ufficiale** (servizi dell'Agenzia: non ancora disponibile).

## Allegati e PDF/A
- `successioni converti-pdfa` converte un PDF in PDF/A-1b e riporta l'esito. Serve Ghostscript.
- Senza veraPDF l'esito è sempre «non verificato», mai «conforme».
- Gli allegati oltre 5 MB si possono suddividere dalla scheda File.

## Backup e ripristino
- `successioni backup <cartella>` copia database e allegati.
- `successioni ripristina <backup> --destinazione <cartella nuova>` ripristina solo in una cartella nuova: non sovrascrive mai dati esistenti.

## Cosa il programma NON fa
- Non invia nulla e non usa credenziali.
- Quadri non coperti: EI, EL, EM, EN, EO, EP, EQ, agevolazioni e riduzioni, rinunce, legatari, testamento, rateazione. Selezionarli blocca la finalizzazione.
- La dichiarazione sostitutiva non è finalizzabile.
- Alcuni dati dell'esportazione (stato civile, codice carica, contatti, versamento) oggi si impostano solo da MCP o API.
- Nessun esito locale autorizza l'uso su una pratica reale.

Fonti: `docs/BETA_DA_REVISIONARE.md`, `docs/RISPOSTA_ALLA_REVISIONE.md`, `docs/COLLAUDO_WINDOWS_CODEX_20261102.md`.
