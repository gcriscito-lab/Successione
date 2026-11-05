# Guida per la prima pratica reale (aggiornata al 2026-11-05)

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
- **Immobili** (dalle **visure aggiornate a non piu' di 3 mesi**): provincia, comune, **codice catastale**, indirizzo, foglio, particella,
  subalterno, categoria, classe, consistenza, **rendita**, **quota di possesso** e **diritto**, e il **valore venale alla data del decesso**
  (il Fascicolo chiede il valore di mercato, non un valore derivato dalla rendita). Terreni: reddito dominicale, superficie, natura,
  tipologia (edificabile o no). Per la **prima casa** servono i requisiti e il numero degli immobili agevolati.
- **Conti e titoli**: saldo alla data del decesso, intestazione, quota.
- **Passivita'**: tipo, importo, estremi e data del documento, bene collegato (es. mutuo).
- **Quote di devoluzione**: la somma dei valori delle quote deve poter essere un numero **intero** di euro (il Fascicolo non indica come arrotondare).
- **Allegati in PDF**: albero genealogico (obbligatorio), documenti delle passivita', documento d'identita' se chi presenta non e' il dichiarante, eventuali dichiarazioni sostitutive.
- **Pagamento**: IBAN e codice fiscale del titolare per l'addebito se paghi contestualmente (tempistica 2); altrimenti l'F24 e' da fare a parte (il programma non lo genera).

## 2. Procedura
1. Avvia il programma (`Avvia-programma-aggiornato.cmd`, collegamento «Successioni» o `successioni gui`). Si apre l'interfaccia locale.
2. Crea la pratica con la **procedura guidata**, poi compila i quadri. In alternativa detta i dati a Claude, che li inserisce con gli strumenti MCP:
   **leggi sempre tu il risultato**, campo per campo, contro le visure e i documenti.
3. Allega i PDF nella scheda **File** (conversione e verifica PDF/A: l'esito «conforme» appare solo se veraPDF l'ha verificato).
4. Apri **Controlli**: devono essere **0 rilievi**. Ogni rilievo indica il campo e la fonte.
5. Nella scheda **File**: compila il profilo del fornitore e premi **Genera file** (scopo «completo»: se manca qualcosa non produce nulla).
6. **Esegui controllo ufficiale**: deve dare *positivo (passato)*. Un solo avviso e' normale: «non e' stata richiesta l'attestazione di avvenuta presentazione».
7. **Stampa modello ministeriale**: controlla a vista **tutte le pagine** contro i documenti (nomi, codici fiscali, particelle, quote, valori, totali EF, IBAN).
   Gli allegati EG compaiono solo come flag. La stampa e' una prova locale, non una certificazione.
8. **Confronto dei totali** con un calcolo indipendente (a mano o con il compilatore ufficiale): ipotecaria 2%, catastale 1%, tassa ipotecaria 120 e bollo 85 per
   circoscrizione, imposta di successione e franchigie; **ImportoDaVersare** deve coincidere. Se non coincide, **non inviare**: segnalalo.
9. **Invio reale (strumenti ufficiali)**: scarica l'XML e il **file controllato `.dcm`** dalla scheda File. Poi, con Desktop Telematico/Entratel:
   *controllo SUC13 → Autentica → Invia*. Il programma non usa le tue credenziali e non trasmette. Per sicurezza **ricontrolla il file nel Desktop Telematico**
   (e' lo stesso componente 2.3.1): se il controllo la' da' errori, fermati.
10. Registra nel programma l'esito/ricevuta (riconciliazione) e fai il backup finale.

## 3. Quando fermarsi e usare il compilatore ufficiale
- Il programma segnala un caso **non supportato** o genera solo una bozza tecnica.
- Il controllo ufficiale non e' positivo, o i totali non coincidono col calcolo indipendente.
- Compare un elemento fuori perimetro: rinunce, trust, enti o stranieri, aziende, beni esteri, testamento con legatari complessi, agevolazioni diverse da prima casa e art. 25,
  pagamento tardivo con sanzioni, immobili in piu' comuni senza il componente configurato.

## 4. Limiti da ricordare
- Nessuna prova con l'Agenzia: l'accettazione ufficiale del file non e' garantita dal solo controllo locale.
- Il programma **non** legge le visure PDF: i dati catastali si inseriscono (o li legge Claude dalle visure, sotto la tua verifica).
- Rateazione e sostitutive codici 1 e 2 sono supportate; sanzioni e interessi, rimborsi e successioni **aperte prima del 2025** (quadro EF) no.
- Evidenze e limiti aggiornati: `docs/MATRICE_COPERTURA.md`, `docs/regole/`, `docs/CONFRONTO_MERCATO_20261105.md`.
