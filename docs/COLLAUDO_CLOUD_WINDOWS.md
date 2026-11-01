# Sviluppo Linux e collaudo della destinazione Windows

Il prodotto rimane un'applicazione locale Windows. Il container Linux è un ambiente di sviluppo valido per le parti indipendenti. Questa tabella descrive possibilità e prove richieste, non esiti già ottenuti.

| Area | Lavoro disponibile nel cloud Linux | Prova successiva / limite |
|---|---|---|
| Materiali | Presenza, hash, lettura PDF e XSD | Aggiornamento delle fonti prima del rilascio |
| Archivio | Persistenza, revisioni, allegati, migrazioni e backup | Percorsi, permessi, recupero e installazione Windows |
| Regole | Implementazione da fonti, casi sintetici e calcoli esatti | Confronti ufficiali e casi residui, senza presumere già validati i risultati |
| XML e stampa | Schema, serializzazione, riapertura interna e rendering PDF | Controllo ufficiale e verifica dei formati di lavoro realmente supportati |
| PDF/A | Conversione e verifica con dipendenze disponibili per Linux | Inclusione/installazione delle dipendenze e prova Windows |
| MCP | Server reale, protocollo, operazioni sullo stesso servizio, conflitti e richieste ripetute | Collegamento del client Claude effettivo su Windows/WSL e ciclo di vita |
| Controlli ufficiali | Ricognizione dei JAR e delle modalità supportate; esecuzione solo se concretamente disponibile | Se non eseguibile qui, diagnosi del limite e test riprendibile; non dire che è sicuramente Windows-only |
| Risultanze catastali | Contratto/adattatore, importazione tracciata, fixture sintetiche, scadenza sessione simulata | Accesso autorizzato al servizio reale, completezza e acquisizione effettiva |
| Invio e ricevute | Adattatore, stati, protocollo, import esiti di prova e gestione esito incerto | Ambiente dell'intermediario e successivo collaudo operativo autorizzato |
| Confezionamento | Script e documentazione, dipendenze fissate, eventuale verifica di build disponibile | Installazione e ripristino sulla postazione Windows |

## Regole degli esiti

- `passato`: prova eseguita, input/output e ambiente documentati.
- `fallito`: prova eseguita con esito negativo e diagnosi.
- `da collaudare`: prova non eseguibile nell'ambiente corrente; riporta prerequisito e procedura concreta per riprenderla.
- `simulazione`: test locale dell'adattatore; non equivale al servizio reale o al controllo ufficiale.

Un requisito `da collaudare` impedisce di dichiarare completata quella capacità operativa, ma non impedisce di sviluppare e provare il resto. Non chiedere conferma per proseguire attività già autorizzate e indipendenti.

Nessuna dichiarazione sintetica deve essere inviata alla produzione per provare il trasporto. Per la prima trasmissione operativa occorrono una pratica effettiva, verifica del professionista e autorizzazione specifica.
