# Valore catastale di fabbricati e terreni

Codice: `src/successioni/valore_catastale.py`. Test: `tests/test_valore_catastale.py`. Testi letti il 7/11/2026.

## Cosa fa il programma

- Per ogni fabbricato (EC) e terreno (EB) **propone** il valore catastale della quota del defunto, con la formula e le fonti.
- Questo è il valore minimo che l'ufficio non può rettificare. **Il valore dichiarato resta quello inserito dal professionista**: il valore venale può essere più alto.
- Se il valore dichiarato è più basso, la verifica della pratica dà un avviso `VALORE_SOTTO_CATASTALE`. È un avviso, non un blocco.
- **Interfaccia:**
  - il pannello della riga mostra il calcolo e il pulsante «Usa il valore catastale»;
  - «Ricalcola valori catastali» (quadri EB/EC) riempie solo i valori mancanti o più bassi, chiede conferma e lascia da salvare.
- **MCP:** lo strumento `successioni_valori_catastali` è in sola lettura.

## Regole e fonti

| Regola | Fonte |
|---|---|
| Rendite catastali urbane rivalutate del 5% | L. 662/1996, art. 3, c. 48 (Normattiva, vigente al 07/11/2026) |
| Redditi dominicali rivalutati del 25% | L. 662/1996, art. 3, c. 51 |
| Le rivalutazioni valgono per le successioni aperte dal 1/1/1997 | L. 662/1996, art. 3, c. 52, lett. b |
| Moltiplicatori: terreni 90; gruppo B 168; C/1 e gruppo E 40,80; A/10 e gruppo D 60; abitazioni prima casa 110; altre abitazioni e altre categorie 120 | Per i decessi fino al 2026: art. 34 c. 5 D.Lgs. 346/1990 e art. 52 c. 4 DPR 131/1986 con le rivalutazioni elencate sotto. Dal 1/1/2027: D.Lgs. 5/8/2026 n. 141, art. 309, c. 6 (GU n. 181 del 6/8/2026, S.O. n. 28, p. 267), che li riunisce senza modifiche |
| Prima casa (110) solo per le categorie del gruppo A diverse da A/1, A/8, A/9 (escluse dall'agevolazione, come in `telematico/prima_casa.py`) e A/11; A/10 ha già il suo moltiplicatore (60) | revisione dell'8/11/2026 |
| Esclusi i terreni con destinazione edificatoria | art. 309, c. 8 |
| La prima casa chiesta da un beneficiario si estende agli altri | Fascicolo I, p. PDF 26 |
| Anche la casella «Diritto di abitazione» del fabbricato con i codici 1, 2, 5, 6 (prima casa sull'immobile principale o contiguo) vale come prima casa per il bene: «L'agevolazione, qualora richiesta, si estende anche alle quote dell'immobile spettanti agli altri beneficiari» | Fascicolo I, pp. PDF 31-32, «Diritto di abitazione», N.B. |

**Validità nel tempo.** Il D.Lgs. 141/2026 si applica dal 1/1/2027 (art. 368). L'art. 309 è compilativo: la sua sotto-rubrica elenca le norme da cui riprende i valori, cioè:
- art. 34 D.Lgs. 346/1990;
- art. 52, c. 4, DPR 131/1986;
- art. 2, c. 63, L. 350/2003 (+10% per la prima casa);
- art. 1-bis, c. 7, D.L. 168/2004 (+20% per gli altri);
- art. 2, c. 45, D.L. 262/2006 (+40% per il gruppo B).

Le note di Normattiva sull'art. 52 DPR 131/1986 confermano queste rivalutazioni (lette il 7/11/2026). Per questo i moltiplicatori valgono anche per le successioni aperte prima del 2027. Il calcolo si fa per i decessi **dal 1/1/2007**: prima del D.L. 262/2006 il gruppo B aveva un altro moltiplicatore, e quelle date non sono gestite.

**Da collaudare.** Le basi 75/100 dell'art. 52 c. 4, con le rivalutazioni, danno 90, 120, 110 e 168. I moltiplicatori 60 (A/10, D) e 40,80 (C/1, E) li ho letti solo nel testo unico 2026: la loro base nel testo previgente non l'ho riletta riga per riga.

## Casi non calcolati (con il motivo mostrato)

- **Diritto diverso dalla piena proprietà** (codice 1). Per nuda proprietà e diritti reali l'art. 309 c. 7 rinvia all'art. 99 del testo unico registro (D.Lgs. 123/2025), da implementare con il modulo usufrutto. Per questi beni il valore dichiarato non è confrontato con un minimo.
- **Pertinenze della prima casa** (C/2, C/6, C/7 con agevolazione X): oggi moltiplicatore 120. L'estensione del 110 alle pertinenze non è nelle fonti del progetto: **da confermare con il professionista** prima di cambiarla.
- **Categorie del gruppo F** o categoria mancante: nessuna rendita.
- **Terreni edificabili o parzialmente edificabili** (tipologia 1 o 2), nature diverse da T/R.
  - Se la tipologia manca, il valore si calcola con l'avviso di verificare che il terreno non sia edificabile.
- **Immobili all'estero** (provincia EE).
- **Successioni aperte prima del 2007.**
- **Dati mancanti**: rendita, reddito dominicale, quota del defunto, data del decesso.

## Arrotondamento

Il valore è arrotondato **all'euro per eccesso**, perché la norma chiede un valore dichiarato «non inferiore». Esempio: 333,33 × 1,05 × 120 / 3 = 13.999,86 → 14.000.
