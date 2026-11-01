# Proposte di modifica al modello comune (area 1 -> coordinatore)

Proprieta' dei file: `schema.py`, `servizio.py`, `quadri.py` sono del coordinatore (docs/CONTRATTI_MODULI.md).
Qui solo proposte: campo, motivo, fonte. Finche' non sono accolte, il modulo telematico legge i dati mancanti da
`opzioni.telematico` (`src/successioni/telematico/supplemento.py`), che e' gia' salvato, versionato e incluso
nell'impronta dichiarativa. Quando un campo viene promosso nel modello, `supplemento.attr()` usa gia' per primo il
valore dell'entita': la migrazione consiste nello spostare il valore e cancellare la chiave del supplemento.

## P1. Codici di diritto: sostituire i codici provvisori con le enumerazioni XSD

| Campo | Oggi (`schema.py`) | Proposta | Fonte |
|---|---|---|---|
| `beni.diritto` | `str` libero (es. `proprieta`) | enum dei codici XSD: per EB/EC `CodiciDirittoImmobili_Type` = 1, 1S, 1T, 2, 2S, 2T, 4, 5, 6, 10; per ER `CodiciDirittoNonImmobili` = 1, 2 | fornituraSUC13_v1.xsd (righe 4119-4313); Fascicolo I Allegato 4 |
| `devoluzioni.diritto` | `str` libero | enum `CodiciDiritto_Type` (17 codici: 1, 1S, 1T, 2, 2S, 2T, 3, 3S, 4, 5, 6, 7, 7S, 8, 8S, 8T, 10); per beni ER `CodiciDirittoNonImmobiliDevoluzione` = 1, 2, 7, 8 | idem |

Come sostituirli senza perdere dati:
1. aggiungere in `schema.py` un kind `enum_xsd:<Tipo>` validato con `successioni.telematico.xsd.enumerazioni(<Tipo>)`
   (le enumerazioni sono lette dagli XSD, nessuna lista copiata a mano); il vincolo dipende dal quadro del bene, quindi
   va in `controlli_coerenza` (o in un validatore per tipo di bene);
2. migrazione dei valori esistenti con `successioni.telematico.esporta.codice_enum(v, tipo, alias_descrizione=True)`:
   converte i testi gia' usati (`proprieta` -> `1`, `nuda_proprieta` -> `2`, `usufrutto` -> `8`, forma `08` -> `8`);
   un valore non convertibile diventa `{"stato": "da_confermare"}` e resta visibile nel pannello controlli;
3. nell'interfaccia mostrare codice + descrizione dell'XSD (`mappa_xsd_albero.md`, sezione Enumerazioni).

`schema.controlli_coerenza` somma gia' le quote per (bene, diritto): coerente con l'annotazione QuotaElementi.

## P2. Persone: dati anagrafici e qualifiche richiesti dal tracciato

| Campo proposto | Tipo | Motivo | Fonte |
|---|---|---|---|
| `sesso` | enum M, F | obbligatorio in `reg:Dati_Anagrafici_Type` (defunto, dichiarante, EA) | typesReg_v2.xsd / Sesso_Type |
| `provincia_nascita` | enum `PN_Type` (sigle + EE) | obbligatorio; per i nati all'estero EE e stato estero nel comune | annotazione DatiAnagrafici |
| `grado_parentela` | enum `GradoParentela_Type` (43 codici) | obbligatorio in EA; determina aliquota e franchigia | annotazione GradoParentela; guida calcolo p. 9-10 |
| `tipo_soggetto` | enum `TipoSoggetto_Type` (1 erede, 2 legatario, 3 chiamato, 4 coniuge rinunciatario, 5 trust, 6 altro) | oggi `ruolo` non distingue erede/chiamato; un ruolo "chiamato" manca | XSD Soggetto/TipoSoggetto |
| `portatore_handicap` | booleano | franchigia 1.500.000 | guida p. 3 |
| `denominazione` | testo (DatoAN2, max 150) | enti e soggetti non persone fisiche (gradi 36-39) | XSD Soggetto/Denominazione |

`relazione_con_defunto` resta descrittivo (non esportato). Per le **qualifiche multiple** (stesso soggetto erede e
legatario) la specifica §5 chiede una sola persona: proporre una lista `qualifiche` (tipo soggetto per rigo EA) e
collegare le devoluzioni alla qualifica, non a una persona duplicata.

## P3. Dati della dichiarazione (frontespizio)

Proposta: una sezione strutturata `dichiarazione` (o campi validati in `opzioni`) con:

| Campo | Tipo | Motivo | Fonte |
|---|---|---|---|
| `stato_civile` | enum `StatoCivile_Type` | obbligatorio; vincola il grado 01 | annotazione GradoParentela |
| `devoluzione` | legge / testamento / entrambi; estremi del testamento | obbligatorio almeno uno | annotazione Devoluzione |
| `presentatore_id` | `ref:persone` | il dichiarante e' spesso un erede: oggi o lo si duplica con ruolo `presentatore` (avviso `PERSONA_DUPLICATA`) o si usa `opzioni.telematico.dichiarazione.presentatore.persona_id` | specifica §5; annotazione CodiceCarica |
| `codice_carica` | enum `CodiciCarica_Type` | obbligatorio | XSD Presentatore |
| `telefono`, `email` | DatoTL, DatoEM | almeno uno obbligatorio | annotazione Presentatore |
| `firma_dichiarante` | booleano con origine `confermato` | la firma non va impostata d'ufficio ne' via MCP | XSD FirmaDichiarante |

## P4. Beni: luogo, dati catastali e tipo cespite

| Campo | Tipo | Motivo | Fonte |
|---|---|---|---|
| `provincia` | enum `PENonTavolare_Type` (+ rilevazione tavolare/EE) | obbligatorio in Luogo | typesReg_v2.xsd |
| `codice_comune` | testo max 4 (EB) / 5 (EC) | codice catastale del comune | Fascicolo I p. PDF 20, 28 |
| `comune_amministrativo`, `codice_comune_amministrativo` | testo | obbligatori; possono differire dal catastale | Fascicolo I p. PDF 28 |
| `indirizzo` | testo max 80 | obbligatorio per EC | annotazione Luogo EC |
| `natura`, `tipologia_terreno`, `superficie_*`, `reddito_dominicale` | enum / interi / importo | terreni; oggi `rendita` per un terreno e' interpretata come reddito dominicale (avviso) | XSD DatiTerreni; TipologiaTerreno |
| `classe`, `zona_censuaria`, `consistenza` | testo / importo | fabbricati | XSD DatiFabbricati |
| `tipo_cespite` | enum `TipoCespite_Type` (BI, CR, DN, AB, GD) | obbligatorio in ER; DN e BI cambiano il calcolo | Fascicolo I p. PDF 33; guida p. 2, 4 |

Chiarire nel modello il significato di `beni.valore`: **base imponibile della quota posseduta dal defunto, in euro
interi** (Fascicolo I p. PDF 22, 30, 34). L'export rifiuta i decimali invece di arrotondarli.

## P5. Passivita': tipo, documento e ripartizione

| Campo | Tipo | Motivo | Fonte |
|---|---|---|---|
| `tipo` | enum `CodiciPassivita_Type` (1-12) | obbligatorio | XSD Passivita/Tipo |
| `estremi_documento`, `data_documento` | testo max 50, data | obbligatori | annotazioni ED |
| `quota_defunto` | quota | Possesso obbligatorio (salvo tipo 11) | Fascicolo I p. PDF 38 |
| `bene_id` | `ref:beni` | progressivo cespite per i tipi 3, 4, 5, 7 (calcolato dalla mappa, mai scritto a mano) | annotazione ProgressivoCespite |
| `ripartizione` | lista `{persona_id, quota}` al posto del solo `persona_id` | il quadro ED ripartisce fra piu' soggetti (es. 1.000 in parti uguali, guida p. 2-3) | XSD RipartizioneED |

## P6. Registro dei quadri (`quadri.py`)

- **EE**: oggi `supportato: False` ("dipende dal calcolo"). L'export lo genera ora dai quadri esportati (totali delle
  annotazioni): proporre `supportato: True`, vista di sola lettura con i totali di `EsitoExport.mappa["quadro:EE"]`.
- **EF/EG/EH** restano non supportati: l'export li segnala in `quadri_mancanti` quando le annotazioni li rendono
  obbligatori (EF dal 2025 o con EA + immobili, EG con EA, EH salvo cariche 5/6/7).

## P7. Servizio, MCP e invalidazione (`servizio.py`)

- Operazioni proposte: `esporta_telematico(pratica_id, scopo)` e `calcola_imposta(pratica_id)` che chiamano
  `telematico.esporta.esporta_xml` / `telematico.calcolo.calcola` sui dati della revisione corrente; il contesto
  (`cf_fornitore`, `tipo_fornitore`, impegno) viene dalle impostazioni locali, non dalla pratica.
- Conservare con l'esito: `impronta_dichiarativa`, revisione, `EsitoExport.versione` / `RisultatoCalcolo.versione`,
  `impronta_xml`. L'esito diventa obsoleto quando cambia l'impronta o la versione delle regole (specifica §10).
- Valori derivati (valore quota, totali EE, imposta) non scrivibili via MCP: sono prodotti dall'export/calcolo.
- `VERSIONE_REGOLE` del servizio dovrebbe includere `telematico.fonti.VERSIONE_MODULO`.
- Un file con `completo=False` non deve poter entrare nella preparazione dell'invio ne' essere presentato come
  dichiarazione al controllo ufficiale; puo' essere usato per prove di schema (stato `simulazione`).
