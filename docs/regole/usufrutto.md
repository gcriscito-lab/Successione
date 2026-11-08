# Usufrutto e nuda proprietà nelle devoluzioni

Codice: `src/successioni/telematico/usufrutto.py`, usato da `esporta.py` (`_valori_diritti_distinti`). Test: `tests/test_usufrutto.py`. Testi letti il 7/11/2026.

## Caso coperto

Il defunto aveva il bene (EB o EC) in **piena proprietà** (codice 1). I beneficiari ricevono **usufrutto** (codice 08) e **nuda proprietà** (codice 02), eventualmente insieme a righe in piena proprietà.

| Regola | Fonte |
|---|---|
| Chi riceve l'intero usufrutto o l'intera nuda proprietà indica quota 1/1; codici 08 e 02 | Fascicolo I, p. PDF 24 |
| Valore quota dell'usufrutto = valore quota del defunto × quota devoluzione × saggio legale × coefficiente per età | Fascicolo I, pp. PDF 22 e 25 (esempio 2025), che rinvia all'art. 14 c. 1 lett. b-c D.Lgs. 346/1990 (TUS); stessa regola nel D.Lgs. 123/2025, art. 99 c. 1 lett. c e art. 102 c. 1 lett. c |
| Valore quota della nuda proprietà = valore × quota − valore dell'usufrutto che la grava | Fascicolo I, p. PDF 25; art. 99 c. 1 lett. b |
| Saggio non inferiore al 2,5%; per il 2025 il Fascicolo indica 2,5% | Fascicolo I, pp. PDF 25 e 34 (D.Lgs. 139/2024); D.Lgs. 123/2025, art. 102 c. 3 |
| Coefficienti per età: da 0 a 20 anni 38 … da 93 a 99 anni 4 | Prospetto allegato al TUS (D.Lgs. 346/1990), esteso alle successioni dal D.Lgs. 139/2024 (Fascicolo I pp. PDF 22, 25, 30 e 34); lo stesso prospetto è l'allegato 4 al D.Lgs. 123/2025 (GU n. 186 del 12/8/2025, S.O. n. 29) |

**Norma citata.** Per i decessi del 2025 la norma è il TUS (D.Lgs. 346/1990) come modificato dal D.Lgs. 139/2024: è quella a cui rinvia il Fascicolo I. Il D.Lgs. 123/2025 riporta gli stessi coefficienti e lo stesso saggio minimo ed è citato come conferma (revisione dell'8/11/2026).

**Età.** È l'età compiuta dell'usufruttuario alla data del decesso. Per questo serve la sua **data di nascita** nel quadro EA; senza, l'export si blocca e dice cosa manca.

**Più nudi proprietari.** Ognuno sottrae la parte dell'usufrutto proporzionale alla sua quota di nuda proprietà. Le quote devono coprire il bene per ogni diritto: piena + usufrutto = 1 e piena + nuda proprietà = 1.

**Arrotondamento.** Il valore quota è al centesimo, con la stessa regola delle altre righe (`docs/regole/dubbio_arrotondamento.md`). L'avviso `ARROTONDAMENTO_VALORE_QUOTA` indica la regola del diritto (usufrutto: valore × quota × saggio × coefficiente; nuda proprietà: valore × quota meno l'usufrutto che la grava), non il semplice valore × quota.

**Solo per testamento o legge estera.** Con la devoluzione per legge (senza testamento e con «legge estera» = 0) i codici diritto della sezione devoluzione devono coincidere con quello del defunto (annotazione XSD di `CodiceDiritto_Rip`, `fornituraSUC13_v1.xsd`): usufrutto e nuda proprietà distinti sono un errore `REGOLA_CODICE_DIRITTO`, come la riga con il diritto di abitazione (codice 3). Prima di questa regola il file risultava completo ma il controllo ufficiale lo scartava con 6 errori (codice diritto, quote di legge, valore quota; `docs/archivio/REVIEW_COMPLETA_20261107_SERA.md`, punto 1).

**Imposta estera.** Un immobile estero con imposta versata all'estero e diritti distinti è «non supportato»: la detrazione (imposta estera × quota di devoluzione, guida al calcolo pp. 7-8) conterebbe l'imposta una volta per ciascun diritto (quote 1/1 + 1/1) e le fonti non indicano il riparto.

**Importazione.** Ogni `QuotaValore` del file importato è confrontato con quello della riesportazione: oltre il centesimo c'è un avviso con i due valori, per bene e beneficiario.

## Prove

- Esempi del Fascicolo I riprodotti: p. 25 (47.500 / 45.000 / 7.500) e p. 31 (coefficiente 20, nuda proprietà 50.000).
- Controllo ufficiale SUC13 locale **positivo** su un caso con usufrutto 1/1 alla figlia (55 anni, coefficiente 26) e nuda proprietà 1/1 al figlio. È un controllo locale, non una verifica dell'Agenzia.
- Devoluzione per legge: la variante 8/2 è bloccata (`REGOLA_CODICE_DIRITTO`); lo stesso caso con codice 1 e quote di legge è positivo al controllo ufficiale locale (`test_controllo_ufficiale_per_legge_codici_coincidenti`).

## Limiti

- **Decessi prima del 2025:** non supportati (prospetti e saggi diversi).
- **Decessi dal 2026:** il calcolo usa 2,5% e lo stesso prospetto, con l'avviso `SAGGIO_USUFRUTTO_DA_VERIFICARE`. Il decreto MEF sul tasso legale 2026 non è nelle fonti del progetto: se il tasso supera il 2,5% il saggio e il prospetto cambiano. **Da confermare con il professionista** prima di usare il programma per decessi del 2026; finché non c'è, l'avviso resta.
- **Diritti non gestiti:** uso, abitazione (anche il legato ex lege del coniuge), enfiteusi, superficie, usufrutto a termine o congiunto. Restano «non supportato».
- **Quadri:** ER e i beni non immobiliari non sono gestiti.
- **Defunto titolare della sola nuda proprietà:** non gestito, e il valore catastale non è calcolato (serve l'età di un usufruttuario estraneo alla successione).
