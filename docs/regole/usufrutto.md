# Usufrutto e nuda proprietà nelle devoluzioni

Codice: `src/successioni/telematico/usufrutto.py`, usato da `esporta.py` (`_valori_diritti_distinti`). Test: `tests/test_usufrutto.py`. Testi letti il 7/11/2026.

## Caso coperto

Il defunto aveva il bene (EB o EC) in **piena proprietà** (codice 1). I beneficiari ricevono **usufrutto** (codice 08) e **nuda proprietà** (codice 02), eventualmente insieme a righe in piena proprietà.

| Regola | Fonte |
|---|---|
| Chi riceve l'intero usufrutto o l'intera nuda proprietà indica quota 1/1; codici 08 e 02 | Fascicolo I, p. PDF 24 |
| Valore quota dell'usufrutto = valore quota del defunto × quota devoluzione × saggio legale × coefficiente per età | Fascicolo I, p. PDF 25 (esempio 2025); D.Lgs. 123/2025, art. 99 c. 1 lett. c e art. 102 c. 1 lett. c |
| Valore quota della nuda proprietà = valore × quota − valore dell'usufrutto che la grava | Fascicolo I, p. PDF 25; art. 99 c. 1 lett. b |
| Saggio non inferiore al 2,5%; per il 2025 il Fascicolo indica 2,5% | art. 102 c. 3; Fascicolo I, p. PDF 25 |
| Coefficienti per età: da 0 a 20 anni 38 … da 93 a 99 anni 4 | D.Lgs. 123/2025, allegato 4 (GU n. 186 del 12/8/2025, S.O. n. 29), esteso alle successioni dal D.Lgs. 139/2024 |

**Età.** È l'età compiuta dell'usufruttuario alla data del decesso. Per questo serve la sua **data di nascita** nel quadro EA; senza, l'export si blocca e dice cosa manca.

**Più nudi proprietari.** Ognuno sottrae la parte dell'usufrutto proporzionale alla sua quota di nuda proprietà. Le quote devono coprire il bene per ogni diritto: piena + usufrutto = 1 e piena + nuda proprietà = 1.

**Arrotondamento.** Il valore quota è al centesimo, con la stessa regola delle altre righe (`docs/regole/dubbio_arrotondamento.md`).

## Prove

- Esempi del Fascicolo I riprodotti: p. 25 (47.500 / 45.000 / 7.500) e p. 31 (coefficiente 20, nuda proprietà 50.000).
- Controllo ufficiale SUC13 locale **positivo** su un caso con usufrutto 1/1 alla figlia (55 anni, coefficiente 26) e nuda proprietà 1/1 al figlio. È un controllo locale, non una verifica dell'Agenzia.

## Limiti

- **Decessi prima del 2025:** non supportati (prospetti e saggi diversi).
- **Decessi dal 2026:** il calcolo usa 2,5% e lo stesso prospetto, con l'avviso `SAGGIO_USUFRUTTO_DA_VERIFICARE`. Il decreto sul tasso legale 2026 non è stato trovato: se il tasso supera il 2,5%, un decreto aggiorna il prospetto (art. 102 c. 2).
- **Diritti non gestiti:** uso, abitazione (anche il legato ex lege del coniuge), enfiteusi, superficie, usufrutto a termine o congiunto. Restano «non supportato».
- **Quadri:** ER e i beni non immobiliari non sono gestiti.
- **Defunto titolare della sola nuda proprietà:** non gestito, e il valore catastale non è calcolato (serve l'età di un usufruttuario estraneo alla successione).
