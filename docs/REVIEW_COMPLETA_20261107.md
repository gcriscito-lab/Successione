# Review completa del programma — 7/11/2026

Cinque revisori indipendenti, in sola lettura, ognuno su un'area: calcolo ed export, importazione, interfaccia web, archivio/allegati/MCP, collegamenti/test/documentazione. Prove su archivi temporanei e dati sintetici; i file inviati in `C:\AttiRegistro\arc` sono stati solo copiati e letti. Il controllo ufficiale citato è il componente SUC13 2.3.1 eseguito in locale. Nessun file del progetto è stato modificato dalla review.

Legenda: **C** = confermato (riprodotto, o verificato su fonte/controllo ufficiale); **P** = probabile (da lettura del codice).
I punti segnati ✔ sono stati ricontrollati di persona sul codice.

## Priorità 1 — possono produrre una dichiarazione sbagliata o perdere dati

| # | Area | Problema | Dove | |
|---|------|----------|------|---|
| 1 | Interfaccia | «150.000» (un solo punto, senza virgola) viene salvato come 150,000 €: valore 1000 volte più basso, senza avvisi | `static/app.js:116-120` | C ✔ |
| 2 | Calcolo EF | Bollo EF16: conta anche le circoscrizioni dei beni con agevolazione C, E, M, G (vanno escluse). Controllo ufficiale: errore 3078 | `quadri_efgh.py:213` | C ✔ |
| 3 | Calcolo EF | Immobili devoluti ai gradi 37-39 tolti da EF15/EF16 (EF15 esclude solo 36; EF16 solo 36-37). Controllo ufficiale: 3078 | `quadri_efgh.py:119-122` | C ✔ |
| 4 | Calcolo EF | Agevolazioni G/M: fissa sempre 200 €, anche per decessi 3/10/2006-31/12/2013 (168 €). Controllo ufficiale: 3076 | `quadri_efgh.py:239-240` | C ✔ |
| 5 | Importazione | Sanzioni e interessi del ravvedimento (EF Sez. VI), tempistica, rateazione, acconto, crediti persi in silenzio: 4 dei 10 file inviati li hanno (la pratica SNNDNC tenuta non è toccata) | `importa.py:34, 715-717` | C ✔ |
| 6 | Allegati | «Rimuovi doppioni» cancella l'originale anche se firmato o se il PDF/A non è conforme | `allegati.py:133-146` | C ✔ |
| 7 | Allegati | Una seconda conversione dello stesso file cancella l'originale anche con PDF/A non conforme | `allegati.py:168-176` | C ✔ |
| 8 | Allegati | Eliminare un allegato può cancellare una ricevuta/copia d'invio con lo stesso contenuto e far fallire ogni backup | `allegati.py:108-115` | C |
| 9 | Catasto | Confronto beni per nome comune (ROMA) contro codice (H501): propone un doppione con il codice nel nome | `catasto.py:146-153, 234` | C ✔ |
| 10 | Export | Il file risulta «completo» anche con PDF non PDF/A o TIFF fuori specifica in EG | `quadri_efgh.py:639-660`, `esporta.py:2336` | C |

## Priorità 2 — blocchi, doppioni, comportamenti scorretti

- **Calcolo**
  - Credito che copre tutta l'imposta di successione: l'export diventa impossibile («0» fuori formato e tempistica pretesa). `quadri_efgh.py:495, 533-543`. **C**
  - Sostitutiva codice 1: il minimo di 200 € dell'ipotecaria è applicato anche con EF2/EF3. `quadri_efgh.py:278-279`. **P**
  - Credito d'imposta senza importo d'acquisto: il programma lo inventa pari al credito usato. `pagamenti.py:77`. **P**
  - Tardiva entro 90 giorni con tempistica 2 bloccata finché non si indicano sanzioni = 0. `quadri_efgh.py:518-526`. **P**
  - Detrazione dell'imposta estera applicata anche alle quote esenti. Il controllo ufficiale la accetta: è una regola da chiarire. `calcolo.py:456-458`
- **Importazione**
  - Le sostitutive non si importano: sono 4 dei 7 file provati.
  - Quote decimali rifiutate (ammesse dall'XSD).
  - Ordine EO troppo rigido.
  - Agevolazioni nelle devoluzioni non lette.
  - Limite di 20 MB su file pieni di allegati EG che comunque non si importano.
- **Interfaccia**
  - Doppio clic su «Crea dichiarazione» crea due pratiche. **C**
  - «Genera file», «controllo», «Prepara invio» e «Invia in prova» non bloccano il secondo clic (`S.writeBusy` mai impostato). **C/P**
  - Due interfacce aperte (prova e reale) si scollegano a vicenda: lo stesso cookie vale per tutte le porte. **C**
  - Server chiuso: le azioni falliscono senza messaggio, oppure con «Failed to fetch», e resta visibile un vecchio «Salvato». **C**
  - Errori di generazione mostrati con percorsi interni come `beni[b_…].comune`. **C**
- **Invio e controllo**
  - «Invia in PROVA» consuma la copia reale confermata: dopo bisogna prepararne un'altra. **C**
  - Un `_logSchema.xml` troncato lascia il controllo «in esecuzione» per sempre e la cartella di lavoro non viene ripulita. **C**
  - Il `.dgn` e l'`.esi` sono abbinati al file solo per nome. Con i nomi usati dal programma, un esito manuale non combacia mai; un esito vecchio con lo stesso nome viene invece accettato. **P**
  - Il passaggio manuale del controllo si chiude solo da riga di comando. **C**
- **MCP e archivio**
  - Se `configurazione.json` è illeggibile, la «sola lettura» di Claude si disattiva da sola. **C**
  - `prepara_pdfa` è dichiarato non distruttivo ma cancella l'originale. **C**
  - Import e acquisizione senza chiave di idempotenza: una ripetizione crea doppioni. **P**
  - Scrittura non atomica del file dell'allegato. **C**
  - Gara alla creazione dell'archivio. **C**
  - Il ripristino è rifiutato se esiste già la cartella `ingresso`. **C**
  - Il backup non include `configurazione.json`. **C**

## Priorità 3 — pulizia, test, documentazione

- **Sicurezza locale e accessibilità**
  - Il token resta valido nell'indirizzo (cronologia, preferiti).
  - Upload senza limite di dimensione.
  - Nome file vuoto → errore 500.
  - Flussi NTFS alternativi accettati.
  - I lettori di schermo leggono i nomi interni dei campi (`aria-label`).
- **Test che passano per il motivo sbagliato**
  - La pulizia della cartella di controllo (`test_collegamenti_controllo.py:140`).
  - Il catasto (`test_collegamenti_catasto.py:79`).
  - L'`.esi` con nomi coincidenti per costruzione.
  - Il controllo positivo reale non passa dall'adattatore usato dall'app.
- **Documentazione superata**
  - `COLLEGAMENTI.md` e `COLLAUDO_RIPRENDIBILE.md` danno A10 positivo «da collaudare», ma il collaudo è stato fatto il 1/11.
  - `MATRICE_COPERTURA.md` riga 93: «estero non coperto».
  - Docstring di `calcolo.py` e `quadri_efgh.py`.
  - Testo della procedura guidata sulla sostitutiva (`app.js:1394`).
- **Codice morto e duplicati**
  - `calcolo.py:210-213`.
  - Ramo EF2/G mai raggiunto.
  - `IMPOSTA_FISSA` duplicata.
  - Elenchi delle agevolazioni esclusive diversi (Z).

## Cosa regge

- **Imposte nei casi comuni.** Aliquote, franchigie, presunzione, riduzioni L/Q/R/F e art. 25, quote di legge e rateazione corrispondono alle fonti. Il caso sintetico coincide con il compilatore ufficiale e la pratica reale reimportata con il file inviato.
- **Sicurezza locale.**
  - Il server ascolta solo su 127.0.0.1.
  - Host e Origin estranei sono rifiutati, il token è obbligatorio e il cookie è HttpOnly e SameSite=strict.
  - Nessun `innerHTML`: niente XSS.
  - Path traversal bloccato su statici, cartella d'ingresso e import.
  - XML con DOCTYPE/XXE rifiutati.
- **Revisioni.** Il conflitto di revisione fra GUI e MCP è gestito bene: le modifiche si uniscono senza perdite.
- **Processo Java.** Nessuna shell, timeout e codifiche gestiti, segreti filtrati. Una simulazione non diventa mai «passato».
