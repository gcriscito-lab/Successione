# Matrice di copertura SUC13 (area 1: XML, regole, calcolo)

Aggiornata il 2026-11-01 dopo le correzioni CE01-CE10 (docs/CORREZIONI_CODEX.md).
Collaudo aggiuntivo 2026-11-02: controllo ufficiale locale Windows, export dal pacchetto con allegati PDF/A
validati da veraPDF; evidenze e limiti in `docs/COLLAUDO_WINDOWS_CODEX_20261102.md`.
Proprieta' dell'area 1 (docs/CONTRATTI_MODULI.md). Stati:

- **implementato-collaudato**: superato il collaudo nell'ambiente ufficiale (Desktop Telematico/servizi). *Nessuna voce.*
- **controllo locale**: il caso documentato supera il controllo ufficiale SUC13 2.3.1 eseguito in locale (batch, dati
  sintetici, 2026-11-01): Frontespizio, EA, EB, EC, ED, EE, EF, EG, EH, ER nel perimetro del caso A10.
- **implementato**: implementato e coperto da test locali (schema XSD e regole interne).
- **parziale**: implementato solo per una parte dei casi; il resto blocca l'export (`non_supportato`).
- **non coperto**: non implementato; se la pratica lo richiede l'XML non viene prodotto.

Test: `tests/test_telematico_xsd.py` (X), `tests/test_telematico_esporta.py` (E), `tests/test_telematico_calcolo.py`
(C). Casi sintetici in `tests/telematico_casi.py`. Comando: `python3 -m pytest -q tests/test_telematico_*.py`.
Regole e fonti dettagliate: `docs/regole/mappa_xsd.md`; albero completo: `docs/regole/mappa_xsd_albero.md`.

## Sintesi per quadro

| Quadro | Stato | Coperto | Non coperto (blocca l'export) |
|---|---|---|---|
| Busta / Intestazione | implementato | Messaggio, CodiceFiscaleFornitore, CodiceFornitura SUC13, TipoFornitore 1/10, SpazioUtente, identificativo | SpazioServizioTelematico (riservato al servizio) |
| Frontespizio | parziale | CF defunto, prima dichiarazione, devoluzione per legge, Beneficiari (conteggi), dati defunto, stato civile, presentatore con carica 1, telefono/email, caselle quadri, firma, impegno a trasmettere | sostitutive/integrative, testamento, legge estera, eventi eccezionali, data opzione, beneficio d'inventario, residenza estera, cariche 2-9, rappresentato, casi particolari, Versamento/F24, ImportoDaVersare, campi servizio, lingua |
| EA | parziale | eredi (1) e chiamati (3) persone fisiche, grado di parentela, persona con disabilita', moduli da 3 | legatari (2), rinunciatari (4), trust (5), altro (6), rinuncia, denominazione (enti), residenza estera, rappresentazione, soggetto su piu' righi |
| EB | parziale | terreni in Italia non tavolari, natura T, superficie, reddito dominicale, possesso, diritto, tipologia, valore, devoluzione con continuazione | estero (EE), nature diverse da T, bene aziendale, discordanza/passaggi (EI), imposta estera, valore precedenti successioni, agevolazioni/riduzioni |
| EC | parziale | fabbricati in Italia non tavolari, sezione, zona, categoria, classe, consistenza, rendita, possesso, diritto, valore, devoluzione con continuazione | estero, rendita proposta (DeterminazioneRendita), D10 senza valore, bene aziendale, graffati, diritto di abitazione, EI, imposta estera, agevolazioni (prima casa P/Z/X/Y ecc.) |
| ED | parziale | tipo, descrizione, estremi e data documento, possesso, valore, progressivo cespite (tipi 3/4/5/7), ripartizione a un soggetto | tipo 11 (legati/oneri), continuazione oltre 3 soggetti. La ripartizione fra 2-3 soggetti e' implementata via `opzioni.telematico.passivita[id].ripartizione` (esporta.py `ripartizione_ed`; test in `tests/test_telematico_controllo.py`); dalla GUI/MCP il campo `persona_id` resta singolo (corretto 2026-11-02) |
| EE | implementato | EE1, EE5, EE6, EE7, EE8 calcolati dai quadri esportati | EE2-EE4 (dipendono da EN, EO, EP, EQ non coperti); esclusioni per agevolazione A e bene aziendale (non presenti nel perimetro) |
| EF | parziale - **controllo locale** (caso A10: nessuno scarto) | Sez. I 2%, II 1%, III 120/circoscrizione, IV 85/circoscrizione (un solo comune), V-bis da `calcolo` (non dovuta o imposta con tempistica 1/2), EF19, ImportoDaVersare e Versamento nel frontespizio (Fascicolo I pp. 39-48; annotazioni EF) | agevolazioni, soli terreni, proporzionale < fissa, piu' comuni, copia conforme, crediti, sostitutive, sanzioni, rateazione -> `quadri_mancanti`/`non_supportato` |
| EG | parziale - **controllo locale** | EG1, EG5, EG6, EG7, EG8 con ImageData da `documenti/base64.dati_file_attachment`; obbligatorieta' albero (EA), passivita' (ED), documento d'identita' (fornitore diverso) | testamento, inventario, estero, agevolazioni/riduzioni; PDF/A non verificato dall'export |
| EH | parziale - **controllo locale** | Sezione I: presentatore, defunto deceduto, dichiarante carica 1, eredi EA, assenza testamento/interdetti/rinunce, FlagPassivita confermato, firma | sezioni II-IV, separazione, unione civile, disabili/interdetti, rinunce, morte presunta |
| EI_new | non coperto | — | voltura: discordanze e passaggi intermedi |
| EL, EM | non coperto | — | sistema tavolare (province tavolari rilevate e bloccate) |
| EN, EO, EP, EQ | non coperto | — | aziende, titoli, aeromobili, navi |
| ER | parziale | tipi cespite BI, CR, DN, AB; descrizione; possesso; diritto 1/2; valore; devoluzione con continuazione; moduli da 4 | GD, CR senza valore, beni esteri, imposta estera, valore precedenti successioni, agevolazioni A/L |

Il caso sintetico nel perimetro coperto puo' ottenere `completo=True` dal modulo, dal servizio/API,
dal processo MCP e dalla GUI, con allegati e profilo intermediario. EF, EG ed EH sono parzialmente presenti.
`completo` descrive la copertura interna: non attesta conformita' PDF/A, accettazione dell'Agenzia o idoneita'
all'uso professionale. Le configurazioni di quote non verificate e le tardive con imposta di successione
dovuta bloccano il completo. Con `scopo='bozza_tecnica'` resta possibile una bozza esplicitamente incompleta
se i dati sono validi allo schema; errori dimensionali impediscono anche la produzione della bozza.

## Dettaglio campo / regola / caso / test

| Quadro | Campo / regola | Fonte | Caso | Test | Stato |
|---|---|---|---|---|---|
| Busta | ordine, namespace, tipi da XSD; UTF-8 | XSD; Specifiche p. 6 | caso completo | X `test_xml_sintetico_valido`; E `test_contenuto_e_totali_ee` | implementato |
| Busta | determinismo, stabilita' al riordino delle righe | specifica §5, §8 | liste rimescolate 5 volte | E `test_determinismo`, `test_id_stabili_al_riordino_righe` | implementato |
| tutti | validazione XSD con XPath, messaggio e fonte | XSD SUC13_20250702 | importo con decimali, codice fuori enumerazione, ordine errato, elemento mancante, XML malformato | X `test_errore_predisposto_*`, `test_elemento_obbligatorio_mancante`, `test_xml_non_ben_formato` | implementato |
| tutti | nessuna perdita silenziosa (`non_supportato`, avvisi per campi interni) | contratto area 1 | EG, legatario, diritto diverso, tavolare, chiave ignota, testamento, quadro EF attivo | E `test_casi_non_supportati_non_esportano`, `test_contenuto_e_totali_ee` | implementato |
| tutti | mappa id -> quadro/modulo/rigo/XPath; errori XSD ricondotti all'id | specifica §5 | caso completo | E `test_mappa_xpath_risolvibili_e_coerenti`, `test_riferimento_errori_xsd_alla_mappa` | implementato |
| Frontespizio | data decesso > 02/10/2006, >= nascita | annotazione DataDecesso | decesso 2006-10-01 | E `test_regole_annotazioni_frontespizio_ea` | implementato |
| Frontespizio | presentatore in EA con carica 1; diverso dal defunto; telefono o email | annotazioni Presentatore | presentatore = erede via riferimento | E `test_caso_sintetico_completo…`, `test_presentatore_e_impegno` | implementato |
| Frontespizio | impegno a trasmettere solo con TipoFornitore 10 e fornitore diverso | annotazione ImpegnoATrasmettere | intermediario | E `test_presentatore_e_impegno` | implementato |
| Frontespizio | firma confermata esplicitamente | XSD FirmaDichiarante | firma falsa | E `test_errori_dati_leggibili_con_percorso_e_fonte` | implementato |
| EA | gradi ammessi per legge; coniuge unico e coerente con stato civile | annotazione GradoParentela | cognata per legge; coniuge con defunto vedovo | E `test_regole_annotazioni_frontespizio_ea` | implementato |
| EA | moduli da 3 soggetti | XSD Soggetto maxOccurs 3 | 4 eredi | E `test_continuazione_oltre_tre_devoluzioni…` | implementato |
| EA | ogni soggetto con almeno una devoluzione | annotazione Soggetto | — | regola in `esporta` | implementato |
| EB/EC/ER | devoluzione: somma quote 1/1, beneficiario EA, nessun duplicato con stesso diritto | annotazioni Devoluzione | quota 1/3 + 1/2; devoluzione mancante | E `test_errori_dati…`, `test_quote_devoluzione…` | implementato |
| EB/EC/ER | valore quota = valore × quota (diritto uguale); centesimo HALF_UP entro tolleranza 1%/100 € | Fascicolo I p. PDF 24; annotazione QuotaValore | 1/3 e 2/3 di 20.000 | E `test_contenuto_e_totali_ee`; X `test_formati` | implementato |
| EB/EC/ER | valore quota con diritto diverso dal defunto (usufrutto, nuda proprieta') | Fascicolo I p. PDF 24-27 | usufrutto devoluto | E `test_casi_non_supportati…` | non coperto |
| EB/EC/ER | continuazione oltre 3 devoluzioni | annotazione Continuazione | 4 eredi su un fabbricato | E `test_continuazione…` | implementato |
| EB/EC | valore = base imponibile della quota del defunto, euro interi (inserito) | Fascicolo I p. PDF 22, 30 | decimali rifiutati | E `test_errori_dati…` | implementato (il calcolo del valore catastale da rendita NON e' implementato) |
| EB/EC/ER | quote di legge dell'Allegato 5 | Fascicolo I p.69, Allegato 5; annotazione Quota | figli, coniuge, coniuge e figli; germano/unilaterale non coperto | test quote esistenti; `test_ce03_quote_non_verificate_non_finalizzabili_ma_bozza_con_avviso` | parziale; configurazioni non verificate bloccano il completo |
| EC | consistenza solo A/B/C; rendita obbligatoria salvo F; indirizzo obbligatorio | annotazioni DatiFabbricati, Luogo | caso completo | E `test_caso_sintetico…` | implementato |
| ED | progressivo cespite per tipi 3/4/5/7; spese funerarie <= 1033 | annotazioni ED | mutuo collegato al fabbricato | E `test_contenuto_e_totali_ee` | implementato |
| EE | totali = somme; asse netto | annotazioni QuadroEE | caso completo | E `test_contenuto_e_totali_ee` | implementato |
| EF/EG/EH | obbligatorieta' e compilazione nel caso coperto; contesto applicativo con allegati e impegno | annotazioni QuadroEF, EG, EH; Fascicolo I pp.49,51 | caso sintetico tempestivo, dichiarante/intermediario | test A10; `test_ce01_export_completo_da_servizio_e_api`; test MCP CE01; GUI `runExport` | parziale; passato localmente sui casi indicati, servizi reali da collaudare |
| EF | tempistica con imposta dovuta; tardive non finalizzabili | Fascicolo I pp.6,48 | tardiva con codici 1/2; tempestiva con imposta 44.132 | `test_ce04_*` | parziale; nessun ravvedimento o decorrenza particolare automatizzati |
| EG/fornitura | limite 5 MB/allegato, 40 MB compressi sull'XML | Specifiche SUC13 pp.3,7 | allegato oltre 6 MB; soglia fornitura ridotta nel test | `test_ce05_*`; test dimensioni esistenti | implementato localmente con byte decimali e stima DEFLATE dichiarata; algoritmo del canale reale da collaudare |
| Calcolo | QE, QDN, QP, AN, FR, QN, PR, QTI, AL, ISL, ISN, totale | guida pp. 1-8 | esempio della guida (fratelli) senza L ed estero | C `test_esempio_guida_senza_riduzioni_ne_estero` | implementato |
| Calcolo | franchigie: linea retta, fratelli, disabilita' (la piu' alta) | guida pp. 3-4 | figli sotto franchigia; cugino con disabilita' | C `test_caso_sintetico_figli_sotto_franchigia`, `test_franchigia_disabilita_e_presunzione_esclusa_con_beni_inventariati` | implementato |
| Calcolo | presunzione su denaro/gioielli/mobilia, esclusa per legatari e con BI | guida p. 4 | esempio guida; cespite BI | C `test_esempio_guida…`, `test_franchigia_disabilita…` | implementato (ramo legatario senza test: i legatari non sono esportabili) |
| Calcolo | politica di arrotondamento; divergenza | guida pp. 7-8; componente ispezionato | cugini 150.159 (9.910 / 9.911) | C `test_divergenza_aperta…` | parziale (vedi docs/regole/dubbio_arrotondamento.md) |
| Calcolo | decorrenza: solo successioni dal 2025-01-01 | guida p. 1; Fascicolo I p. PDF 46 | decesso 2024-12-31 | C `test_decesso_anteriore_al_2025_non_supportato` | implementato (rifiuto esplicito) |
| Calcolo | riduzioni art. 25, agevolazioni L/Q/R/F, DET.estero | guida pp. 5-8 | agevolazione L nel file | C `test_agevolazioni_nel_file_non_supportate` | non coperto |
| Calcolo | qualifiche multiple (franchigia unica), trust, rinunce | guida p. 3; Fascicolo I p. PDF 46 | — | regola in `calcolo` | non coperto |

## Prove di accettazione della specifica (§12) che toccano l'area 1

| ID | Stato area 1 | Evidenza / mancanza |
|---|---|---|
| A05 Quote e continuazioni | parziale | numeratori/denominatori esatti, continuazioni EB/EC/ER, moduli EA; configurazioni di quote non verificate bloccate; diritti diversi non coperti |
| A06 Franchigie e DN/BI | parziale | franchigie e presunzione da guida; qualifiche multiple non coperte |
| A07 Decorrenze | parziale | solo regime dal 2025; pre-2025 e tardive con imposta dovuta rifiutati; termini particolari non coperti |
| A08 Riduzioni/estero/arrotondamenti | non coperto / divergenza aperta | dubbio documentato con ispezione del componente; caso non finalizzabile |
| A09 XML e stampa | parziale | caso sintetico con EF/EG/EH e allegati passato localmente via API, processo MCP e GUI; lxml usato nelle nuove prove, xmllint solo nella precedente evidenza; stampa: altra area |
| A10 Controllo ufficiale | controllo locale (positivo + 2 negativi) | SUC13 2.3.1 in batch su dati sintetici, 2026-11-01: caso base solo (*) 3345, negativi predisposti scartati (1013 CF defunto, 3376 importo da versare); `tests/fixture_telematico/controllo_20261101/`, `tests/test_telematico_controllo.py`. Collaudo su Desktop Telematico (Windows) e con i servizi dell'Agenzia: da fare |
| A20 Copertura | parziale | matrice aggiornata e regressioni CE03/CE05 sui blocchi; non prova esaustiva di tutte le combinazioni SUC13 |
