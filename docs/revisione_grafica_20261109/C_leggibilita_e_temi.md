# Revisione C: leggibilità, contrasto e temi

**Norma:** WCAG 2.2 AA (1.4.3, 1.4.11, 2.4.7, 2.4.11), con il metodo della skill accessibility-review | **Data:** 09/11/2026
**Ambito:** temi chiaro, scuro, seppia, alto contrasto (chiaro e scuro), finestra 1440×900, testo predefinito di 16 px.
**Vincolo:** solo correzioni minime (valori dei token, dimensione o peso, contorno del focus, bordi, spazi). Struttura, componenti e testi restano come sono.

## Come ho misurato

- Ho usato Playwright con Chrome sull'istanza di prova `127.0.0.1:8833/?t=rev`, che contiene solo dati sintetici. Ho cambiato tema solo in memoria, con `applicaAspetto` nella pagina: niente «Salva», nessuna preferenza scritta, nessun backup, Pulisci, invio o controllo ufficiale.
- **Testo:** per ogni elemento visibile con testo proprio ho calcolato il colore effettivo (alfa e opacità degli antenati composte) contro lo sfondo composto dalla catena dei genitori. Per i campi vuoti ho misurato anche il `::placeholder`. Le schermate misurate sono: home, EC con la riga aperta (sopra e sotto), EA, EF, File e invio (sopra e sotto), EC compatta, Impostazioni (apertura, Aspetto, Operatività), Guida (4 linguette), procedura guidata, calcolatrice, menu Operazioni, linguette Controlli e Cronologia.
- **Elementi non testuali:** bordi di campi, menu, pulsanti, chip, sigle e pallini delle tappe, contro lo sfondo del contenitore. Per le caselle native ho letto i pixel dalla schermata.
- **Focus:** ho premuto Tab 60 volte nelle Impostazioni e 70 volte nel quadro EC con il pannello aperto, in tutti e tre i temi. Poi Shift+Tab 25 volte nel pannello dati, per vedere se il campo con il focus resta coperto.
- Script e risultati: `meas_c.js`/`meas_c.json`, `meas_c2.js`/`meas_c2.json`, `focus_c.js`/`focus_c.json`, `obscured_c.js`, `extra_c.js`. Le schermate del focus sono in `screens_c/`. Tutti i file sono nella cartella `revisione_ui`.

## Quadro generale

Il **testo normale va bene in tutti i temi.** Sotto 4,5:1 restano solo il segnaposto nel tema scuro (C02), il numero dentro il chip attivo (C03) e i pulsanti disabilitati, che la norma esenta (C06). Il **focus si vede ovunque**: anello di 2 px nel colore d'accento, mai sotto 4,8:1. Il **problema più serio non è di colore.** La barra «Dati / Controlli / Cronologia» resta ferma in alto nel pannello ma è trasparente: il contenuto le scorre sotto, visibile, e con Shift+Tab copre i campi che ricevono il focus (C01).

| Elemento (valori misurati) | Chiaro | Scuro | Seppia | Alto contr. chiaro | Alto contr. scuro | Richiesto |
|---|---|---|---|---|---|---|
| Testo principale `--t` su pannello | 14,3 | 13,5 | 11,4 | 14,3 | 16,4 | 4,5 |
| Testo secondario e aiuti `--t2` (peggior caso: su `--lat`/linguetta) | 4,97 | 5,20 | 5,38 | ≥12,9 | ≥14,3 | 4,5 |
| Sigla e «calcolato dal programma» su voce selezionata | 5,08 | 4,81 | 5,18 | 5,08 | 4,81 | 4,5 |
| Badge `.pz` (superato / dichiarante) | 5,30 / 5,37 | 5,80 / 5,62 | 5,30 / 5,37 | come chiaro | come scuro | 4,5 |
| Etichetta «calcolato» | 5,97 | ≥6 | ≥6 | 5,97 | ≥6 | 4,5 |
| **Segnaposto** (`#757575`, predefinito di Chrome) | 4,61 | **3,83** | 4,50 | 4,61 | **3,83** | 4,5 |
| **Numero nel chip attivo** | **3,83** | 5,02 | **4,04** | **3,83** | 5,02 | 4,5 |
| Pulsante disabilitato (Salva) | 2,68 | 3,68 | 2,47 | 2,68 | 4,22 | esente |
| Bordo dei campi nel pannello / nella barra laterale | 3,12 | 3,21–3,29 | 3,12 | 9,7 | 10,0 | 3,0 |
| Contorno del focus (minimo trovato) | 4,82 | 5,74 | 4,90 | ≥4,8 (3 px) | ≥5,7 (3 px) | 3,0 |

**Dimensioni:** con 16 px di base il carattere più piccolo misura 13,71 px (`--fs-s`: intestazioni di colonna, barra di stato, stato dei quadri, badge, aiuti in modalità compatta). Il valore è adeguato, ma scende a 10,3 px con il testo impostato a 12 px (C04).

## Rilievi (dal più importante)

| ID | Tema | Schermate | Problema | Misurato / richiesto | Causa | Correzione minima | Gravità |
|---|---|---|---|---|---|---|---|
| C01 | tutti | S106_scuro_pratica_EC, S60_compatta_EC, `screens_c/F_scuro_quadro_40.png`, `screens_c/F_chiaro_shifttab.png` | La barra «Dati / Controlli / Cronologia» resta ferma in alto nel pannello ma ha uno sfondo trasparente. Il testo dei campi le scorre sotto e si legge attraverso (nello scuro si vede «calcolato… H501» dietro «Dati»). Con Shift+Tab il campo che riceve il focus resta sotto la barra. | 6 campi su 25 coperti, fino a 34 px su 35 (es. «bene aziendale»): campo nascosto, contro 2.4.11 (focus non coperto). Sfondo misurato `rgba(31,42,42,.07)` | `app.css:170` `.ins > .seg { position:sticky; top:-16px; background:var(--grigio) }`: `--grigio` è semitrasparente | `.ins > .seg { background:linear-gradient(var(--grigio),var(--grigio)), var(--lat); }` e `.ins { scroll-padding-top:3.5rem; scroll-padding-bottom:var(--s-3); }` | **Alta** |
| C02 | scuro, alto contrasto scuro (al limite in chiaro e seppia) | S100, S102, S104, S105, calcolatrice | I segnaposto si leggono poco, e alcuni portano informazioni: «di legge» (quota), «GG/MM/AAAA», «codice fiscale», «Cerca una pratica / un argomento». | scuro 3,83:1, chiaro 4,61, seppia 4,50, contro 4,5:1 | Nessuna regola `::placeholder`: resta il grigio predefinito di Chrome `#757575` su `--campo` `#131A19` | Accanto a `app.css:96`: `::placeholder { color:var(--t2); opacity:1; }`. Risultato: 6,44 (chiaro), 8,34 (scuro), 7,34 (seppia); il valore inserito, in `--t`, resta distinto (14,5 nello scuro) | **Media** |
| C03 | chiaro, seppia, alto contrasto chiaro | S01, S02_*, S100 | Il numero bianco nel chip attivo («Tutte 2») è grassetto a 13,7 px, quindi non conta come testo grande. | chiaro 3,83:1, seppia 4,04, contro 4,5:1 (scuro 5,02) | `app.css:601` `.chip[aria-pressed=true] .n { background:color-mix(in srgb, var(--su-acc) 22%, transparent) }` | Portare `22%` a `12%`: diventa 4,76 (chiaro), 5,10 (seppia), più di 5 nello scuro | **Media** |
| C04 | tutti | S102 / S42 («Dimensione del testo») | La scelta «Dimensione del testo» va da 12 a 22 px. Con 12 o 14 px tutto il testo in `--fs-s` scende sotto il leggibile: intestazioni di colonna, barra di stato («2 avvisi», «Non finalizzabile»), «1 riga», badge, aiuti, `kbd`. | a 12 px: `--fs-s` 10,28 px, `--fs-m` 11,15 px; a 14 px: 12,0 e 13,0 px (contro un minimo pratico di 12 px) | `app.css:33` token in `rem`, senza soglia | `--fs-s:max(.857rem, 12px); --fs-m:max(.929rem, 13px);` (nessun effetto con i 16 px predefiniti) | **Media** |
| C05 | tutti | S43, S103 | Impostazioni > Operatività: etichetta della casella, testo d'aiuto ed etichetta del campo successivo hanno lo stesso colore e la stessa dimensione e sono attaccati, quindi non si capisce a quale opzione appartiene l'aiuto. | Etichetta e aiuto entrambi `#55615F` a 14,86 px; distanza fra un blocco e il successivo **0 px** in 3 casi su 4 | `app.css:204` `.campo label { color:var(--t2) }` vale anche per `label.chk`; nessun margine fra `.campo` in `#impPreferenze` (generati in `app.js:2554` e `2559`) | `#imp .campo + .campo { margin-top:var(--s-3); }` e `.campo > label.chk { color:var(--t); }` | **Media** |
| C06 | tutti | S106_*, S51_completa_EF, S111 (Salva, Stampa modello, Esegui controllo ufficiale) | I pulsanti disabilitati si leggono a fatica. La norma li esenta, ma «Salva» spento è lo stato che si controlla di continuo. | `.gh`: 2,68 (chiaro), 3,68 (scuro), 2,47 (seppia); `.pil`: 2,32–2,74 | `app.css:69` `button:disabled { opacity:.45 }` | `opacity:.6`: `.gh` passa a 4,07 / 5,37 / 3,61 e resta chiaramente spento | Bassa |
| C07 | tutti | S102, S43, S103 | Le caselle di spunta native misurano 13×13 px accanto a testo di 16 px: piccole da vedere e da puntare. Il bordo basta (`#767676` su bianco 4,54:1; `#858585` nello scuro). Tutta l'etichetta è cliccabile, quindi il bersaglio è conforme. | 13 px contro i 16 px del testo | `app.css:167` `.chk input`, `app.css:203` `.radio input` (solo `width:auto`) | `.chk input, .radio input { width:1rem; height:1rem; }` | Bassa |
| C08 | chiaro, seppia, scuro | S106_scuro_pratica_EC, S110, S51_completa_EC, S60_compatta_EC | Il bordo dei campi vuoti nel pannello dati e nella barra laterale (sfondo `--lat`) è conforme ma al minimo: «Comune amministrativo» o «Sezione urbana» vuoti quasi spariscono. Nello scuro il fondo del campo è uguale al pannello (1,09:1). | chiaro 3,12, seppia 3,12, scuro 3,21–3,29, contro 3:1 | `app.css:21` `--sep-f:.52`, `:45` `.40` (scuro), `:57` `.64` (seppia) | Alzare solo l'alfa: chiaro `.60` (3,88 su `--lat`), scuro `.48` (3,98–4,13), seppia `.72` (3,72) | Bassa |
| C09 | scuro | Guida > Tabelle e fonti (S105 e linguetta tabelle) | Le righe delle tabelle della guida usano un grigio fisso chiaro e nel tema scuro diventano linee bianche abbaglianti. È l'unico colore fuori dai token. | `#DDDDDD` su `#1F2928` 11:1, contro le righe delle altre tabelle a 1,49:1 | `app.css:651` `border-bottom:1px solid var(--bd, #ddd)`: `--bd` non è definito da nessuna parte | `var(--sep)` | Bassa |
| C10 | tutti | S106_*, S53 | Nelle sessioni lunghe la barra di stato in fondo (rilievi, avvisi, «Non finalizzabile…») è il testo più piccolo e più tenue proprio dove ci sono gli stati importanti. Il contrasto passa: 5,6:1 o più. | 13,71 px, `--t2` | `app.css:190` `.sb { font-size:var(--fs-s); color:var(--t2) }` | Portare `.sb` a `font-size:var(--fs-m)` (14,86 px). Colori invariati | Bassa |
| C11 | tutti | `screens_c/F_*_quadro_8.png` | Con Tab in avanti, l'anello del focus di 2 px viene tagliato sul bordo inferiore della barra laterale e del pannello: lo scorrimento automatico porta l'elemento a filo. Resta visibile su tre lati. | 1 voce della barra laterale e 4 campi del pannello con l'anello tagliato | Nessuno `scroll-padding` su `.lat` e `.ins` | Con C01 per `.ins`; inoltre `.lat { scroll-padding-block:var(--s-2); }` | Bassa |

## Cosa va già bene (da non toccare)

- I token di testo `--t` e `--t2` sono conformi in tutti i temi e su tutti gli sfondi (pannello, barra laterale, finestre, righe selezionate, riquadri ocra e ardesia).
- Il focus è sempre visibile: 2 px pieni, distanza 2 px (0 sui campi, dove diventa anche colore del bordo). Nell'alto contrasto lo spessore sale a 3 px. Nessun elemento interattivo trovato senza anello.
- L'alto contrasto chiaro e scuro porta tutti i bordi oltre 9:1. Restano scoperti solo il segnaposto (C02, che la correzione proposta sistema anche lì) e i pulsanti disabilitati.
- Il seppia non ridefinisce `--ok`, `--er` e `--am`, ma quelli del tema chiaro passano anche sul suo fondo (5,3–5,9:1).

## Ordine consigliato

C01, poi C02 e C03 (una riga di CSS ciascuna), poi C05 e C04. Tutte le altre sono modifiche di un solo valore.
