# Design system — Successioni (MASTER)

Fonte di verità per l'aspetto dell'interfaccia locale (`src/successioni/static`). Le pagine con regole proprie stanno in `pages/`, che qui non contiene ancora nulla. I token sono in [`tokens.css`](tokens.css).

**Come è stato generato (8/11/2026).**
- Il punto di partenza è l'analisi di `app.css`, che conta 622 righe e 125 classi.
- Il resto viene dalla skill `ui-ux-pro-max`, con la query «professional tax filing desktop tool accountant government forms».
- Impostazioni usate: densità 8, movimento 2, varianza 3.

**Cosa ho preso dalla skill e cosa no.**
- Presi lo stile *Minimalism & Swiss*, il font Atkinson Hyperlegible, la scala densa degli spazi e le regole UX citate più avanti.
- **Ho scartato la palette blu navy** che la skill propone. È generica: per il settore pubblico non trova nessuna palette verde. Sostituirebbe un'identità già scelta e approvata («il modulo ministeriale reso chiaro», `docs/REVIEW_DESIGN_20261106.md`).
- Ho invece verificato la palette esistente con i criteri della skill: testo ≥ 4,5:1, controlli ≥ 3:1.

## 1. Principi

1. **Il modulo ministeriale reso chiaro.** Si prendono i colori del modello verde dell'Agenzia e un solo segno memorabile: codici fiscali e sigle dei quadri in caselle. Tutto il resto resta quieto.
2. **Densità da studio professionale.** È uno strumento di lavoro quotidiano su desktop: molte righe visibili e spazi stretti ma regolari, senza effetti decorativi.
3. **Il calcolato non si confonde con lo scritto.** I valori proposti dal programma hanno una tinta propria, l'ardesia. Non si scrivono da soli.
4. **Lo stato si capisce senza colore.** Ogni esito ha testo e icona oltre alla tinta.
5. **Leggibilità prima di tutto.** Atkinson Hyperlegible, base 14 px regolabile, tre temi (chiaro, scuro, seppia), contrasto alto e movimento ridotto.

Da evitare (dalla skill e dall'identità):
- ornamenti, gradienti, viola o rosa «da AI», ombre complesse, 3D;
- animazioni d'ingresso;
- emoji al posto delle icone;
- grigio su grigio;
- la sola tinta per dire «errore».

## 2. Colore

Tre livelli: **primitivi** (`--p-*`), **semantici** (i nomi storici `--t`, `--blu`, `--sep-f`… usati da app.js e dalle preferenze) e **componenti** (`--btn-*`, `--campo-*`…).

| Ruolo | Token | Chiaro | Scuro | Seppia |
|---|---|---|---|---|
| Testo | `--t` | #1F2A2A | #E4EAE6 | #3C342A |
| Testo secondario | `--t2` | #55615F | #A9B5B0 | #5E5343 |
| Fondo pagina | `--fondo` | #F6F7F4 | #151C1B | #EDE5D7 |
| Barra laterale | `--lat` | #EEF1EC | #1A2221 | #EEE6D9 |
| Pannello | `--pann` | #FBFCFA | #182120 | #FAF6EE |
| Campo | `--campo` | #FFFFFF | #131A19 | #FFFCF7 |
| Accento (verde modello) | `--blu` | #2F6B57 | #7FB79F | #6E5732 |
| Casella / selezione | `--blu-t` | #DDEBE3 | verde al 20% | #EADFCB |
| Esito positivo | `--ok` / `--ok-t` | #2B6B45 / #E1EFE5 | #8CCB9F / 20% | come chiaro |
| Errore (rosso registro) | `--er` / `--er-t` | #B3261E / #F7E3E1 | #F2A39C / 20% | come chiaro |
| Avviso (ocra timbro) | `--am` / `--am-t` | #86540C / #F5EBD8 | #E3B66A / 20% | come chiaro |
| Valore calcolato | `--calc-b` / `--calc` | #3E5794 / #E8EDF7 | #A9BEEF / #232C3B | #4A4F7A / #E6E6EE |
| Bordo controlli | `--sep-f` | inchiostro al **52%** | testo al **40%** | seppia al **64%** |
| Divisori | `--sep` | inchiostro al 13% | testo al 14% | seppia al 16% |

### Contrasto verificato (WCAG 2.2, calcolo sui valori reali)

| Coppia | Chiaro | Scuro | Seppia |
|---|---|---|---|
| Testo su fondo | 13,7 | 14,2 | 9,8 |
| Secondario su fondo | 6,0 | 8,2 | 6,0 |
| Accento su pannello | 6,1 | 7,2 | 6,3 |
| Testo su pulsante primario | 6,3 | 7,4 | 6,8 |
| Accento su casella | 5,1 | 4,9 | 5,2 |
| Esito / errore / avviso sulla propria tinta | 5,4 / 5,3 / 5,4 | 6,2 / 6,4 / 6,2 | 5,4 / 5,3 / 5,4 |
| Valore calcolato | 6,0 | 7,6 | 6,3 |
| **Bordo dei campi, com'è oggi** | **2,0 ✗** | **2,8 ✗** | **1,8 ✗** |
| Bordo dei campi, con i nuovi token | 3,0 | 3,1 | 3,0 |

**Correzione necessaria:** il bordo dei campi non raggiunge 3:1 (WCAG 1.4.11, contrasto dei componenti) in nessun tema. `tokens.css` porta `--sep-f` al 52%, 40% e 64%. Il contrasto alto resta come oggi (75-80%).

## 3. Tipografia

| Token | rem | px (base 14) | Uso |
|---|---|---|---|
| `--fs-s` | .857 | 12 | etichette, note, barra di stato, badge |
| `--fs-m` | .929 | 13 | tabelle, campi densi, menu |
| `--fs-base` | 1 | 14 | testo |
| `--fs-l` | 1.286 | 18 | titoli di sezione e di finestra |
| `--fs-xl` | 1.714 | 24 | titolo di pagina |

- **Caratteri:** Atkinson Hyperlegible Next per l'interfaccia; Atkinson Hyperlegible Mono per codici fiscali, importi nei riepiloghi e percorsi. Sono già inclusi in locale (OFL), quindi niente Google Fonts: il programma funziona offline.
- **Pesi:** 400 testo, 550 etichette e intestazioni di tabella, 700 titoli e valori chiave.
- **Interlinea:** 1,5 per il testo, 1,25 per titoli e celle.
- **Numeri:** `tabular-nums` ovunque; importi allineati a destra.
- **Testo minimo:** 12 px. Sotto non si scende nemmeno nella barra di stato.
- **Fuori scala oggi:** `1.071rem` (3 usi) diventa `--fs-base`; i `font-size:1rem` diventano `--fs-base`.

## 4. Spazi

Base 4 px, scala densa. Lo spazio fra elementi di un gruppo è minore di quello fra gruppi.

| Token | px | Uso tipico |
|---|---|---|
| `--s-05` | 2 | distanza icona-bordo, caselle CF |
| `--s-1` | 4 | dentro i badge, fra icona e testo stretto |
| `--s-15` | 6 | celle in verticale, spazio dei pulsanti |
| `--s-2` | 8 | celle in orizzontale, campi, spazio standard |
| `--s-3` | 12 | pulsanti, distanza fra campi |
| `--s-4` | 16 | pannelli, distanza fra gruppi |
| `--s-5` | 20 | margini di `main` (desktop medio) |
| `--s-6` | 24 | finestre, sezioni |
| `--s-8` | 32 | blocchi della pagina iniziale |
| `--s-10` | 40 | respiro sopra i titoli di pagina |

Oggi `app.css` usa **21 valori diversi**. Quelli fuori scala si arrotondano al passo più vicino:

| Oggi | Diventa |
|---|---|
| 3 px | 4 |
| 5 px | 4 o 6 |
| 7 px | 6 o 8 |
| 9 px, 10 px | 8 o 12 |
| 11 px | 12 |
| 14 px | 12 o 16 |
| 18 px | 16 o 20 |
| 22 px | 20 o 24 |
| 28 px | 24 o 32 |

## 5. Forma ed elevazione

- **Arrotondamenti:** `--r0` 2 px (caselle CF, barre); `--r1` 4 px (campi, pulsanti); `--r2` 8 px (pannelli, finestre); `--r-pill` per i badge; `--r-tondo` per le tappe. I `3px` e l'`8px` scritti a mano diventano token.
- **Elevazione:**

  | Token | Uso |
  |---|---|
  | `--e0` | niente |
  | `--e1` | bordo di 1 px, cioè le schede e i pannelli |
  | `--e2` | bordo più un'ombra morbida, solo per ciò che galleggia: menu, finestre, avvisi a comparsa |

  Le schede ferme non hanno ombra.

## 6. Movimento

- `--dur-1` 120 ms per hover e stato dei controlli; `--dur-2` 180 ms per il cassetto laterale e le aperture; `--ease` cubic-bezier(.2,0,0,1).
- Si animano solo colore, opacità e `transform`, mai larghezza o altezza.
- Niente animazioni d'ingresso allo scorrimento: la skill suggerisce GSAP, ma per uno strumento di lavoro è rumore, e l'app non usa librerie esterne.
- `prefers-reduced-motion` e l'impostazione «movimento ridotto» azzerano le durate.

## 7. Focus e accessibilità

- Anello di focus da 2 px nel colore d'accento, staccato di 2 px; 3 px con contrasto alto. Nei campi l'anello è a filo e il bordo diventa d'accento.
- Ogni controllo con sola icona ha `aria-label`. Le icone decorative hanno `aria-hidden`.
- **Errori:**
  - messaggio specifico sotto il campo, collegato con `aria-describedby`;
  - dopo un salvataggio non riuscito, riepilogo in testa con collegamenti ai campi e focus sul riepilogo;
  - niente errori al solo `blur`.
- **Finestre:** trattengono il focus, Esc chiude, il focus torna al pulsante che le ha aperte. Invio non chiude una finestra con dati.
- **Finestre e cassetto:** non coprono l'elemento che ha il focus (WCAG 2.4.11).
- **Aree cliccabili:** almeno 24×24 px (WCAG 2.5.8). Su schermo stretto, 44×44.
- **Ruoli:** chi dichiara `menu` o `tab` deve muoversi con le frecce; altrimenti si usano pulsanti normali.

## 8. Componenti

| Componente | Specifica | Stati |
|---|---|---|
| **Pulsante primario** | alto 32, `--btn-px` 12, `--r1`, fondo `--blu`, testo `--su-acc`, icona 16 + spazio 6 | hover: luminosità al 92%; attivo: 85%; focus: anello; disabilitato: opacità .45 e `cursor:not-allowed`; in corso: indicatore e `aria-busy` (protegge dal doppio clic) |
| **Pulsante secondario** | come il primario, con fondo `--solido`, bordo `--sep-f` e testo `--t` | hover: fondo `--grigio` |
| **Pulsante di testo** (`lk-azione`) | colore `--blu`, nessun bordo | hover e focus: sottolineato, distanza 3 px |
| **Campo** | alto 30, `--campo-px` 8, bordo `--sep-f`, fondo `--campo`, testo `--fs-m` | focus: bordo `--blu` e anello a filo; errore: bordo `--er-b` più messaggio; calcolato: fondo `--calc` e testo `--calc-b`, con l'indicazione «proposto»; sola lettura: fondo `--grigio` |
| **Caselle CF e sigle dei quadri** | carattere mono, una casella per carattere, larga 1,35 em, bordo `--sep-f`, `--r0` | è il segno distintivo: si usa solo per codici e sigle |
| **Tabella dei righi** | celle 6×8, intestazione 550 `--fs-s` `--t2`, righe con divisore `--sep`, importi a destra | hover: `--grigio`; selezionata: `--blu-t` più filo a sinistra di 3 px `--blu`; focus della riga: anello all'interno |
| **Badge di stato** | alto 20, a pillola, `--fs-s`, tinta di fondo e colore del ruolo | sempre con testo; l'icona è facoltativa, il colore non basta mai |
| **Tappe** (Dati → File → Controllo → Invio → Ricevute) | cerchio da 18, linea da 2, etichetta `--fs-s` | fatta: piena `--ok-b` con spunta; bloccata: bordo `--er-b` con «!» e motivo nel testo; da fare: bordo `--sep-f`; corrente: anello `--blu` |
| **Scheda di Prossime azioni** | pannello `--r2`, bordo `--sep`, spaziatura 16 | il motivo del blocco va in un riquadro con filo sinistro `--er-b` o `--am-b`; la scadenza a destra in `--t2` |
| **Finestra** | larga al massimo 720, spaziatura 24, `--r2`, `--e2`, titolo `--fs-l` | trattiene il focus; azioni in fondo a destra, la principale per ultima |
| **Avviso a comparsa** | `--e2`, `--r2`, `role="status"`, oppure `alert` per gli errori | resta finché serve se contiene un'azione |
| **Titolo del quadro** | sigla in casella piena `--blu` (mono 700, `--r0`) seguita dal titolo `fs-xl`; su schermo stretto il titolo va su una riga sua | il titolo accessibile resta «EA — Eredi…» |
| **Controlli** | campi, menu a tendina e pulsanti con icona alti uguali (min. 2,2 rem); i collegamenti con aspetto di pulsante (es. «Elenco in CSV») si allineano agli altri | etichetta in grassetto = dato richiesto dal quadro, spiegato in testa alla scheda |
| **Titoli di sezione** | inchiostro `--t`, grassetto, `fs-base`, ovunque (schede, finestre, calcolatrice); il verde resta per azioni e selezione | |
| **Barra laterale** | fondo `--lat`, pratiche in `--fs-m` | sotto 960 px diventa un cassetto (180 ms) che trattiene il focus |

## 9. Larghezze dello schermo

Le soglie sono quelle di oggi:

| Larghezza | Comportamento |
|---|---|
| fino a 480 | marchio compatto |
| fino a 560 | una colonna |
| fino a 960 | cassetto laterale e tabelle in schede |
| 961-1440 | desktop medio, margini 16-20 |
| oltre 1440 | desktop largo |

Nessuno scorrimento orizzontale a 390 px: titoli lunghi con `overflow-wrap:anywhere` e barra di stato che va a capo.

## 10. Adozione nell'app (non ancora fatta)

`tokens.css` è compatibile con `app.css`: i nomi semantici sono gli stessi. Passi proposti:

1. Sostituire il blocco `:root` di `app.css` con il contenuto di `tokens.css`. Correggere i bordi a ≥ 3:1 è l'unica modifica visibile.
2. Sostituire spazi, arrotondamenti e dimensioni fuori scala con i token (sezioni 3-5).
3. Usare i token dei componenti nelle regole di pulsanti, campi, tabella e finestre.
4. Rifare le prove dell'interfaccia (`tests/e2e/esegui_tutti.py`) e le schermate dei tre temi.

## Checklist prima della consegna

- [ ] Testo ≥ 4,5:1 e controlli ≥ 3:1 nei tre temi e con contrasto alto
- [ ] Focus visibile su ogni controllo, anche nelle finestre; nessun focus coperto
- [ ] Nessuna emoji come icona; icone SVG con maschera `[data-ic]`
- [ ] Stati di hover, attivo, disabilitato e in corso su ogni pulsante; protezione dal doppio clic
- [ ] Errori sotto il campo con `aria-describedby` e riepilogo che riceve il focus
- [ ] `prefers-reduced-motion` e «movimento ridotto» rispettati
- [ ] Prove a 390, 768, 1366×768 e 1920 px, senza scorrimento orizzontale
- [ ] Nessun valore fuori scala: spazi, arrotondamenti e testo vengono dai token
