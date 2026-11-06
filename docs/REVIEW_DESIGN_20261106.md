# Review dell'interfaccia — 6 novembre 2026

Ambito: `src/successioni/static` (`index.html`, `app.js`, `app.css`, `layout.js`).
Metodo: pratica dimostrativa, schermate a 1440×900 e 390×844 (`build/ui_0*.png`), misure sul CSS.
Proposta visiva in Canva: https://canva.link/u1k9jh1ow0tlsyh

## Giudizio sintetico

La struttura è buona: quadri a sinistra, tabella al centro, ispettore a destra e barra di stato in basso. Funziona per chi compila tutti i giorni. I problemi sono di rifinitura e di identità:
- l'aspetto imita un'app di sistema Apple con un accento verde acqua e non ha un carattere proprio;
- in alcune schermate il programma mostra campi e gergo che non servono in quel momento.

## Risultati per priorità

### Alta (incide sul lavoro di sabato)

1. **L'ispettore del quadro EC mostra tutto.** Per un immobile a Roma compaiono i dati esteri, l'intero blocco agevolazioni e gli estremi tavolari. Bisogna mostrare i campi in modo progressivo: i dati esteri solo se la provincia è EE, il tavolare solo per i comuni tavolari, le agevolazioni ripiegate se vuote.
2. **Gergo in vista.** Etichette e suggerimenti mostrano `[non_applicabile]`, «schema XSD» e importi col punto decimale (`1234.56`). Gli importi vanno mostrati all'italiana (`1.234,56`) e gli stati come parole: «non applicabile», «da confermare».
3. **File e invio senza un ordine.** I passi sono una vera sequenza (genera il file, controllo ufficiale, stampa e rileggi, invio con Desktop Telematico) ma appaiono come blocchi alla pari. Va resa come percorso numerato, con lo stato di ogni passo. Qui la numerazione è giustificata.
4. **Su mobile la barra di stato non è ancorata in basso.** Dopo il ricaricamento resta a metà schermo (`ui_07`).

### Media

5. **Due azioni principali di pari peso nella barra in alto.** Serve una sola azione primaria per contesto; l'altra diventa secondaria.
6. **Dati generali:** le etichette sono a volte sopra e a volte accanto ai campi; c'è «si'» al posto di «sì».
7. **Tabella EC:** quando è larga scorre in orizzontale lasciando vuoti a destra. Conviene fissare le colonne chiave (n., comune, foglio/particella, valore) e ripiegare le altre nell'ispettore.
8. **Impostazioni:** è una lunga finestra modale senza sezioni e le caselle di spunta sono disallineate. Va divisa in Studio, Programmi esterni, Aspetto, Diagnosi e backup, con un indice a sinistra.
9. **Pagina iniziale generica.** C'è un'etichetta in maiuscolo sopra il titolo e non ci sono dati utili. Meglio «Riprendi il lavoro»: pratiche recenti con stato e scadenza dei 12 mesi dal decesso, avvisi aperti e «Nuova dichiarazione» come unica azione primaria.

### Igiene del codice di stile

10. Ci sono 8 raggi diversi: ne bastano 2 (4px per i campi, 8px per i pannelli).
11. Ci sono circa 10 dimensioni di carattere fuori scala: va usata una scala a 5 passi (12, 13, 15, 18, 24 px).
12. `app.js` contiene 56 stili scritti nel codice: vanno spostati in classi di `app.css`.
13. Il fuoco da tastiera è visibile solo in pochi casi: serve una regola `:focus-visible` unica con l'anello nel colore d'accento.

## Direzione proposta: «il modulo ministeriale reso chiaro»

Lo spunto viene dal modello SUC verde dell'Agenzia: le caselle, le sigle dei quadri, i codici fiscali incasellati. Si evitano i luoghi comuni:
- niente crema e terracotta;
- niente maiuscoletto sopra i titoli;
- niente schede tutte uguali con ombra.

| Ruolo | Nome | Hex |
|---|---|---|
| Sfondo | Carta | `#F6F7F4` |
| Testo | Inchiostro | `#1F2A2A` |
| Accento e azioni | Verde modello | `#2F6B57` |
| Campi e selezione | Verde casella | `#DDEBE3` |
| Avvisi | Ocra timbro | `#A86A12` |
| Errori | Rosso registro | `#B3261E` |

**Caratteri.** Atkinson Hyperlegible Next per tutta l'interfaccia. Atkinson Hyperlegible Mono solo per codici fiscali, particelle e importi, perché distingue `0` e `O`. I caratteri vanno inclusi nel programma, che funziona senza rete.

**Elemento memorabile (uno solo).** Il codice fiscale in 16 caselle, come sul modello cartaceo, e le sigle dei quadri in caselle verdi nell'elenco a sinistra. Il resto rimane quieto.

**Temi.** Chiaro, scuro e seppia restano. Il tema scuro va ricavato dagli stessi ruoli: fondo `#151C1B`, testo `#E4EAE6`, accento `#7FB79F`. Il contrasto va verificato a WCAG AA.

## Ordine di lavoro consigliato

1. Dopo sabato: correggere i punti 1–4 (ispettore progressivo, gergo e importi, percorso File e invio, barra mobile).
2. Introdurre i token (palette, scala, raggi, fuoco) e togliere gli stili scritti nel codice.
3. Applicare la nuova direzione visiva, poi riorganizzare Impostazioni e la pagina iniziale.
4. Rifare le schermate a schermo largo, portatile e telefono, in chiaro e in scuro, e provare la navigazione da tastiera.

Prima della pratica reale non conviene cambiare l'aspetto: nessun punto blocca la compilazione.

## Stato dell'applicazione (6 novembre 2026)

Applicato tutto quanto sopra:
- **Correzioni 1–4:** commit `a0466ac`.
- **Direzione visiva e punti 5–13:**
  - palette e tema scuro con i ruoli indicati, contrasti verificati a WCAG AA;
  - caratteri Atkinson Hyperlegible inclusi nel programma (licenza OFL in `static/OFL-*.txt`);
  - scala tipografica e due soli raggi;
  - regola unica per il fuoco da tastiera;
  - codice fiscale in 16 caselle e sigle dei quadri in casella;
  - una sola azione piena per contesto nella barra in alto;
  - pagina iniziale con le pratiche recenti e il termine ordinario;
  - Impostazioni divise in sezioni con un indice;
  - Dati generali con etichette uniformi;
  - stili spostati da `app.js` in classi di `app.css`.
