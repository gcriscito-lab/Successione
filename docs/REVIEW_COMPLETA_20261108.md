# Review completa — 8/11/2026

Cinque revisori indipendenti, in sola lettura, sul commit 15ea830 (versione 0.4 con il design system).

- **Aree:** calcolo ed esportazione; archivio, server e MCP; interfaccia; funzioni 0.3/0.4; codice, test e documenti.
- **Dati:** sintetici e archivi temporanei. Il controllo ufficiale SUC13 nei test è in gran parte servito dalla cache dei risultati (`docs/TEST.md`), quindi non vale come nuova esecuzione.
- **Legenda:** C = riprodotto o verificato sulle fonti; P = ricavato dalla lettura del codice.

## Corretto

| # | Area | Problema | Correzione |
|---|---|---|---|
| 1 | Copia anonima (C) | Restavano in chiaro il notaio del testamento, le denominazioni di enti, gli estremi di rinuncia, trascrizione e registrazione, la provenienza («atto notaio … a favore di ROSSI») e il titolare del conto esterno | Nomi e codici fiscali sostituiti anche dentro i testi; testi liberi ed estremi resi di fantasia; ogni campo di testo dello schema classificato (un test fallisce se ne nasce uno non classificato) |
| 2 | Prossime azioni (C) | Le ricevute si leggevano dalla copia più recente, non da quella trasmessa | Si legge la copia attiva, come nello stato degli elaborati |
| 3 | Prossime azioni (C) | Un pagamento negativo o volture parziali o negative davano «Pratica completata» | Restano da lavorare, con tappa «problema» e un'azione dedicata |
| 4 | Prossime azioni (C) | Oltre le prime 12 pratiche compariva «Genera il file» anche quando il file non si può generare | «Apri la pratica e verifica se il file telematico si può generare» |
| 5 | Elenco CSV (C) | I giorni al termine negativi diventavano testo | Restano numeri |
| 6 | Invio (P) | Il controllo che impedisce una nuova copia durante un invio aperto e la creazione della copia erano in due transazioni | Il controllo si ripete dentro la transazione che crea la copia |
| 7 | Fascicolo (C) | Includeva la stampa del modello anche se superata | La copertina lo dichiara e indica di rigenerarla |
| 8 | Preventivo (P) | Imposte prese da una bozza o da un file incompleto senza avviso | Avviso nel documento |
| 9 | Web (P) | Nome dello studio letto dalla configurazione globale e non da quella dell'archivio in uso | Si legge dall'archivio in uso |
| 10 | Web (P) | Nome del file .dcm messo nell'intestazione senza codifica | Codificato con `filename*` |
| 11 | Web (C) | Copia senza file telematico: errore 500 | 404 con il motivo |
| 12 | Fonti (C) | Usufrutto citato dal D.Lgs. 123/2025 e moltiplicatori dal D.Lgs. 141/2026 (applicabile dal 2027) | Prima la norma vigente al decesso, cioè il TUS (D.Lgs. 346/1990) come modificato dal D.Lgs. 139/2024, a cui rinvia il Fascicolo I, con art. 34 e art. 52 DPR 131/1986 e le rivalutazioni; i testi unici come conferma |
| 13 | Valore catastale (C) | Prima casa (110) applicata anche ad A/1, A/8, A/9 e A/11 | Moltiplicatore ordinario (120), come le esclusioni di `prima_casa.py` |
| 14 | Calcolatrice (C) | Categoria mancante calcolata come A/2 senza dirlo | La nota lo dice e chiede di verificare la visura |
| 15 | Avviso del saggio (C) | Con il diritto di abitazione l'avviso parlava di «usufrutto» | Testo per il diritto effettivo |
| 16 | Codice (C) | Funzioni morte (`_flag_ok`, `quota_json`), variabile e import inutilizzati, eccezioni senza causa | Tolti; `raise … from` |

L'interfaccia (procedura guidata, preventivo e finestre che si chiudono perdendo dati, accessibilità dei messaggi d'errore, tabella, calcolatrice, prestazioni della selezione) è affidata alla sessione della versione 0.4: l'esito è in fondo.

## Decisioni da confermare con il professionista

1. **Saggio legale per i decessi dal 2026.** Il programma usa il 2,5% e il prospetto in vigore, con un avviso. Il decreto MEF 2026 non è nelle fonti del progetto.
2. **Pertinenze della prima casa (C/2, C/6, C/7 con codice X).** Oggi hanno il moltiplicatore 120. L'estensione del 110 non è nelle fonti del progetto.
3. **Preventivo e parcella:**
   - IVA su compensi più contributo cassa e ritenuta sui soli compensi;
   - spese anticipate esenti (art. 15) e bollo non gestiti;
   - dicitura per i regimi senza IVA;
   - arrotondamento al centesimo voce per voce.
4. **Esiti delle ricevute che tengono aperta la pratica.** Oggi sono pagamento negativo, volture parziali o negative ed esiti contraddittori.

## Non fatto in questo giro (minori o da programmare)

- **Prestazioni:** la pagina iniziale e il CSV rifanno verifica e letture per ogni pratica a ogni richiesta. Da ottimizzare passando i risultati già calcolati.
- **Letture che possono scrivere:** `stato_elaborati` e `invio_stato`, chiamati da richieste GET, possono aprire transazioni di allineamento.
- **Backup:** il backup automatico prima della generazione blocca la richiesta. Inoltre non è una fotografia coerente: il database viene copiato prima degli allegati.
- **Idempotenza:** l'impronta di `aggiorna` non comprende l'origine della richiesta.
- **Copia anonima:** non indica quali controlli EG daranno rilievi senza allegati.
- **Data del preventivo:** cambia a ogni apertura finché non viene salvata.
- **Moduli grandi:** dividere `esporta.py`, `importa.py` e `app.js` solo se porta un beneficio concreto.
- **Test:** attese fisse in alcuni test; import «per effetto collaterale» del fixture `ctx`; `add_js` di pypdf deprecato.

## Cosa regge

- **Sicurezza dell'interfaccia locale:**
  - Host e Origin controllati;
  - cookie httponly e samesite=strict;
  - frame solo dallo stesso sito;
  - percorsi controllati;
  - CSV protetti dalle formule.
- **Archivio:**
  - transazioni IMMEDIATE;
  - conflitti di revisione;
  - chiavi di richiesta idempotenti;
  - ripristino solo in una cartella vuota.
- **MCP:**
  - classificazione prudente: uno strumento non in elenco conta come scrittura;
  - sola lettura con annullamento finale.
- **Invio:**
  - conferma solo dall'interfaccia;
  - un solo tentativo attivo per pratica, garantito dentro la transazione.
- **Calcolo:**
  - usufrutto e nuda proprietà riproducono gli esempi del Fascicolo I;
  - franchigie e aliquote coincidono con la guida al calcolo;
  - l'importazione non perde dati in silenzio.
- **Interfaccia:**
  - nessuno scorrimento orizzontale da 390 a 1920 px;
  - focus visibile;
  - modifica di un campo in 11 ms con 150 righi.
