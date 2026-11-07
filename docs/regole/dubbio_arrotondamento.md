# Dubbio di arrotondamento nel calcolo dell'imposta di successione

Stato: **divergenza aperta** per la regola DET.estero (quota d'imposta relativa al bene estero) e, in generale, per
ogni caso in cui la politica di arrotondamento cambia l'importo intero dichiarato. Specifica §8 e prova A08.
Aggiornato il 2026-11-01 (agente area 1).

## 1. Il dubbio

Fonte: `fonti/Specifiche tecniche/All. Specifiche tecniche (passaggi calcolo imposta di successione).pdf`
(10 pagine, sha256 `2570aacc73d0ab903fd4b265f50cbf761dd280cd1639653694c991c105b3c447`), pp. 5-8.

| Passaggio della guida | Valore esatto | Valore esposto nella guida | Arrotondamento compatibile |
|---|---|---|---|
| r = 125.000 × 6.567 / 200.000 (p. 5-6) | 4.104,375 | 4.104,38 | per eccesso (HALF_UP) |
| Rid.agevL = r × 0,5 (p. 6) | 2.052,1875 (da r esatto) / 2.052,19 (da r esposto) | 2.052,19 | — |
| e = 2.500 × 6.567 / 200.000 (p. 7) | **82,0875** | **82,08** | solo troncamento (HALF_UP e HALF_EVEN danno 82,09) |
| ISN = 6.567 − 2.052,19 − 82,08 (p. 8) | 4.432,725 (da valori esatti) | 4.432,73 | — |
| Totale due eredi (p. 8) | 8.865,45 (da valori esatti) | 8.865,46 | — |

Nessuna politica unica applicata ai centesimi produce sia 4.104,38 sia 82,08: l'esempio non definisce un criterio.
La guida non contiene alcuna regola di arrotondamento (ricerca di "arrotond" nel testo: nessuna occorrenza). Il campo
del modello in cui va l'imposta, `QuadroEF/SezioneVBis_ImpostaSuccessione/ImpostaCalcolata/Imposta` (rigo EF18bis
col. 2), e' `cm:DatoNP_Type` (euro interi), mentre la guida chiude con 8.865,46: anche il passaggio dai centesimi
all'euro non e' descritto (Fascicolo I p. PDF 46-47 non lo indica; altri righi EF, nelle annotazioni XSD, dicono
"arrotondato all'unità di euro, per difetto se la frazione è inferiore a 50 centesimi e per eccesso se non").

## 2. Ricerca di un chiarimento o esempio ufficiale (2026-11-01)

| Fonte consultata | Esito |
|---|---|
| Guida online <https://www.agenziaentrate.gov.it/portale/documents/d/guest/guida-calcolo-imposta-successione-per-dichiarazione-web> (PDF del 14/02/2025) | **identica** alla copia locale (stesso sha256 `2570aacc…`): nessun aggiornamento |
| "Guida al calcolo dell'imposta di successione" (strumento ALIS 2.x) <https://www.agenziaentrate.gov.it/portale/documents/d/guest/guida-calcolo-imposta-successione> (21 pp., PDF del 14/02/2025, sha256 `a6339989…2537`) | stesso esempio (4.104,38 a p. PDF 15; 82,08 a p. PDF 17); nessuna regola di arrotondamento. Indica che ALIS legge il file XML `.SUC` della dichiarazione |
| Circolare n. 3/E del 16/04/2025 <https://www.agenziaentrate.gov.it/portale/documents/20143/8410821/Circolare_decreto_delegato_Successioni_Donazioni.pdf> (23 pp., sha256 `ec94a24f…11ad`) | nessuna occorrenza di "arrotond" o "centesim" |
| Comunicato stampa 16/07/2025 "Successioni, da oggi la dichiarazione è più semplice" <https://www.agenziaentrate.gov.it/portale/documents/20143/8405056/045_Com.+st.+Calcolo+automatico+imposta+successione+16.07.2025/966b2ad5-16c6-8fd5-1ae0-a1a07d109d2a> | il software dell'Agenzia calcola in automatico l'imposta nel quadro EF; nessun criterio |
| Pagina del software <https://www.agenziaentrate.gov.it/portale/schede/dichiarazioni/dichiarazione-di-successione/sw-comp-dichiarazione-successioni-telematiche> | versione 2.3.0 del 15/07/2025 "Calcolo automatico dell'imposta di successione"; 2.3.1 del 11/03/2026 "Aggiornamento uffici" |
| Ricerche web sul sito dell'Agenzia (arrotondamento autoliquidazione) | nessuna regola esplicita trovata |

Nessun chiarimento ufficiale scritto e' stato trovato.

## 3. Riscontro applicativo: ispezione statica del componente ufficiale

**Natura della prova**: lettura del bytecode con `javap -c` (JDK 21 del container), **senza eseguire** il programma.
E' un riscontro sul comportamento del software, non una regola fiscale (specifica §3): non sostituisce la norma ne'
la guida e non equivale al controllo ufficiale.

Componente: `controlliXMLREG2013.jar` scaricato il 2026-11-01 da `https://jws.agenziaentrate.it/jws/registro/2013/`
(risorsa del `SUC13.jnlp`, identico a `fonti/Programma e controlli/SUC13 (4).jnlp`),
sha256 `0b42dfc37e673a4cee65f696bbf84612fee0c898a7a3b0456b661d17dece6a10`, classi datate 2025-03-18 nell'archivio.

| Passaggio | Metodo | Comportamento rilevato |
|---|---|---|
| AN | `modSUC2013.CalcolaImpostaSuccessione.calcolaAttivoNettoAN` | QE + QDN − QP; se <= 0 vale 0 |
| QN | `calcolaQuotaNettaQN` | AN − FR; se <= 0 vale 0 e la franchigia residua passa agli altri righi dello stesso codice fiscale |
| PR | `calcolaPresunzionePR` | `new BigDecimal(0.1d) × (QN − QDN)` poi `setScale(2, HALF_UP)`, meno QDN; se <= 0 vale 0; non calcolata se tipo soggetto 2 o se nel quadro ER c'e' un cespite BI |
| ISL | `calcolaImpostaSuccessioneLordaISL` | `(QTI × AL).setScale(2, HALF_UP)` |
| r (agevolazioni) | `modSUC.beans.AgevolazioniRiduzioni.calcolaAliquota` | valore quota × (ISL ÷ QE a 10 decimali HALF_UP); L × 0,5; Q, R, F × 0,4 (R, F con soglia 103.291); nessun arrotondamento finale salvo un ramo R (`setScale(2)`) |
| r25 | `AgevolazioniRiduzioni.calcolaRiduzione` | divisioni a 6 decimali HALF_UP, coefficiente, `setScale(3, HALF_UP)` |
| e, DET | `CalcolaImpostaSuccessione.setDET` | e = (valore quota × (ISL ÷ QE a 10 decimali HALF_UP)).`setScale(4, HALF_UP)`; IE = imposta estera × (num ÷ den a 5 decimali HALF_UP); DET = minore dei due |
| ISN | `calcolaImpostaSuccessioneNettaISN` | ISL − RID − DET; se < 0 vale 0; nessun arrotondamento |
| Totale | `modSUC2013.ImpostaSuccessione.calcolaImpostaSuccessione` (restituisce `long`) | somma degli ISN con `setScale(2, HALF_UP)` dopo ogni addendo; risultato `setScale(0, HALF_UP).longValue()` |

I valori quota sono letti come `double` (`new BigDecimal(double)`), con possibili residui binari.

Applicato all'esempio della guida: e = **82,0875** (4 decimali, non 82,08), Rid.agevL = 2.052,1875,
ISN = 4.432,725 per erede, totale 4.432,73 + 4.432,725 = 8.865,455 -> **8.865,46**, importo intero **8.865**.
Quindi i valori finali esposti dalla guida (4.432,73 e 8.865,46) sono coerenti con il componente, mentre 82,08 e' una
rappresentazione dell'intermedio che il componente conserva a 4 decimali. Con aritmetica esatta il totale e' 8.865,45:
**l'importo intero dichiarabile (8.865) e' lo stesso** in tutte e tre le letture, ma il centesimo no.

## 4. Decisione implementata (`src/successioni/telematico/calcolo.py`)

- Valori intermedi in `Fraction` esatta, riportati con fonte e pagina per ogni passaggio.
- Due candidati espliciti: `esatta` (nessun arrotondamento intermedio; centesimo ed euro HALF_UP sul totale: ipotesi
  dichiarata) e `componente_ispezionato` (scale della tabella sopra).
- `completato` solo se i candidati danno lo **stesso importo intero** per EF18bis; un'eventuale differenza al
  centesimo e' riportata in nota e il centesimo **non** e' considerato validato.
- `divergenza_aperta` se l'importo intero cambia: il caso non e' finalizzabile. Esempio provato
  (`tests/test_telematico_calcolo.py::test_divergenza_aperta_quando_l_arrotondamento_cambia_l_importo`): valore
  150.159 ripartito 1/3 e 2/3 fra due cugini (6%, nessuna franchigia) -> esatto 9.910,494 -> 9.910; componente
  9.910,50 -> 9.911.
- DET.estero, riduzioni e agevolazioni (dove compaiono 4.104,375 e 82,0875) **non sono implementati**: il calcolo
  restituisce `non_supportato`. Il dubbio della specifica resta quindi aperto per quella regola.
- `esito_collaudo` e' sempre `da_collaudare`.

Interpretazioni dichiarate (non scritte nella guida, coerenti con il componente): AN e QN non negativi; nessuna
franchigia per i gradi non elencati a p. 3; corrispondenza `05a/07a/09a` (guida) = `5A/7A/9A` (XSD).

## 5. Limiti residui e prova che chiude il dubbio

- L'ispezione statica puo' non vedere percorsi alternativi (per esempio la parte ALIS in Excel o altre classi);
  i residui dei `double` e l'ordine di iterazione delle mappe Java possono cambiare il centesimo nei casi limite.
- Prova necessaria (**da collaudare**, postazione con Java e interfaccia grafica): compilare nel software ufficiale
  2.3.x (o con ALIS 2.x) un caso di riferimento che includa agevolazione L e imposta estera come nell'esempio, e il
  caso dei cugini sopra; confrontare l'importo EF18bis calcolato dal software con i due candidati e registrare
  versione, input e output. Finche' la prova manca, il calcolo resta una proposta da confermare.

## 6. Aggiornamento 2026-11-03: riduzioni art. 25 e controllo ufficiale eseguito in locale

- Il controllo ufficiale SUC13 2.3.1 **eseguito in locale** (dati sintetici) ricalcola l'imposta di successione e scarta il file
  se EF18bis non corrisponde (diagnostici 3454 e 3481). Per i casi con riduzioni art. 25, L, Q, R, F implementati
  (docs/regole/riduzioni_art25.md) l'importo intero calcolato e' accettato e l'importo +1 e -1 e' scartato: l'**intero**
  di EF18bis coincide con quello del componente per ogni caso provato. Il centesimo non e' osservabile (campo in euro interi).
- Il dubbio 82,0875 / 82,08 riguarda `DET.estero`, ancora **non implementata**: resta aperto. Non e' stato eseguito con il
  componente alcun caso con imposta estera.
- Ispezione statica aggiuntiva (`javap -c`, nessuna esecuzione): scale di `AgevolazioniRiduzioni.calcolaAliquota` e
  `calcolaRiduzione` riportate nel §3 di riduzioni_art25.md.


## 7. Aggiornamento 2026-11-07: somme dei 'Valore quota' con centesimi nei campi interi del quadro EF

**Problema.** Ogni `QuotaValore` (cm:DatoVP_Type) e' il valore del bene per la quota, arrotondato al centesimo
(ROUND_HALF_UP, `formati.frazione_a_centesimi`): con quote 1/3 la somma delle righe puo' avere centesimi (3 x 2004,33 =
6012,99 per un bene da 6013). I campi che riportano queste somme sono in euro interi (cm:DatoNP_Type): EF1 e EF9 col. 1
(`ImpostaProporzionale_Imponibile`), EF4 col. 2 (`AgevolazionePX_Valore`). Prima di questa modifica il quadro EF non veniva
generato («somma dei 'Valore quota' ... non intera»): caso reale di una sostitutiva codice 1 con prima casa, somma 104.903,97.

**Fonti.**
- Annotazione XSD di `QuotaValore`: la somma dei valori quota puo' scostarsi dal valore del bene fino all'1% e comunque non
  oltre 100 euro (i centesimi dell'arrotondamento delle quote sono quindi ammessi).
- Annotazioni XSD dei righi EF (`ImpostaProporzionale_Imposta` di EF1 ed EF9, `AgevolazioneG_Imposta`, EF8, EF14): importi
  «arrotondato all'unita' di euro, per difetto se la frazione e' inferiore a 50 centesimi e per eccesso se non inferiore»;
  l'imposta e' calcolata sul «campo precedente» (l'imponibile intero).
- Il file originale del caso reale, accettato dall'Agenzia, riporta 104.904 (somma 104.903,97) in EF1 e EF9 e imposte
  2.098 e 1.049.

**Riscontro col controllo ufficiale SUC13 2.3.1 eseguito in locale** (non e' la verifica dell'Agenzia): la riesportazione
del caso reale con 104.904 e' accettata; la stessa con 104.903 e' scartata con il diagnostico 3120 su EF1 col. 1 e EF9
col. 1 (valore atteso dal componente: 104.904). Quindi arrotondamento all'euro (HALF_UP), non troncamento.

**Decisione implementata** (`quadri_efgh._somma_in_euro`): le somme dei valori quota di EF1, EF9 (col. 1) ed EF4 (col. 2)
sono arrotondate all'unita' di euro con la regola sopra, con l'avviso `ARROTONDAMENTO_SOMMA_VALORI_QUOTA`; le imposte
proporzionali sono il 2% / 1% dell'imponibile intero, poi arrotondate all'euro. Le somme delle agevolazioni G ed M (EF2, EF3)
restano bloccanti se non intere: nessun caso provato col componente. Prove: `tests/test_quote_non_intere.py` (caso sintetico
con tre eredi a 1/3, controllo ufficiale locale positivo, imponibile troncato scartato con 3120).
