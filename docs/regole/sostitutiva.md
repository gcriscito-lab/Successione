# Dichiarazione sostitutiva (codici 1 e 2)

Implementazione: `src/successioni/telematico/sostitutiva.py`; prove: `tests/test_sostitutiva.py`.

## Fonti
- `fornituraSUC13_v1.xsd`: `Frontespizio/TipoDichiarazione` (scelta `PrimaDichiarazione` | `DichiarazioneSostitutiva` + `EstremiPrimaDichiarazione`), annotazioni di `DataDecesso`, `ImpostaIpotecariaVersata`, `ImpostaCatastaleVersata`, `ImpostaCalcolata/ImpostaVersata`, `Circoscrizioni_Numero`.
- Fascicolo I (Nov 2023), pp. PDF 11-13 (tipo di dichiarazione, codici 1/2/3, estremi) e 42-47 (righi EF6, EF8, EF12, EF14, EF15, EF16, EF18bis col. 3).

## Regole applicate
- La sostitutiva sostituisce integralmente la precedente: contiene tutti i quadri, non solo le modifiche.
- Estremi della prima dichiarazione: anno >= 2014 e >= anno del decesso; **volume 88888 o 88889** (annotazione XSD; il controllo ufficiale locale scarta ogni altro valore); numero di sole cifre, al massimo 6.
- EF6 / EF12 / EF18bis col. 3: imposte gia' versate (euro interi).
- Codice 1: l'imposta ipotecaria e catastale da versare, se dovuta, non e' inferiore a 200 euro; sezioni III e IV (circoscrizioni delle nuove trascrizioni) compilate.
- Codice 2: sezioni III e IV non compilate.
- Imposta di successione (V-bis): ricalcolata su tutti i dati della dichiarazione; da versare = imposta - gia' versata (zero se <= 10 euro).

## Campi (`opzioni.telematico.dichiarazione`)
`codice_sostitutiva` (1|2), `prima_anno`, `prima_volume`, `prima_numero`, `ipotecaria_versata`, `catastale_versata`, `successione_versata`; con `opzioni.tipo_dichiarazione = "sostitutiva"`.

## Limiti
- Codice 3 (solo frontespizio ed EG): NON supportato, nessun XML.
- Imposta gia' versata superiore alla riliquidata (rimborso): non coperto.
- Tardive con imposta aggiuntiva, sanzioni e interessi: non coperti.
- Immobili in piu' comuni (conservatorie): non coperti.

## Evidenza
Controllo ufficiale SUC13 2.3.1 eseguito in locale il 2026-11-05: esito positivo per i codici 1 e 2 su dati sintetici. Non e' un invio ne' una verifica con l'Agenzia.
