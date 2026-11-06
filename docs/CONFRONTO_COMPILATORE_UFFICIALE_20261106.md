# Confronto con il compilatore ufficiale, 6 novembre 2026

**Esito: imposte uguali sul caso provato.** Un solo caso sintetico. Non dimostra che il calcolo sia corretto per tutti i casi.

## Come è stato fatto

- **Compilatore usato:** SuccessioniOnLine ver. 2.3.1 del 11/03/2026, avviato da `fonti/Programma e controlli/SUC13 (4).jnlp` con Java Web Start (Java 8u511).
- **Inserimento dei dati:** il compilatore non importa i file XML (vedi `docs/MANUALE_BREVE.md`). Lo stesso caso è stato quindi inserito a mano nei due programmi.
- **Dati usati:** inventati, con i codici fiscali sintetici di `tests/telematico_casi.py`. Nessun IBAN inserito, nessun invio.
- **Archivio del compilatore:** la dichiarazione di prova è stata chiusa senza salvare. In `C:\AttiRegistro` non è stato scritto niente; è stato verificato che la cartella del codice fiscale di prova non esiste.

## Caso

- **Defunto:** Rossi Mario, nato il 01/01/1940, celibe (stato civile 1), deceduto il 10/03/2025 a Roma.
- **Eredi per legge:** Rossi Anna e Rossi Luca, fratelli germani (grado 10).
- **Bene:** un fabbricato a Roma (H501), foglio 100, particella 200, sub. 3, categoria A/2, rendita 1.000,00. Proprietà 1/1, valore 300.000. Va 1/2 a ciascun erede (150.000 ciascuno).
- **Altro:** nessuna passività e nessun altro bene.

## Risultati

| Voce | Compilatore ufficiale | Nostro programma |
|---|---|---|
| Imposta ipotecaria (EF1, EF5, EF8) | 6.000 | 6.000 |
| Imposta catastale (EF9, EF11, EF14) | 3.000 | 3.000 |
| Tassa ipotecaria (EF15) | 120 | 120 |
| Imposta di bollo | 85 (ricavato: EF19 meno le altre voci) | 85 |
| Imposta di successione (EF18-bis) | 6.600 | 6.600 (3.300 per erede) |
| Totale EF19 / importo da versare | 9.205,00 | 9.205,00 |

Il caso è fissato in `tests/test_confronto_compilatore_ufficiale.py`.

## Differenza di comportamento (non di importo)

Alla data del confronto la dichiarazione risulta tardiva: sono passati più di dodici mesi dal decesso.

- **Compilatore ufficiale:** calcola comunque il quadro EF e lascia vuote le sanzioni.
- **Nostro programma:** non genera il quadro EF finché non si indicano le sanzioni.

Per gli importi il confronto è stato rifatto con data di riferimento 15/01/2026, entro i termini.

## Seconda prova: una dichiarazione reale già presentata

Senza dati personali in questo documento.

- **File di partenza:** il file telematico di una dichiarazione reale dello studio, prodotto dal compilatore ufficiale e già inviato (decesso 2026, erede unico, un terreno, due fabbricati, disponibilità finanziarie, attestazione richiesta).
- **Controllo ufficiale sul file originale:** positivo, senza segnalazioni (eseguito in locale).
- **Importazione e rigenerazione:** il file è stato importato nel nostro programma, nell'archivio reale (pratica «Ricopia da compilatore ufficiale»), e rigenerato.
- **Risultato:** 0 differenze sui 21 valori dei quadri EE ed EF e sull'importo da versare del frontespizio.
- **Non rigenerati:** gli allegati del quadro EG non vengono importati e vanno riacquisiti.

Lacune emerse e corrette, con test in `tests/test_attestazione.py` e `tests/test_pratiche_reali_20261106.py`:

1. **Attestazione di avvenuta presentazione (copia conforme):** mancava. La chiedono 9 dichiarazioni reali su 10.
   - Casella `richiesta_attestazione` nel frontespizio (CasiParticolari/CopiaConforme).
   - EF16: colonna 1 a 32 euro, colonna 3 a 85 per circoscrizione più 32.
   - EF18: 16 euro.
   - Fonte: Fascicolo I pp. PDF 16, 45-46.
   - Controllo ufficiale locale: positivo senza segnalazioni. Togliendo i 32 euro il file viene respinto.
2. **Fabbricato senza indirizzo:** era bloccato per l'annotazione XSD. Il controllo ufficiale accetta il file reale, quindi ora è un avviso.
3. **Importazione:** ora vengono letti anche email e decorrenza del presentatore, immobili graffati e identificativo del software produttore.

Lacune di importazione ancora aperte sulle altre dichiarazioni reali: sostitutive, quadro EO (decimali e ordine dei righi), agevolazioni nella devoluzione EC, diritto di abitazione. Riguardano solo l'importazione: la compilazione manuale non è toccata.

## Limiti

- **Un solo caso:** fratelli e un immobile. Restano non confrontati coniuge e figli, passività, agevolazione prima casa, più moduli, riduzioni e sostitutiva.
- **Prospetto del compilatore:** non letto, perché il compilatore chiede l'IBAN prima di aprirlo e l'IBAN non è stato inserito.
- **Controllo ufficiale del file:** questo confronto non lo sostituisce.
