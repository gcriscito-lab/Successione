# Guida per la prima pratica reale (aggiornata al 2026-11-07)

**Per chi e' e per quale caso.** Pratica con decesso **dal 1/1/2025**, devoluzione **per legge**, immobili in **un solo comune**,
conti, titoli e passivita'. Questo perimetro e' coperto e provato con il controllo ufficiale SUC13 2.3.1 eseguito in locale su
dati sintetici. **Nessuna prova e' stata fatta con i servizi dell'Agenzia ne' su una pratica reale**: la responsabilita' della
dichiarazione resta del professionista, e il programma e' un assistente di compilazione, non un sostituto dei suoi controlli.

## 0. Prima di iniziare (10 minuti)
0. **Un solo archivio per interfaccia e Claude.** Per la pratica reale usa `Avvia-pratica-reale.cmd` (archivio `%USERPROFILE%\Successioni-reale`, separato da quelli di
   prova). Il server MCP di Claude Code e di Claude Desktop e' gia' configurato sulla stessa cartella (2026-11-05): apri una **sessione nuova** di Claude Code o riavvia
   Claude Desktop, poi verifica con `successioni_capacita` (deve indicare la cartella `Successioni-reale`).
1. Esegui `Diagnosi.cmd` (o `python scripts\windows\diagnosi.py`): devono risultare OK Java 8, il controllo SUC13, Ghostscript, veraPDF.
2. Fai un **backup** dell'archivio: Impostazioni → Backup → «Crea backup ora» (oppure `successioni backup <cartella>`). Imposta la cartella dei backup su **un'altra unita'**.
   Prima di ogni «Genera file» il programma ne fa uno automatico. Rifallo a fine lavoro.
3. Tieni a portata il **compilatore ufficiale** (SuccessioniOnLine/Suc13) come rete di sicurezza e per il confronto dei totali.

## 1. Dati da avere sul tavolo
- **Defunto**: cognome, nome, codice fiscale, data/luogo di nascita, **data del decesso**, stato civile.
- **Dichiarante/presentatore**: dati anagrafici, **codice carica**, telefono **o** email, e la conferma della firma.
- **Eredi**: per ciascuno codice fiscale, dati anagrafici, **grado di parentela** (es. 01 coniuge, 02 figlio), eventuali disabilita'. Se un figlio e'
  premorto o ha rinunciato: i suoi discendenti con `rappresentato_cf` e `rappresentato_grado`.
- **Immobili** (dalle **visure aggiornate a non piu' di 3 mesi**): **data della visura**, provincia, comune, **codice catastale**, indirizzo, foglio, particella,
  subalterno, categoria, classe, consistenza, **rendita**, **quota di possesso** e **diritto**, e il **valore venale alla data del decesso**
  (il Fascicolo chiede il valore di mercato, non un valore derivato dalla rendita). Terreni: reddito dominicale, superficie, natura,
  tipologia (edificabile o no). Per la **prima casa** servono i requisiti e il numero degli immobili agevolati.
- **Conti e titoli**: saldo alla data del decesso, intestazione, quota.
- **Passivita'**: tipo, importo, estremi e data del documento, bene collegato (es. mutuo).
- **Quote di devoluzione**: la somma dei valori delle quote deve poter essere un numero **intero** di euro (il Fascicolo non indica come arrotondare).
- **Allegati in PDF**: albero genealogico (obbligatorio), documenti delle passivita', documento d'identita' se chi presenta non e' il dichiarante, eventuali dichiarazioni sostitutive.
- **Pagamento**: IBAN e codice fiscale del titolare per l'addebito se paghi contestualmente (tempistica 2); altrimenti l'F24 e' da fare a parte (il programma non lo genera).

## 2. Procedura
1. Avvia il programma con `Avvia-pratica-reale.cmd`. Si apre l'interfaccia locale.
2. Crea la pratica con la **procedura guidata**, poi compila i quadri. In alternativa detta i dati a Claude, che li inserisce con gli strumenti MCP:
   **leggi sempre tu il risultato**, campo per campo, contro le visure e i documenti.
3. Allega i PDF nella scheda **File** (conversione e verifica PDF/A: l'esito «conforme» appare solo se veraPDF l'ha verificato).
4. Apri **Controlli**: devono essere **0 rilievi**. Ogni rilievo indica il campo e la fonte.
5. Nella scheda **File**: compila il profilo del fornitore e premi **Genera file** (scopo «completo»: se manca qualcosa non produce nulla).
6. **Esegui controllo ufficiale**: deve dare *positivo (passato)*. Se non hai chiesto l'attestazione, un solo avviso e' normale: «non e' stata richiesta l'attestazione di avvenuta presentazione». Per chiederla (serve per sbloccare i conti): Dati generali, sezione 5, «Richiesta attestazione di avvenuta presentazione» = sì; il programma aggiunge 32 euro di bollo (EF16) e 16 di tributi speciali (EF18).
7. **Stampa modello ministeriale**: controlla a vista **tutte le pagine** contro i documenti (nomi, codici fiscali, particelle, quote, valori, totali EF, IBAN).
   Gli allegati EG compaiono solo come flag. La stampa e' una prova locale, non una certificazione.
8. **Confronto dei totali** con un calcolo indipendente (a mano o con il compilatore ufficiale): ipotecaria 2%, catastale 1%, tassa ipotecaria 120 e bollo 85 per
   circoscrizione, imposta di successione e franchigie; **ImportoDaVersare** deve coincidere. Se non coincide, **non inviare**: segnalalo.
9. **Prepara e conferma la copia da inviare** (scheda File, riquadro «Invio e ricevute»), PRIMA di aprire Desktop Telematico:
   1. **Prepara invio**: congela il file XML aggiornato con il controllo ufficiale positivo. Se compare «Requisiti per la conferma», correggi
      (di solito: controllo non positivo o file rigenerato dopo il controllo) e ripeti.
   2. Spunta «Ho verificato il file…» e premi **Conferma questa copia** (solo dall'interfaccia: Claude non puo' confermare).
   3. Premi **Istruzioni per l'invio reale**: il programma NON trasmette, ma registra il **tentativo** (stato «attesa invio manuale») e
      mostra nome e SHA-256 del file da inviare. Senza questo passo protocollo, `.esi` e ricevute non hanno un tentativo a cui
      agganciarsi.
   4. **Scarica la copia congelata** (`copia_congelata.xml`) e usa quel file, **senza rinominarlo**: il nome serve ad abbinare il `.esi`.
10. **Invio con gli strumenti ufficiali**: in Desktop Telematico/Entratel *controllo SUC13 → Autentica → Invia* sulla copia congelata. Le
    credenziali restano li'. Per sicurezza **ricontrolla il file nel Desktop Telematico** (stesso componente 2.3.1): se la' da' errori,
    fermati e registra «invio non avvenuto» (punto 11).
11. **Registra l'esito nel programma** (stesso riquadro, sotto il tentativo), il giorno stesso:
    - con il **file `.esi`** dell'invio (Entratel-Multifile; quale file produca Desktop Telematico e' **da collaudare**): scegli il file e
      premi **Registra file .esi** (abbinato per nome del file e data, mai per ordine d'arrivo; se non e' riferibile il tentativo resta
      aperto e vengono mostrati i motivi);
    - oppure scrivi il **protocollo** e **dove l'hai verificato** (prima ricevuta, «Ricerca ricevute») e premi **Registra protocollo**;
    - se l'invio non e' partito, **Registra invio non avvenuto** indicando dove l'hai verificato: solo allora si puo' preparare una nuova copia.
    Finche' l'esito non e' registrato il programma **non prepara un'altra copia** (rischio di doppio invio). Con il protocollo registrato
    compare «Ricevute ed esiti successivi»: allega ogni ricevuta con il suo tipo (trasmissione, registrazione, pagamento, volture...).
12. Fai il backup finale.

## 3. Quando fermarsi e usare il compilatore ufficiale
- Il programma segnala un caso **non supportato** o genera solo una bozza tecnica.
- Il controllo ufficiale non e' positivo, o i totali non coincidono col calcolo indipendente.
- Compare un elemento **non coperto** dal programma (blocca il file o lo lascia in bozza): trust, curatore/amministratore/morte presunta
  (cariche 5, 6, 8, 9), stesso soggetto su piu' righi con imposta dipendente dall'ordine, pagamento tardivo con sanzioni e interessi, rimborsi,
  immobili in piu' comuni senza il componente configurato.
- Compare un elemento **coperto ma fuori dal perimetro di questa prima pratica** (provato solo col controllo locale su dati sintetici,
  `docs/MATRICE_COPERTURA.md`): decesso prima del 2025, rinunce, testamento con legatari, enti, residenti all'estero, beni esteri e
  imposta pagata all'estero, aziende, agevolazioni diverse da prima casa. Per la prima pratica reale conviene restare nel perimetro
  iniziale; se ci rientra, raddoppia i controlli col compilatore ufficiale.

## 4. Limiti da ricordare
- Nessuna prova con l'Agenzia: l'accettazione ufficiale del file non e' garantita dal solo controllo locale.
- Il programma **non** legge le visure PDF: i dati catastali si inseriscono (o li legge Claude dalle visure, sotto la tua verifica).
- Rateazione e sostitutive codici 1 e 2 sono supportate; sanzioni e interessi e rimborsi no. Successioni **aperte dal 3/10/2006 al 31/12/2024**:
  il file si genera con il quadro EF senza la sezione V-bis (imposte ipocatastali, tassa e bollo; l'imposta di successione la liquida
  l'ufficio, quindi il programma non la calcola); prima del 3/10/2006 il file non si genera.
- Evidenze e limiti aggiornati: `docs/MATRICE_COPERTURA.md`, `docs/regole/`, `docs/CONFRONTO_MERCATO_20261105.md`.
