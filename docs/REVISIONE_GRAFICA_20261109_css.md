# Revisione grafica del 9/11/2026: campi delle finestre (analisi del codice CSS)

Ambito: `src/successioni/static/app.css`, `app.js` (Impostazioni e finestre generate) e `index.html`. Questa è un'analisi del
codice: non ho modificato nulla. Le immagini sono raccolte a parte, dalla sessione che coordina la revisione.

Vincolo del professionista: **nessuno stravolgimento**. Restano uguali la struttura, le sezioni e la posizione delle cose.
Si correggono solo allineamenti, spazi, larghezze dei campi e la gerarchia dei testi di aiuto.

## Sintesi

Ho esaminato **7 finestre**: Impostazioni, Nuova dichiarazione, finestre operative (`dialogo()`), Preventivo, Calcolatrice,
Guida e Scorciatoie. Più i moduli di File e invio e Dati generali, per confronto. I problemi trovati sono **9**.

Tutti nascono da un fatto solo: **manca un modello comune per una riga di modulo**. Ogni finestra si arrangia con regole
proprie e rimedi locali.

## Cause, con i punti del codice

| # | Problema visto | Causa nel codice | Dove |
|---|---|---|---|
| 1 | I campi numerici (24, 90) occupano tutta la larghezza | Regola globale `input, select, textarea { width:100% }`. Nessuna classe di larghezza per numeri, date, CF e importi; solo rimedi locali (`.calc-riga input.n 7.5em`, `.q 4.5em`, preventivo `9em` e `6em`) | `app.css:85`, `516`, `534`, `661`, `663` |
| 2 | «Pulisci ora» è attaccato al campo | In `impPreferenzeRender` il pulsante è un fratello diretto dei `.campo` dentro `<section>`. `.campo` non ha margini propri, quindi tra i campi non c'è spazio | `app.js` `impPreferenzeRender`; `app.css` non definisce lo spazio tra `.campo` |
| 3 | Caselle e testi di aiuto ammassati, senza ritmo | Lo spazio tra i campi esiste solo per casi isolati: `.strumenti .campo { margin-top:s-3 }`, `.voce-imp { margin-bottom:s-3 }` (in Strumenti si sommano: 24 px), `.diagnosi-voce s-15`, `.aspetto-griglia gap s-4`. In Operatività vale **0** | `app.css:288`, `291`, `292`, `364` |
| 4 | L'aiuto sembra un'etichetta | Etichetta (`.campo label`: `fs-m`, `--t2`) e aiuto (`.mut.testo-m`: `fs-m`, `--t2`) hanno **stessa dimensione e stesso colore**. In più il testo della casella (`.chk span`) è a dimensione base: l'etichetta è più grande della domanda | `app.css:204`, `349`, `81` |
| 5 | L'aiuto sotto una casella non è allineato al testo | L'aiuto parte dal bordo sinistro, sotto il quadratino, invece che sotto il testo della casella | `app.js` `casella()` in `impPreferenzeRender` |
| 6 | Quattro modi diversi di scrivere «etichetta sopra il campo» | `.campo label` (fs-m, t2, margine s-05), `.file-griglia label` (margine s-3/s-1), `.persona-campi .rg > label` (margine s-1), `.dlg-op .rg > label` (grassetto 600, flex) | `app.css:204`, `263`, `251`, `436`, `441` |
| 7 | `.chk` nasce come voce di elenco (bordo sotto, rientro s-3) e va annullato ovunque | La regola globale con il bordo viene annullata in `#imp`, `.file-griglia`, `.calc-riga` e `.dlg-op` | `app.css:166`, `285`, `265`, `518`, `440` |
| 8 | Due classi per lo stesso errore | `.err` (margine e altezza minima) e `.e` (fs-m): `dialogo()` usa `.e`, Impostazioni e Nuova dichiarazione usano `.err` | `app.css:81`, `153`; `app.js` `dialogo()` |
| 9 | Valori scritti a mano invece dei token | `.file-griglia input.cf { padding:6px … }`, `scroll-padding-top:12px`; nel preventivo `width:9em`, `6em` e spazi in sintassi diversa | `app.css:267`, `279`, `656-665` |

### Token

| Categoria | Definiti | Fuori dai token |
|---|---|---|
| Spazi | 10 (`--s-05` … `--s-10`) | 2 casi in px (punto 9). Il problema vero non sono i valori ma la **mancanza di una regola per lo spazio fra i campi** |
| Testo | 5 (`--fs-s` … `--fs-xl`) | Nessuno; manca però un ruolo «aiuto» distinto dall'etichetta |
| Larghezze dei campi | **0** | 8 larghezze locali in em |

## Proposta: un solo modello di modulo per tutte le finestre

Si aggiungono classi nuove e non si cambia l'HTML delle sezioni: in JS cambiano solo le classi che le funzioni già generano.

```
.modulo                    contenitore: campi uno sotto l'altro, distanza uniforme
  .campo                   etichetta / controllo / aiuto
    label                  fs-m, peso 600, colore --t (più marcata dell'aiuto)
    input|select           larghezza secondo il dato (classi l-*), non al 100%
    .aiuto                 fs-s, --t2, margine sopra s-1, al massimo 70ch
  .campo.casella           casella + testo su una riga; l'aiuto allineato al testo, non al quadratino
  .campo .in-linea         controllo + pulsante sulla stessa riga, distanza s-2 (es. ore + «Pulisci ora»)
.modulo-griglia            come .aspetto-griglia: due colonne, poi una sotto i 960 px
```

### Spazi fissi (un solo ritmo)

| Fra | Spazio |
|---|---|
| etichetta e controllo | `--s-1` (4 px) |
| controllo e aiuto | `--s-1` (4 px) |
| un campo e il successivo | `--s-4` (16 px) |
| titolo `h3` di sezione e primo campo | `--s-2` (8 px), come oggi |
| una sezione e l'altra | `--s-6` (24 px), con la riga di separazione come oggi |
| pulsante di sezione (es. «Crea backup ora») e campo precedente | `--s-3` (12 px) |

### Larghezze secondo il dato (token nuovi)

```css
:root { --l-num:7rem; --l-data:11rem; --l-cf:calc(16 * var(--cella, 1.4ch) + 2rem); --l-importo:12rem;
        --l-breve:16rem; --l-media:28rem; --l-lunga:40rem; }
.modulo :is(input, select):not([type=checkbox]):not([type=radio]) { max-width:var(--l-lunga); }
input[type=number], input.l-num { width:var(--l-num); }
input[type=date],   input.l-data { width:var(--l-data); }
input.cf { max-width:var(--l-cf); }
input.importo, input.l-importo { width:var(--l-importo); text-align:right; font-variant-numeric:tabular-nums; }
.l-breve { max-width:var(--l-breve); } .l-media { max-width:var(--l-media); }
```

La regola globale `width:100%` (`app.css:85`) **resta com'è**: la usano tabelle, schede dei quadri e filtri. Le larghezze
nuove valgono solo dentro `.modulo` e per i tipi `number` e `date`. I percorsi di Strumenti restano lunghi (`--l-lunga`).

### Gerarchia del testo

| Ruolo | Dimensione | Peso | Colore |
|---|---|---|---|
| Titolo di sezione (`h3`) | fs-base | 700 | --t (invariato) |
| Etichetta / testo della casella | fs-m | 600 | --t |
| Valore nel controllo | fs-base | 400 | --t |
| Aiuto | **fs-s** | 400 | --t2 |
| Errore | fs-m | 400 | --er (una sola classe; `.e` diventa sinonimo di `.err`) |

### Casella con aiuto

```css
.campo.casella { display:grid; grid-template-columns:auto minmax(0,1fr); column-gap:var(--s-2); align-items:start; }
.campo.casella > input { margin-top:.2em; accent-color:var(--blu); }
.campo.casella > .aiuto { grid-column:2; }   /* sotto il testo, non sotto il quadratino */
```

## Applicazione, finestra per finestra (stessa struttura)

1. **Impostazioni > Operatività e sicurezza.** Sezione dentro `.modulo`. «Ore» e «giorni» a `--l-num`. «Pulisci ora» va
   **sulla stessa riga** del campo delle ore (`.in-linea`), nello stesso punto di oggi. Caselle in `.campo.casella` con aiuto
   allineato. Tra un campo e l'altro 16 px.
2. **Impostazioni > Aspetto.** Già in griglia: menu fino a `--l-media`; testi di aiuto in `.aiuto`; i 15 quadri proposti
   restano in griglia, togliendo l'annullamento di `.chk`.
3. **Impostazioni > Studio.** CF a `--l-cf`; menu fino a `--l-media`.
4. **Impostazioni > Backup e Diagnosi.** Testo descrittivo in `.aiuto` (fs-s), pulsante con 12 px sopra. Esiti della diagnosi
   invariati.
5. **Impostazioni > Strumenti e percorsi.** Togliere il doppio spazio (`.strumenti .campo` + `.voce-imp`): resta 16 px. Le due
   righe di stato e nota diventano `.aiuto`.
6. **Finestre operative (`dialogo()`, `.dlg-op`).** Etichette come `.campo label` (600 invece del flex in grassetto); caselle con
   `.campo.casella`; errore `.err`.
7. **Nuova dichiarazione, Preventivo, Calcolatrice.** Solo classi di larghezza al posto delle em locali (`.calc-riga input.n` →
   `l-num`, preventivo `9em` → `l-importo`); impaginazione invariata.

Fuori ambito: tabelle, schede dei quadri (`.ins .rg`, densità compatta), pagina iniziale e File e invio. Hanno regole proprie
già riviste. Prendono solo, se si vuole, le classi `l-*`.

## Verifiche proposte (e2e, dati sintetici)

Da aggiungere a `tests/e2e/esegui_tutti.py`, prova nuova `gui_moduli.js`, a 1440×900 e 1920×1080:

- in Impostazioni ogni `input[type=number]` è largo ≤ 8rem;
- «Pulisci ora» sta sulla stessa riga del campo delle ore (stesso `top` ± 4 px), con almeno 8 px di distanza;
- tra campi consecutivi di una `.modulo` la distanza verticale è 16 px ± 2;
- il testo di aiuto è più piccolo dell'etichetta (`fontSize` minore) e il suo bordo sinistro coincide con il testo della
  casella, non con il quadratino;
- nessun campo esce dalla finestra (`scrollWidth <= clientWidth`) e restano valide le prove di contrasto esistenti.

`tests/test_design_system.py` resta il guardiano dei token: le larghezze nuove passano come variabili, non come numeri sparsi.
