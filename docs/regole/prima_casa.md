# Agevolazione «prima casa» (codici P, X, Z): regole, fonti, perimetro

Codice: `src/successioni/telematico/prima_casa.py` (+ ganci in `esporta.py`, `quadri_efgh.py`, `calcolo.py`).
Test: `tests/test_telematico_prima_casa.py` (casi in `tests/telematico_casi.py`). Pagine = pagine del file PDF
(`Succ_FASCICOLO_I_Nov_23.pdf`); XSD = `fornituraSUC13_v1.xsd` (SUC13_20250702).

## Dati di ingresso (supplemento `opzioni.telematico`)
- `devoluzioni[<id>].agevolazioni`: `"P"`, `"X"` o `"Z"` sulla riga di devoluzione del soggetto che chiede il beneficio.
- `dichiarazione.prima_casa` (solo se il dichiarante chiede P): `dichiara_requisiti` (true), `requisito_comune`
  (`residenza` | `attivita` | `stabilire_residenza`), `nessuna_altra_casa_comune` (true), `altra_casa`
  (`nessuna` | `vendita`), `impegno_unione_catastale` (true, obbligatorio con Z).

## Regole implementate e fonte
| Regola | Fonte |
|---|---|
| P, X, Z solo nella devoluzione dei quadri EC, EM (altrove: errore); EM non supportato | XSD, annotazione `DevoluzioneImmobili_Type/Agevolazioni` |
| P: un solo immobile per soggetto; X solo se lo stesso soggetto ha P; una X per categoria C/2, C/6, C/7 | XSD stessa annotazione; Fascicolo I p. 26 («un solo immobile abitativo»), p. 26-27 (pertinenze) |
| P e Z: casa di abitazione con categoria diversa da A/1, A/8, A/9 (A/1, A/8, A/9: errore; altre categorie diverse da A/2-A/7: non supportato, le fonti non le classificano) | Fascicolo I p. 60, Allegato 2 |
| X: categoria C/2, C/6 o C/7 | Fascicolo I p. 26-27 |
| Z solo con P dello stesso soggetto (un solo Z, solo del dichiarante) | Fascicolo I p. 26; XSD `SezioneII_AgevPrimaCasa/ImmobileContiguo`, `FlagContigui` |
| Un solo codice per riga; l'agevolazione si estende a tutti i beneficiari del bene | XSD annotazioni `PrimaCasa/AgevolazionePX_Valore`, `ImpostaProporzionale`; Fascicolo I p. 26 |
| EF4 col. 1: numero di immobili con P (X non si conta; Z conta solo in assenza di P) | XSD `PrimaCasa/PrimaCasa_Numero`; Fascicolo I p. 41 |
| EF4 col. 2: somma dei «Valore quota» di tutti i beneficiari dei beni agevolati | XSD `PrimaCasa/AgevolazionePX_Valore`; Fascicolo I p. 41 |
| EF4 col. 3: numero x 200 euro; EF5 = EF1 + EF4 col. 3 | XSD `PrimaCasa_Imposta`, `ImpostaIpotecariaDovuta`; Fascicolo I p. 41 |
| EF10 = EF4 col. 3 (`ImpostaCatastaleFissa`); EF11 = EF9 + EF10 | XSD `ImpostaCatastaleFissa`, `ImpostaCatastaleDovuta`; Fascicolo I p. 43 |
| I beni agevolati escono dalle basi EF1 ed EF9 | XSD `ImpostaProporzionale` (Sezioni I e II); Fascicolo I p. 40 e 43 |
| Nessun effetto su EE e sull'imposta di successione (P, X, Y, Z non escludono quote dalla QE e non sono riduzioni) | Guida al calcolo p. 1 e p. 5; Fascicolo I p. 57 (quadro sinottico) |
| Sezione II del quadro EH del dichiarante: immobile principale, contiguo, pertinenze (dati uguali al quadro EC), opzione a, dichiarazioni b e c/d, impegno i (con Z), firma | XSD `SezioneII_AgevPrimaCasa`; Fascicolo I p. 52; modello EH14-EH18 (`fonti/Istruzioni/Modello Successione (1).pdf`) |
| Beneficiario diverso dal dichiarante: richiesta al rigo EG9 (PrimaCasa) e documento d'identita' (EG7), altrimenti il quadro risulta incompleto | XSD `QuadroEG/PrimaCasa`; Fascicolo I p. 7 e p. 52 |
| Se EF1/EF9 restano (beni non agevolati) l'imposta proporzionale inferiore alla fissa blocca come prima | invariato: fonti non concordi (Fascicolo I p. 40 e 43 / annotazioni XSD) |

Corrispondenza nome XSD - dichiarazione del modello EH (dedotta dall'ordine e dal nome degli elementi, **non** da una
tabella esplicita delle fonti): `FlagComuneResidenza`/`FlagComuneAttivita`/`FlagCambioResidenza` = scelta a;
`FlagNessunaAltraCasaComune` = b; `FlagNessunaAltraCasa` = c; `FlagVenditaAltraCasa` = d; `FlagContigui` = i.
Il controllo ufficiale verifica la presenza ma non il significato: va riletta in sede di collaudo.

## Non supportato (blocca l'esportazione con il motivo)
Codice Y; Z senza P dello stesso soggetto o di soggetto diverso dal dichiarante; quadro EM (il diritto di abitazione del
coniuge, `DirittoAbitazione` 1-8, e' coperto: `docs/regole/diritto_abitazione.md`); requisiti per trasferiti all'estero, forze armate, residenti all'estero (altre scelte
di `Opzioni`, `FlagTrasferimentoPrima`, ...); evento eccezionale cod. 1; credito d'imposta (Sezione III); combinazioni
con altre agevolazioni o riduzioni; piu' comuni (come prima); categorie diverse da A/2-A/7 per P e Z.
