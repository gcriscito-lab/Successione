# Confronto con i software di successioni - 5 novembre 2026

**Metodo e limiti.** Ricerca web su schede commerciali e articoli (DE.A.S. di Geo Network, Eredito di GEC, Blumatica SuccessOne,
CIS Successioni di Wolters Kluwer, software gratuito dell'Agenzia). Non ho provato nessun prodotto: le funzioni dei concorrenti
sono quelle **dichiarate dai produttori o da siti terzi**, spesso datate (2017-2020). Nessuna classifica indipendente trovata.
La colonna «Noi» e' verificata sul codice del repository (ricerche nel sorgente) e sulle prove eseguite.

| # | Funzione | Concorrenti (fonte) | Noi oggi | Gap |
|---|---|---|---|---|
| 1 | Pratica da visura catastale PDF / acquisizione Entratel | DE.A.S.: importa visure PDF, «crea pratica da visura», flusso da Entratel | Adattatore catasto con normalizzazione e dati sintetici; nessun lettore di visure PDF; nessun accesso reale | **Alto** (il lettore PDF e' realizzabile senza credenziali) |
| 2 | Quota legale automatica per ogni grado, anche premorti e rinunciatari | CIS Successioni (Wolters Kluwer) | Figli, coniuge, genitori, fratelli (tabelle Allegato 5); niente rappresentazione, nonni, premorti, rinunce | **Alto** |
| 3 | Successioni storiche (aperte prima del 2025; SuccessOne dichiara dal 16/5/1949) e agevolazioni per periodo d'imposta | SuccessOne | Quadro EF coperto solo per decessi dal 2025; prima, nessun XML se ci sono immobili | **Alto** |
| 4 | Ripartizione di diritti e imposte per erede/legatario con prospetti analitici | SuccessOne, DE.A.S., Eredito | Calcolo interno ma nessun prospetto per soggetto/bene esposto all'utente | Medio-alto |
| 5 | Documenti accessori: F23/F24 compilati, autocertificazioni, editor di testi | Eredito (PDF editabili: dichiarazione, F23, autoliquidazione, autocertificazioni), SuccessOne (editor integrato) | Nessuno nel sorgente | Medio |
| 6 | Calcolo di diritti reali (usufrutto, nuda proprieta') | SuccessOne («calcolo dei diritti e ripartizione») | Codici diritto dell'XSD gestiti; calcolo con coefficienti da verificare | Da verificare |
| 7 | Trasmissione senza Desktop Telematico | DE.A.S. (dal 2020, dichiarato) | Controllo ufficiale locale integrato; trasmissione reale assente | Alto, ma richiede credenziali e postazione |
| 8 | Albero genealogico generato | Eredito (relazioni familiari) | Solo allegato manuale | Basso-medio |

**Fatto nuovo da tenere presente (volture).** Dal 12 gennaio 2026 l'applicativo Voltura 2.0 e' dismesso e l'unico canale e'
Voltura catastale Web (provvedimento del 27 marzo 2025). I programmi che esportavano il file `.dat` per Voltura 1/2.0 (Eredito)
vanno intesi come superati su quel punto: **non conviene costruire un export `.dat`**.

**Dove abbiamo qualcosa che le fonti pubbliche degli altri non citano** (non e' una prova di superiorita'): controllo ufficiale
SUC13 locale integrato e usato per validare le regole, stampa del modello ministeriale con il codice dell'Agenzia, rilevazione
automatica delle regole delle annotazioni XSD, archivio con revisioni, accesso via MCP.

## Fonti
- DE.A.S. (scheda e articoli): https://www.lavoripubblici.it/prodotti/DE-A-S-Gestione-completa-pratiche-successorie/1264 ; https://www.ingenio-web.it/articoli/la-dichiarazione-di-successione-telematica-al-via-definitivo-ecco-cosa-ci-aspetta-per-il-2019/
- Eredito: https://www.infobuild.it/software-edilizia/eredito-software-per-la-dichiarazione-di-successione-e-voltura-catastale/
- SuccessOne: https://www.lavoripubblici.it/prodotti/Blumatica-SuccessOne/485
- CIS Successioni: https://wolterskluwer.com/it-it/solutions/cis-successioni
- Voltura Web: https://www.lavoripubblici.it/news/stampa/37130 ; https://www.edotto.com/articolo/catasto-dismissione-dellapplicativo-voltura-20-telematica
