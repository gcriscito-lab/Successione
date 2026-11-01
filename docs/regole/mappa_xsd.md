# Mappa XSD SUC13 e corrispondenza con il modello dati

Area 1 (telematico). Fonti in sola lettura in `fonti/`. Questo documento e' scritto a mano; l'albero completo degli
elementi (occorrenze, tipi, facet, annotazioni integrali) e le enumerazioni sono in
[`mappa_xsd_albero.md`](mappa_xsd_albero.md), **generato dagli XSD** con
`PYTHONPATH=src python3 -m successioni.telematico.mappa > docs/regole/mappa_xsd_albero.md` (un test verifica che sia
aggiornato).

## 1. Fonti e versioni

| Fonte | Versione / impronta (fonti/manifest.json) | Uso |
|---|---|---|
| `SUC13_20250702/SUC/xsd/fornituraSUC13_v1.xsd` | sha256 `25fe2af4…59b6` | schema principale (targetNamespace `suc`) |
| XSD caricati dagli import | `fornitura_v2`, `typesDati_v2`, `typesProvincie_v2`, `datiFiscali_v3`, `typesFiscali_v3`, `typeEventi_v3`, `typesReg_v2`, `telematico_v1` | non usati dallo schema: `datiFiscali_v4`, `typesFiscali_v4`, `typesDati_v3`, `esitoFornitura_v3` |
| `Specifiche_SUC13_20250702.pdf` | sha256 `1b01ebe1…cb1b` | busta e tipi: pp. 3-15 (p. 4 CodiceFornitura SUC13, p. 6 UTF-8, p. 11 Tabella 3 tipi, p. 13-15 Messaggio/Fornitura/TipoFornitore) |
| `Succ_FASCICOLO_I_Nov_23.pdf` | sha256 `a760fa06…40f5` | istruzioni di compilazione (pagine indicate come "p. PDF") |
| `All. Specifiche tecniche (passaggi calcolo …).pdf` | sha256 `2570aacc…c447` | calcolo dell'imposta (vedi `dubbio_arrotondamento.md`) |

## 2. Busta (radice) — Specifiche pp. 4, 13-15

```
tm:Messaggio                                   (telematico_v1.xsd)
  tm:Intestazione
    tm:CodiceFiscaleFornitore   [1]            pattern [0-9]{11}|[A-Z0-9]{16}
    tm:SpazioServizioTelematico [0..1]         riservato al servizio telematico: mai valorizzato da noi
  tm:Contenuto @CodiceFornitura="SUC13"        pattern [A-Z0-9]{5}; valore SUC13 (Specifiche p. 4)
    suc:Fornitura                              substitutionGroup di tm:Fornitura (astratto)
      suc:Intestazione  (estende suc:Intestazione_Type)
        suc:TipoFornitore [1]                  DatoAN; ammessi 1 o 10 (Specifiche p. 15, "Validazione")
        suc:SpazioUtente  [0..1]
      suc:Dichiarazione @identificativo        suc:Dichiarazione_SUC_Type (estende cm:Documento_Type);
                                               @identificativo Identificativo_Type: 5 cifre non tutte zero
        suc:Frontespizio [1]
        suc:QuadroEA, EB, EC, ED, EE, EF, EG, EH, EI_new, EL, EM, EN, EO, EP, EQ, ER   tutti [0..1], in quest'ordine
```

Namespace (prefisso usato nel file): `tm` = `www.agenziaentrate.gov.it:specificheTecniche:telent:v1`,
`suc` = `urn:…:sco:suc:v1`, `reg` = `urn:…:sco:reg:v2`, `sc` = `urn:…:sco:common:v3`, `cm` = `urn:…:common:v2`.
`elementFormDefault="qualified"` in tutti gli schemi: i figli dichiarati nei tipi `reg:` (es. `Dati_Anagrafici_Type`,
`Luogo_Type`, `DatiCatastali_Type`, `ImpegnoATrasmettere_Type`) sono nel namespace `reg` anche dentro elementi `suc`.
Il serializzatore (`telematico/modello_xsd.py`) ricava ordine e namespace dallo schema, non da liste scritte a mano.

### Conflitti tra fonti (documentati, nessuno blocca il perimetro)

| Punto | Fonte A | Fonte B | Scelta |
|---|---|---|---|
| namespace `tm` | PDF Tabella 1 p. 9: `urn:www.agenziaentrate…telent:v1` | `telematico_v1.xsd`: `www.agenziaentrate…telent:v1` (senza `urn:`) | vale lo schema (e' quello validato) |
| numero di dichiarazioni | Specifiche p. 14: Dichiarazione "una o più occorrenze" | p. 3 "una sola dichiarazione"; XSD `Dichiarazione` `[1..1]` | una dichiarazione per fornitura |
| codici diritto a due cifre | Fascicolo I p. PDF 24: "codice '08'", "'02'" | XSD `CodiciDiritto_Type`: `8`, `2` | si scrive il valore XSD; in ingresso `08` e' accettato e convertito (documentato) |
| gradi 5A/7A/9A | Guida calcolo p. 9: `05a`, `07a`, `09a` | XSD `GradoParentela_Type`: `5A`, `7A`, `9A` (stesse descrizioni) | codice XSD; corrispondenza per descrizione |
| TipoFornitore | XSD: `cm:DatoAN_Type` senza enumerazione | Specifiche p. 15: valori 1, 10 | controllo applicato in `esporta` |

## 3. Tipi semplici (typesDati_v2.xsd, typesReg_v2.xsd; Specifiche Tabella 3 p. 11)

| Tipo | Regola (pattern/facet) | Conversione dal modello (`telematico/formati.py`) |
|---|---|---|
| DatoAN_Type | maiuscole, cifre, `. , ' - / ° ^ ( ) & + " \ |`, À È É Ì Ò Ù Ü; primo carattere A-Z 0-9 - " | maiuscolo + spazi multipli ridotti; altri caratteri -> errore |
| reg:DatoAN2_Type | come AN, primo carattere anche `. ' ,` (cognome, nome, denominazione) | idem |
| DatoNP_Type | `[1-9][0-9]*` (niente zero; maxLength per elemento: Valore 13) | solo interi >= 1, decimali rifiutati |
| DatoNU_Type | intero non nullo con segno | asse netto EE; zero -> elemento omesso con avviso |
| DatoVP_Type | `[0-9]+,[0-9]{2}`, maxLength 16 | punto -> virgola, max 2 decimali |
| DatoCF_Type | 11 cifre o 16 caratteri nel formato ministeriale | maiuscolo; il carattere di controllo NON e' verificato dallo schema |
| DatoDT_Type | `ggmmaaaa`, "non successiva alla data corrente" | ISO -> ggmmaaaa; confronto con `ContestoExport.data_riferimento` |
| DatoCB_Type | `0`/`1` | si scrive solo `1`; caselle non barrate omesse |

## 4. Corrispondenza modello -> XML nel perimetro (`telematico/esporta.py`)

`sup.` = `opzioni.telematico` (vedi `telematico/supplemento.py`); campi da promuovere nel modello comune in
`docs/PROPOSTE_telematico.md`.

| Elemento XSD | Origine nel modello | Note / fonte |
|---|---|---|
| tm:CodiceFiscaleFornitore | `ContestoExport.cf_fornitore` | Specifiche p. 13 |
| suc:TipoFornitore | `ContestoExport.tipo_fornitore` (1/10) | Specifiche p. 15 |
| Dichiarazione/@identificativo | `ContestoExport.identificativo` (default 00001) | fornitura_v2.xsd Identificativo_Type |
| Frontespizio/CodiceFiscaleDefunto | persona `ruolo=defunto`.codice_fiscale | |
| TipoDichiarazione/PrimaDichiarazione | costante `1` (solo prima dichiarazione) | sostitutive: non supportate |
| TipoDichiarazione/Devoluzione/DevoluzionePerLegge | `sup.dichiarazione.devoluzione_per_legge = true` | testamento/legge estera: non supportati |
| Beneficiari/NumeroEredi, NumeroChiamati | conteggio dei righi EA per tipo soggetto 1 e 3 | annotazioni NumeroEredi/NumeroChiamati |
| DatiDefunto/DatiAnagrafici | cognome, nome, data_nascita, luogo_nascita (ComuneNascita); `sup.persone[id].sesso`, `.provincia_nascita` | nati all'estero: provincia EE e stato in ComuneNascita (annotazione DatiAnagrafici) |
| DatiDefunto/UlterioriDati/DataDecesso | defunto.data_decesso | > 2 ottobre 2006, >= nascita (annotazione) |
| UlterioriDati/StatoCivile | `sup.dichiarazione.stato_civile` (StatoCivile_Type) | |
| Presentatore | persona `ruolo=presentatore` **oppure** `sup.dichiarazione.presentatore.persona_id` (es. un erede); `codice_carica`, `telefono`, `email` dal supplemento | solo codice carica 1; almeno telefono o email (annotazione) |
| FirmaModello/CasellaXX | `1` per ogni quadro presente nel file | Fascicolo I p. PDF 15 ("vanno indicati anche i Quadri compilati") |
| FirmaModello/FirmaDichiarante | `sup.dichiarazione.firma_dichiarante = true` (conferma esplicita) | mai impostata d'ufficio |
| ImpegnoATrasmettere | `ContestoExport.impegno_codice`, `.data_impegno`, CF fornitore | solo se TipoFornitore=10 e fornitore diverso dal dichiarante (annotazione) |
| QuadroEA/Modulo/Soggetto | persone `ruolo=erede` (TipoSoggetto 1, o 3 con `sup.tipo_soggetto='3'`) | 3 soggetti per modulo |
| Soggetto/GradoParentela | `sup.persone[id].grado_parentela` oppure `relazione_con_defunto` se e' gia' un codice XSD | testo libero in relazione_con_defunto = dato interno (avviso) |
| Soggetto/PortatoreHandicap | `sup.persone[id].portatore_handicap = true` | |
| QuadroEB/Modulo/Terreni | beni `tipo=terreno` | 2 righi per modulo |
| Luogo/Provincia, Italia/* | `sup.provincia`, `comune` (o `sup.comune_amministrativo`), `sup.codice_comune` (catastale, Fascicolo I p. PDF 20/28), `sup.codice_comune_amministrativo`, `sup.indirizzo` | province tavolari ed EE: non supportate |
| DatiTerreni/DatiCatastali | foglio, particella, subalterno | `sezione` non prevista per i terreni -> non supportato |
| DatiTerreni/DatiTerreni | `sup.superficie {ettari, are, centiare}`, `sup.natura` (solo T), `sup.reddito_dominicale` o, in mancanza, `rendita` (avviso di interpretazione) | |
| Possesso | `quota_defunto` (numeratore come `n,00` perche' PossessoNumeratore e' DatoVP) | denominatore max 6 cifre |
| CodiceDiritto_P | `diritto` (CodiciDirittoImmobili_Type; alias da descrizione XSD, es. `proprieta` -> `1`) | |
| TipologiaTerreno | `sup.tipologia_terreno` (1/2/3) | obbligatoria (annotazione) |
| Valore | `valore`: base imponibile della **quota del defunto**, euro interi | Fascicolo I p. PDF 22/30/34 |
| DevoluzioneXX/Devoluzione | `devoluzioni` del bene: IdentificazioneSoggetto (rigo/modulo EA), QuotaElementi (num/den come inseriti), QuotaValore = Valore × quota, CodiceDiritto_Rip | 3 per rigo; oltre: Continuazione=1 e rigo successivo con sola devoluzione |
| QuadroEC/Modulo/Fabbricati | beni `tipo=fabbricato`: come EB piu' SezioneUrbana (`sezione`), ZonaCensuaria, CategoriaCatastale (`categoria`, `A/2` -> `A2`), Classe, Consistenza, RenditaCatastale (`rendita`) | Indirizzo obbligatorio; consistenza solo per A, B, C; rendita obbligatoria tranne F (annotazioni) |
| QuadroER/Modulo/Rendite | beni `tipo=disponibilita_finanziaria` o `altro`: `sup.tipo_cespite` (BI, CR, DN, AB), `descrizione`, possesso, diritto (CodiciDirittoNonImmobili 1/2), valore | 4 righi per modulo; CR comprende le somme in conto corrente (Fascicolo I p. PDF 33) |
| QuadroED/Modulo/Passivita | `passivita`: `sup.tipo`, `descrizione`, `sup.estremi_documento`, `sup.data_documento`, `sup.possesso`, `importo` (Valore, euro interi); ProgressivoCespite da `sup.bene_id` tramite la mappa; Ripartizione 1/1 a `persona_id` | 3 righi per modulo; tipo 3/4/5/7 richiede il cespite |
| QuadroEE | somme calcolate: EE1 = Σ Valore EB+EC, EE5 = Σ Valore ER, EE6 = EE1..EE5, EE7 = Σ passivita', EE8 = EE6 − EE7 | annotazioni QuadroEE |

Campi del modello **interni per progetto** (non hanno elemento XSD; non bloccano, compaiono come avviso
`DATO_INTERNO_NON_ESPORTATO`): `beni.provenienza`, `beni.descrizione` per EB/EC, `persone.relazione_con_defunto` in
testo libero, campi del presentatore separato (`relazione_con_defunto`, `data_decesso`), sezione `note`.
Ogni altro campo valorizzato e non serializzato va in `non_supportato` e blocca l'XML.

## 5. Ordinamento, numerazione e mappa

Le righe sono ordinate con chiavi ricavate dai dati, mai dall'ordine delle liste (riordinare non cambia il file):
EA per (cognome, nome, codice fiscale, id); EB/EC per (comune, sezione, foglio, particella, subalterno, id) con
ordinamento numerico dei campi solo cifre; ER per (tipo cespite, descrizione, id); ED per (tipo, data documento,
descrizione, id); le devoluzioni di un bene per posizione EA (annotazione IdentificazioneSoggetto: "in ordine
progressivo") e diritto. Righi per modulo: EA 3, EB 2, EC 2, ER 4, ED 3 (maxOccurs negli XSD).

`EsitoExport.mappa[id_interno]` = `{coll, quadro, modulo, rigo, xpath, righi_continuazione}` (beni),
`{…, posizione}` (devoluzioni). Gli XPath usano indici espliciti e sono valutabili sul file. Gli errori della
validazione XSD vengono ricondotti all'id interno con il prefisso XPath piu' lungo (`beni[b_x] @ /tm:Messaggio/…`).

## 6. Codici provvisori del modello -> enumerazioni XSD

| Dato del modello | Valore oggi | Enumerazione XSD | Regola di conversione |
|---|---|---|---|
| `beni.diritto` (testo libero) | es. `proprieta` | EB/EC: `CodiciDirittoImmobili_Type` (1, 1S, 1T, 2, 2S, 2T, 4, 5, 6, 10); ER: `CodiciDirittoNonImmobili` (1, 2) | codice XSD; oppure descrizione XSD normalizzata (`proprieta`, `nuda_proprieta`, `proprieta_superficiaria`…); oppure forma a due cifre `08` |
| `devoluzioni.diritto` | es. `proprieta` | EB/EC: `CodiciDiritto_Type` (17 valori); ER: `CodiciDirittoNonImmobiliDevoluzione` (1, 2, 7, 8) | come sopra; nel perimetro deve coincidere con il diritto del defunto |
| `persone.ruolo` | erede / legatario / rappresentante / presentatore / altro | `TipoSoggetto_Type` 1 erede, 2 legatario, 3 chiamato, 4 coniuge rinunciatario, 5 trust, 6 altro; `CodiciCarica_Type` per il dichiarante | erede -> 1 (o 3 con `sup.tipo_soggetto`); legatario -> 2 (non supportato: richiede testamento); rappresentante/altro -> non supportato |
| `persone.relazione_con_defunto` | testo libero | `GradoParentela_Type` (43 codici) | usata solo se e' gia' un codice; altrimenti serve `sup.grado_parentela` |
| `beni.tipo` | fabbricato / terreno / disponibilita_finanziaria / altro | quadri EC / EB / ER (`quadri.quadro_di`) + `TipoCespite_Type` per ER | `tipo_cespite` obbligatorio per ER |

Proposta di sostituzione definitiva in `docs/PROPOSTE_telematico.md`.

## 7. Regole dalle annotazioni XSD

La validazione di schema **non** esegue le regole scritte nelle annotazioni. Implementate in `esporta.py`
(codice errore -> annotazione):

| Codice | Regola | Elemento |
|---|---|---|
| REGOLA_DATA_DECESSO | data decesso > 02/10/2006, >= nascita, non futura | Frontespizio/DatiDefunto/UlterioriDati/DataDecesso |
| REGOLA_PRESENTATORE | dichiarante diverso dal defunto; con carica 1 presente in EA | Presentatore/CodiceFiscale, CodiceCarica |
| DATO_MANCANTE (telefono/email) | almeno uno dei due | Presentatore/Telefono, Email |
| REGOLA_IMPEGNO | sezione solo con TipoFornitore 10 e fornitore diverso dal richiedente | Frontespizio/ImpegnoATrasmettere |
| REGOLA_GRADO_CONIUGE | un solo '01'; '01' solo con stato civile 2, 3, 5, 7 | QuadroEA/…/GradoParentela |
| REGOLA_GRADO_LEGGE | con devoluzione per legge esclusi 12-14, 17-19, 23-26, 35, 37-39; 36 solo se unico | QuadroEA/…/GradoParentela |
| non supportato | gradi 04/15 per legge richiedono la rappresentazione | QuadroEA/…/SuccessionePerRappresentazione |
| SOGGETTO_SENZA_DEVOLUZIONE | ogni soggetto EA compare in una devoluzione | QuadroEA/Modulo/Soggetto |
| DEVOLUZIONE_MANCANTE / DEVOLUZIONE_SENZA_EA | devoluzione obbligatoria con EA, vietata senza | Devoluzione{EB,EC,ER} |
| DEVOLUZIONE_DUPLICATA | stesso beneficiario piu' volte solo con diritti diversi | IdentificazioneSoggetto |
| QUOTE_DEVOLUZIONE | somma delle quote = 1/1 | QuotaElementi |
| (calcolo) QuotaValore | valore quota = valore × quota se diritto uguale (tolleranza 1%, max 100 €) | QuotaValore; Fascicolo I p. PDF 24 |
| REGOLA_CONSISTENZA / REGOLA_RENDITA | consistenza solo per A, B, C; rendita obbligatoria salvo F, vietata per F | DatiFabbricati/Consistenza, RenditaCatastale |
| DATO_MANCANTE (indirizzo EC) | indirizzo obbligatorio se provincia diversa da EE | QuadroEC/…/Luogo |
| DATO_MANCANTE (tipologia terreno) | obbligatoria | QuadroEB/…/TipologiaTerreno |
| REGOLA_SPESE_FUNERARIE | tipo 2: valore <= 1033 | QuadroED/…/Possesso/Valore |
| REGOLA_PROGRESSIVO_CESPITE | tipo 3/4/5/7 richiede il cespite; tipo 3 solo EB/EC (EL/EM); altrimenti vietato | QuadroED/…/ProgressivoCespite |
| QUADRO_OBBLIGATORIO_NON_SUPPORTATO | EF (dal 2025 o EA + immobili), EG (con EA), EH (carica diversa da 5/6/7) | QuadroEF, QuadroEG, QuadroEH |
| EE | totali uguali alle somme | QuadroEE/* |

**Non implementate** (casi fuori perimetro o controlli che richiedono tabelle esterne): congruenza comune/provincia e
codici comune (tabella dell'Agenzia non in `fonti/`), registrazione in Anagrafe del codice fiscale e carattere di
controllo, quote di legge dell'Allegato 5 (avviso nella matrice), eta' coerente con il grado di parentela, regole di
agevolazioni/riduzioni, beni aziendali, graffati, diritto di abitazione, EI, rinunce, rappresentazione, trust,
testamento, sostitutive. Queste restano compito del controllo ufficiale e, per i casi fuori perimetro, bloccano
l'export tramite `non_supportato`.
