# Pagamenti: crediti d'imposta, rimborsi, sanzioni e interessi (Pacchetto 9)

Codice: `src/successioni/telematico/pagamenti.py` (regole), ganci minimi in `telematico/quadri_efgh.py` (EF, `_sezione_vbis`, `quadro_eh`, `quadro_eg`).
Test: `tests/test_pagamenti_crediti.py`. Fonti: XSD `fornituraSUC13_v1.xsd` (annotazioni di `CreditoImposta`, `SezioneIII_CreditoImposta`,
`SezioneVI_SanzioniInteressi`, `ImportoDaVersare`), Fascicolo I (pp. PDF 41-44, 47-49), controllo ufficiale SUC13 2.3.1 eseguito in locale
(arbitro: se il controllo dissente dalla lettura delle fonti, vince il controllo).

## 1. Crediti d'imposta

| Rigo | Campo XML | Chiave della dichiarazione | Regola |
|---|---|---|---|
| EF7 | `SezioneI_ImpostaIpotecaria/CreditoImposta` | `credito_ipotecaria` | EF8 = EF5 - EF6 - EF7, minimo 0 |
| EF13 | `SezioneII_ImpostaCatastale/CreditoImposta` | `credito_catastale` | ammesso solo se EF5 - EF6 - EF7 <= 0 (cioe' l'ipotecaria e' azzerata) e non oltre l'importo dovuto |
| EF18bis col. 4 | `SezioneVBis_ImpostaSuccessione/ImpostaCalcolata/CreditoImposta` | `credito_successione` | solo decesso dal 1/1/2025 e solo se EF11 - EF12 - EF13 = 0 (catastale azzerata); `ImpostaDaVersare` = imposta - versata - credito |

Il credito si scomputa nell'ordine ipotecaria -> catastale -> successione, come dice l'XSD. Ogni credito richiede la **sezione III del quadro EH**
e il rigo **EG8 «Altro»** (dichiarazione sostitutiva di atto di notorieta' con i requisiti del credito, Fascicolo I p. 42): senza, la pratica non e'
completa (`quadro[EG].Altro`).

Sezione III di EH (`credito_tipologia`, `credito_imposta`, `credito_acquisto.*`, `credito_vendita.*`, e le stesse con suffisso `_2`):
- tipologia 1 (registro) o 2 (IVA): servono **due righi** di acquisti (il primo nel primo modulo con la firma, il secondo nel `Modulo[0]`). Lo ha
  imposto il controllo (messaggio **3386**, «almeno 2 righi di acquisti»), non il testo dell'XSD;
- tipologia 3: un solo rigo;
- la registrazione di vendita e' facoltativa e non puo' precedere quella di acquisto;
- il credito scomputato in EF non puo' superare la minore delle imposte pagate indicate.

Evidenza: il controllo ufficiale accetta credito su EF7 (con e senza vendita), EF7 + EF13, azzeramento di entrambe, tipologia 3 e credito fino
all'imposta di successione (EF7 2820, EF13 1410, EF18bis col. 4 1000 -> `ImpostaDaVersare` 21396, `TotaleDaVersare` 21601,00). Respinge le
alterazioni: EF7 non scalato in EF8, secondo rigo di acquisto mancante (3386).

## 2. Rimborsi nelle dichiarazioni sostitutive

Il modello non ha un campo «rimborso»: l'eccedenza si esprime con i righi esistenti.
- **Imposta di successione**: `ImpostaVersata` non puo' superare l'imposta calcolata (annotazione XSD). Il programma limita il versato all'imposta
  e segnala `ECCEDENZA_IMPOSTA_VERSATA_DA_RIMBORSARE` (avviso) con l'importo da chiedere a rimborso.
- **Ipotecaria e catastale**: l'importo da versare resta 0 (EF8/EF14 non negativi) e l'avviso riporta l'eccedenza.
- Lo scomputo dell'eccedenza fra tributi **non e' definito dall'XSD**: non e' implementato.

## 3. Sanzioni e interessi (Sezione VI di EF)

Le fonti non contengono il tasso di interesse legale ne' la misura delle riduzioni del ravvedimento: **il professionista indica gli importi**
(`sanzione_<tributo>`, `interessi_<tributo>` con tributo = `successione`, `ipotecaria`, `catastale`, `tassa_ipotecaria`, `bollo`), con due decimali.
Il programma non li calcola.
- EF24 col. 1 e col. 2 = somme delle colonne; `TotaleDaVersare_Sanzioni` coerente.
- `QuadroEF/TotaleDaVersare` (EF19) **non** include le sanzioni; `Frontespizio/ImportoDaVersare` = EF19 + EF24 (messaggio **3376** del controllo).
- Sanzioni/interessi su un tributo senza «da versare» sono un errore (`DATI_INCOERENTI`).
- Sanzioni sull'imposta di successione solo con `tempistica_pagamento = 2` (pagamento contestuale).

### Dichiarazioni tardive (Fascicolo I p. 48)
Termine = 12 mesi dal decesso. Entro i 90 giorni successivi al termine e' ammesso il codice 1 (imposta pagata nei termini ordinari); oltre,
serve il codice 2. Una tardiva oltre i 90 giorni **si esporta** se il professionista dichiara sanzioni e interessi (anche 0,00 dichiarato), altrimenti
resta bloccata con la richiesta di indicarli; con tempistica 1 oltre i 90 giorni e' un errore (`tempistica_pagamento`). Se i dati sono dichiarati
l'avviso `EF_TARDIVA_SANZIONI_NON_CALCOLATE` non compare.

## 4. Verifica col controllo ufficiale (2026-11-06, dati sintetici)

Positivi (solo diagnostico 3345, non bloccante): credito EF7 con vendita; EF7+EF13; azzeramento ipocatastali; tipologia 3; credito su successione;
sanzioni ipocatastali (decesso 2024); tardiva con successione e sanzioni; tardiva entro 90 giorni con tempistica 1; sanzioni su tassa ipotecaria e
bollo; sostitutive con successione e ipotecaria versata oltre il dovuto.
Negativi: EF7 incoerente con EF8; secondo rigo EH III assente (3386); `ImportoDaVersare` senza EF24 (3376); totale sanzioni alterato.

## 5. Limiti dichiarati

- Credito richiesto da un beneficiario diverso dal dichiarante: non coperto.
- Al massimo due righi di credito (`_2`).
- Tasso legale e riduzioni del ravvedimento non calcolati (importi dichiarati dal professionista).
- Il controllo facoltativo di coerenza di p. 49 (sanzione attesa) non e' implementato.
- Decorrenze particolari del termine (art. 31 d.lgs. 346/90 per assenza, ecc.) non coperte.
- Scomputo dell'eccedenza fra tributi non definito dall'XSD.
