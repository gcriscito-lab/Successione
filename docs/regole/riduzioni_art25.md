# Riduzioni dell'art. 25 e agevolazioni L, Q, R, F (imposta di successione)

Stato: implementate nel perimetro descritto al §4; esito **controllo locale** (componente ufficiale SUC13 2.3.1 eseguito in
locale con dati sintetici), **non** collaudo su Desktop Telematico e **non** trasmissione. Aggiornato il 2026-11-03.
Codice: `src/successioni/telematico/riduzioni_art25.py` (regole di esportazione), `calcolo.py` (formule), `quadri_efgh.py`
(Sezione IV del quadro EH, righi EG8/EG11), `esporta.py` (righi di devoluzione). Test: `tests/test_telematico_riduzioni_art25.py`.
Mutation testing: `scripts/mutazioni_riduzioni_art25.py` (§7).

Fonti (pagine PDF): XSD = `fonti/Specifiche tecniche/SUC13_20250702/SUC/xsd/fornituraSUC13_v1.xsd`; Fasc. I =
`Succ_FASCICOLO_I_Nov_23.pdf`; Guida = `All. Specifiche tecniche (passaggi calcolo imposta di successione).pdf`
(10 pagine, stesso SHA-256 di `dubbio_arrotondamento.md`).

## 1. Cosa prevedono le fonti (analisi di partenza)

| Elemento XSD | Dove | Significato (fonte) |
|---|---|---|
| `Riduzioni` (`CodiciRiduzioni25comma1_Type`: 1, 2, 3, 4, 5) | `Devoluzione` di tutti i quadri EB-ER | art. 25 c. 1, beni oggetto di precedenti successioni/donazioni entro 1..5 anni (XSD; Fasc. I p. PDF 27, 63) |
| `ValorePrecSucc` | rigo del cespite (EB, EC, EL, EM, EN, EP, EQ, ER; EO dentro `Possesso`) | «Non puo' essere presente in assenza di riduzioni art. 25 c. 1 ... obbligatorio in presenza ... non superiore al campo valore» (annotazione XSD) |
| `Agevolazioni` = `L` | `Devoluzione` | beni culturali, vincolo posteriore all'apertura, art. 25 c. 2 (XSD `CodiciRiduzioni25AltriComma`; Fasc. I p. PDF 62-63) |
| `Agevolazioni` = `Q` | `Devoluzione` | aziende, quote di societa' di persone, beni strumentali in comuni montani, art. 25 c. 4-bis |
| `Agevolazioni` = `R` | `Devoluzione` | fondi rustici, art. 25 c. 3 |
| `Agevolazioni` = `F` | `Devoluzione` (solo EC, EM) | immobili di impresa artigiana familiare, art. 25 c. 4 |
| `QuadroEH/.../SezioneIV_AltreAgevRiduz` | EH, primo modulo | richieste del dichiarante: `EsenzioneImpostaSuccessione` (A, L), `Agevolazioni` (C, D, E, Q), `Riduzioni` (estremi della dichiarazione o donazione precedente) |
| `QuadroEG/RiduzioniImposteSuccessione` | EG, rigo EG11 | richieste di soggetti diversi dal dichiarante per A, L, Q, 1-5 (Fasc. I p. PDF 50) |

Altre agevolazioni dell'XSD (A, C, D, E, G, H, M, N) **non** sono riduzioni dell'art. 25: A, C, D, E, G, H, N escludono la quota
dalla QE (Guida p. 1) e restano **non supportate**; M non cambia la QE ma non e' trattata; P, X, Y, Z: vedi `prima_casa.md`.

## 2. Formule (Guida pp. 5-7) e rigo/colonna

Per il beneficiario con QE (quota ereditaria) e ISL (imposta lorda) gia' determinati (Guida pp. 1-5):

| Passaggio | Formula (fonte) |
|---|---|
| r (agevolazioni) | `valore quota agevolata x ISL / QE`; «valore quota» = campo `QuotaValore` della riga di devoluzione (Guida p. 5-6) |
| Rid.agevL | `r x 0,5` (p. 6) |
| Rid.agevQ | `r x 0,4` (p. 6) |
| Rid.agevR, Rid.agevF | quota <= 103.291,00: `r x 0,4`; quota > 103.291,00: `(103.291,00 x ISL / QE) x 0,4` (p. 6) |
| r25 | `(ValorePrecSucc x valore quota con art. 25 / valore cespite) x ISL / QE` (p. 7); «valore cespite» = campo `Valore` del rigo |
| Rid.art25 | `r25 x` 0,5 / 0,4 / 0,3 / 0,2 / 0,1 per i codici 1 / 2 / 3 / 4 / 5 (p. 7) |
| RID | `Rid.art25 + Rid.agevL + Rid.agevQ + Rid.agevR + Rid.agevF` (p. 7) |
| ISN | `ISL - RID - DET.estero`, DET = 0 nel perimetro (p. 8); non negativa (interpretazione, come in `dubbio_arrotondamento.md`) |

Importi nel file: `Agevolazioni` / `Riduzioni` nella `Devoluzione` del cespite (EB..ER), `ValorePrecSucc` nel rigo del cespite
(EO: dentro `Possesso`), imposta complessiva in `QuadroEF/SezioneVBis_ImpostaSuccessione/ImpostaCalcolata/Imposta` (rigo
EF18bis col. 2, euro interi). Le riduzioni non modificano la base delle imposte ipotecaria e catastale (quadro sinottico delle
riduzioni, Fasc. I p. PDF 62: «riduzioni relative all'imposta di successione»): EF1/EF9 invariati.

## 3. Arrotondamenti: cosa dicono le fonti e cosa si e' fatto

La Guida **non** definisce arrotondamenti (nessuna occorrenza di «arrotond»; l'esempio di p. 6 espone 4.104,38 per 4.104,375 e
2.052,19 per 2.052,1875). Si applica la stessa politica di `calcolo.py` (§4 di `dubbio_arrotondamento.md`): due candidati, stato
`completato` solo se l'**intero** dichiarabile coincide.

- `esatta`: nessun arrotondamento intermedio; centesimo e poi euro HALF_UP sul totale (ipotesi dichiarata).
- `componente_ispezionato`: scale lette con **ispezione statica** (`javap -c`, nessuna esecuzione) di
  `it.finanze.entrate.sco.modSUC.beans.AgevolazioniRiduzioni` e `modSUC2013.CalcolaImpostaSuccessione` in
  `controlliXMLREG2013.jar` (stesso SHA-256 di `dubbio_arrotondamento.md`). Riscontro applicativo, non regola fiscale:
  - L, Q, R, F: rapporto `ISL / QE` a **10** decimali HALF_UP; `r = valore quota x rapporto` (nessun arrotondamento); coefficienti
    `new BigDecimal(0.5d)` / `0.4d` (valori `double`, con residuo binario); R, F oltre soglia: `103291 x rapporto x 0,4`; per R la
    **somma** delle riduzioni R e' riportata a 2 decimali HALF_UP (solo nel ramo oltre soglia); nessun arrotondamento per L, Q, F;
  - art. 25: rapporto `ISL / QE` a **6** decimali; `(VPS x valore quota) / valore` a **6** decimali; prodotto dei due; riduzione =
    coefficiente (`double`) x r25 con `setScale(3, HALF_UP)`;
  - `RID` = somma senza arrotondamento; `ISN = ISL - RID - DET` senza arrotondamento (se < 0 vale 0); il totale accumula gli ISN
    con `setScale(2, HALF_UP)` e chiude con `setScale(0, HALF_UP)`.
  I valori quota, VPS e valore sono letti come `double` (`new BigDecimal(double)`): replicato con `Fraction(float(...))`.
- **Controllo ufficiale SUC13 2.3.1 eseguito in locale (dati sintetici)**: il componente ricalcola l'imposta e scarta il file se
  EF18bis non corrisponde (diagnostici 3454 per `Imposta`, 3481 «Il valore dell'imposta di successione non corrisponde al valore
  calcolato»). Nei test, per ogni caso positivo l'importo calcolato e' accettato e **+1 e -1 sono scartati**: l'**intero**
  dichiarato e' quindi confermato dal componente ufficiale per ogni caso della tabella al §5. Non conferma il centesimo
  (EF18bis e' `cm:DatoNP_Type`, euro interi) e non sostituisce il collaudo su Desktop Telematico.
- Dubbio 82,0875 / 82,08: riguarda la detrazione estera (`DET.estero`), **non implementata**; resta aperto.
  L'esempio di p. 6 (r = 4.104,375, Rid.agevL = 2.052,1875) e' riprodotto da `test_esempio_della_guida_con_agevolazione_l`:
  senza DET il totale esatto e' 9.029,625 (esatta: 9.029,63; componente: 9.029,62), **intero 9.030 per entrambi**.

## 4. Perimetro supportato (esportazione + calcolo)

| Codice | Quadri | Richiesta del dichiarante | Richiesta di altri beneficiari |
|---|---|---|---|
| 1-5 (art. 25 c. 1) | EB, EC, EL, EM, EN, EO, EP, EQ, ER (non cespiti DN) | EH Sez. IV `Riduzioni` (estremi della dichiarazione precedente **oppure** della donazione precedente) | EG11 + EG7 (documento d'identita') |
| L | EB, EC, EL, EM | EH Sez. IV `EsenzioneImpostaSuccessione/AgevolazTipoL` (numero protocollo 7-16 caratteri e data) | EG11 + EG7 |
| Q | EN, EO | EH Sez. IV `Agevolazioni/FlagQ` | EG11 + EG7 |
| R | EB, EC, EL, EM | nessuna sezione (l'XSD non ne prevede); attestazione dell'ufficio regionale allegata al quadro EG (Fasc. I p. PDF 63) nel rigo EG8 «Altro» | idem |
| F | EC, EM | nessuna sezione (XSD) | nessuna |

Dati di ingresso: `opzioni.telematico.devoluzioni[<id>] = {"agevolazioni": "L|Q|R|F", "riduzioni": "1".."5"}`,
`opzioni.telematico.beni[<id>].valore_prec_succ` (euro interi), `opzioni.telematico.dichiarazione.riduzioni_art25 =
{"dichiara_requisiti": true, "l": {"num_protocollo", "data"}, "successione_precedente": {"ufficio", "anno", "volume", "numero"}
| "donazione_precedente": {"ufficio", "serie", "numero", "sottonumero"}}`. «Dichiarante» = presentatore presente nel quadro EA
(annotazione XSD di `RiduzioniImposteSuccessione`, stessa definizione di `prima_casa.py`).

Regole applicate in esportazione (errori con fonte): codici ammessi per quadro (annotazione `Agevolazioni`); gradi di parentela per
Q, R, F (annotazione `Agevolazioni`: elenchi riportati in `riduzioni_art25.GRADI`); un'agevolazione esclusiva (A, C, D, E, L, M, N,
P, X, Y) non convive con altre sullo stesso bene (annotazione); `ValorePrecSucc` obbligatorio con `Riduzioni`, assente senza,
positivo, non superiore al valore, `Riduzioni` uguale su tutti i righi della devoluzione del bene; niente trust (tipo soggetto 5).

Regole che **non** sono scritte negli XSD o nei Fascicoli ma risultano dal controllo ufficiale SUC13 2.3.1 eseguito in locale
(citate come tali nel codice):

- numero protocollo L: 7-16 caratteri (diagnostico 3128);
- Q su terreni/fabbricati richiede il «bene aziendale» (diagnostico 3333) -> Q supportata solo in EN ed EO.

## 5. Casi positivi con esito del controllo locale (test `test_reale_*`)

Tutti: dati sintetici (`caso_a10` con la casa a 2.400.000, due figli 1/2, grado 02, franchigia 1.000.000, aliquota 4%): controllo
**positivo** (solo il diagnostico informativo 3345) e **+1/-1 sull'imposta scartati (3454)**.

| Caso | EF18bis | Calcolo a mano nel test |
|---|---|---|
| L, dichiarante (EC) | 13.384 | ISL 8.822 e 8.910; Rid.agevL = 1.200.000 x 8.822 / 1.217.500 x 0,5 |
| art. 25 codice 2 (EC), VPS 600.000 | 15.984 | r25 = 300.000 x ISL / 1.217.500; x 0,4 |
| Q (EN), azienda 1.000.000 | 54.543 | Rid.agevQ = 500.000 x ISL / 1.717.500 x 0,4 |
| R sopra soglia (EB), terreno 400.000 | 33.656 | (103.291 x ISL / 1.410.000) x 0,4 |
| R sotto soglia / F sopra e sotto soglia | vedi test | come sopra con quota 75.000 / soglia |
| art. 25 su EB, ER, EN, EO, EP, EQ, EL, EM | vedi test | formula r25 con codici 1-5 |
| L di beneficiario diverso dal dichiarante | vedi test | EG11 + EG7 |

## 6. Casi negativi con esito del controllo locale

Scartati dal componente (file modificato a partire dal positivo): ValorePrecSucc mancante (3488); maggiore del valore (3301);
`Riduzioni` su una sola riga (3489); EG11 mancante (3241); Sezione IV mancante con riduzione 1-5 del dichiarante (3248); L del
dichiarante senza Sezione IV (3243, 3290); L insieme a P sullo stesso bene (3076, 3228); Q su fabbricato (3333); protocollo L
troppo corto (3128). Rilevati prima dall'esportazione (test omonimi senza Java): valori fuori regola, codici non ammessi per
quadro, gradi non ammessi, dati EH mancanti, allegati obbligatori mancanti (`quadri_mancanti`).

## 7. Non supportati (bloccano l'esportazione o il calcolo con il motivo)

| Voce | Motivo |
|---|---|
| Codici 1-5 insieme a un'agevolazione sulla stessa riga | combinazione non descritta dalle fonti |
| Riduzione su cespiti DN o titoli esenti | la guida esclude DN dalla QE e li tratta nella QDN: nessuna formula per la riduzione |
| Piu' righe R / F per lo stesso beneficiario | la Guida applica la soglia 103.291 per riga, il Fasc. I p. PDF 63 al «valore complessivo» |
| L in ER, EP, EQ; Q in EB, EC, EL, EM, EP, EQ | l'XSD li consente ma il Fasc. I descrive L come beni immobili; Q richiede il bene aziendale (controllo 3333), non supportato |
| Bene aziendale (`BeneAziendale`, `ImmobiliAziendali`) | fuori perimetro |
| A, C, D, E, G, H, M, N | non sono riduzioni art. 25; A, C, D, E, G, H, N escludono la quota dalla QE (Guida p. 1): non implementato |
| DET.estero (imposta pagata all'estero) | invariato: dubbio 82,0875 / 82,08 aperto |
| Richiesta del dichiarante via EG11 al posto della Sezione IV | non supportato: il dichiarante compila sempre EH |
| `FlagC`, `FlagD`, `FlagE` della Sezione IV; A in `EsenzioneImpostaSuccessione` | agevolazioni non supportate |
| Importazione di un XML con ValorePrecSucc / Riduzioni / L, Q, R, F | `importa.py` non le legge (rifiuta il file, nessuna perdita silenziosa) |

## 8. Mutation testing

`python scripts/mutazioni_riduzioni_art25.py` applica 27 mutazioni (coefficienti, soglia, formule esatte e del componente, scale,
regole di esportazione, quadri, gradi, esclusivita', dichiarante/non dichiarante, allegati, limiti di valore) su una copia di
`src` ed esegue `test_telematico_riduzioni_art25.py` e `test_telematico_calcolo.py`: ogni mutazione deve far fallire almeno un test.
Esito riportato nel rapporto di consegna.
