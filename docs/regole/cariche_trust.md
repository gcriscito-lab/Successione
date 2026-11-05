# Cariche 5, 6, 8, 9 · tipo soggetto «Altro» · trust · Stato

Fonti: `fonti/fornituraSUC13_v1.xsd` (annotazioni, riprese in `docs/regole/mappa_xsd_albero.md`), Fascicolo I pp. 14-19 (cariche e
tipi di soggetto), controllo ufficiale SUC13 2.3.1 locale (arbitro: dove le annotazioni non bastano vince il controllo).
Codice: `telematico/frontespizio.py` (`regole_carica`, `regole_tipo_altro`, `grado_tipo_altro`, `morte_presunta`),
`telematico/quadri_efgh.py` (DichSost EG1, EH morte presunta), `telematico/esporta.py`. Test: `tests/test_cariche_trust.py`.

## Coperto (esportato e accettato dal controllo ufficiale)

| Caso | Regola applicata | Evidenza |
|---|---|---|
| Carica 6 (amministratore dell'eredità) | prima dichiarazione; casella «non dar corso alle volture» obbligatoria (diagnostico 3250); EG1 `DichSost` obbligatorio (3328); niente CF del rappresentato; niente quadro EH | positivi `6_chiamati`, `6_eredi`, `6_testamento` |
| Carica 5 (curatore dell'eredità giacente) | come la 6, in più EA con **un solo soggetto**, tipo soggetto 6 «Altro», grado 35; solo con devoluzione per testamento (con devoluzione per legge il grado 35 è vietato dall'XSD) | positivi `5_curatela_testamento`, `5_senza_passivita` |
| Carica 8 (possesso temporaneo dei beni dell'assente) | EH con `MortePresunta` (tribunale, data deposito successiva al decesso, sentenza) al posto del decesso; `Dichiarante` = Presenza se il presentatore è un soggetto del quadro EA, Assenza altrimenti (3213/3214); CF del rappresentato facoltativo ma vietato se uguale a defunto/presentatore | positivi `8_dichiarante_in_ea`, `8_dichiarante_fuori_ea`, `8_testamento` |
| Tipo soggetto 6 «Altro» | solo con grado 35 (estraneo) e come unico soggetto del quadro EA; denominazione al posto del cognome/nome | inclusi nei casi della carica 5 |

Campi nuovi raggiungibili da interfaccia: sezione «Possesso temporaneo dei beni dell'assente» (`morte_presunta.tribunale`,
`.data_deposito`, `.sentenza`; chiave in `CHIAVI_DICHIARAZIONE`).

## Negativi del controllo (XML alterato, prova che la regola viene dal controllo)

- carica 6 senza la casella volture → negativo (3250);
- carica 5 senza l'EG1 `DichSost` → negativo (3328);
- carica 8 con `FlagAssenzaDichiarante` ma dichiarante nel quadro EA → negativo (3213).

## Bloccato (nessun XML, motivo esplicito nei non supportati)

| Caso | Motivo |
|---|---|
| Carica 9 (trustee) | richiede insieme: soggetti tipo 5 nel quadro EA con sezioni `Trust` e beneficiario finale, `TrustDisab`/EF3-bis, `ImpostaCatastaleTrustDisab`, atto istitutivo in EG «Altro», `PagamentoAnticipatoTrust` (EF18ter), esclusione di agevolazioni/riduzioni, solo con testamento. Il modulo `calcolo` non gestisce il trust e le fonti non danno una regola di importo completa verificabile; coprirlo parzialmente produrrebbe importi indovinati |
| Tipo soggetto 5 (trust) | idem |
| Grado 36 (Stato) | l'XSD lo vieta nelle devoluzioni; non esportabile nei quadri di devoluzione |
| Tipo 6 con gradi 36-39 | ammessi dall'XSD con Denominazione ma non provati col controllo: bloccati (solo il grado 35) |
| Carica 5 con devoluzione per legge | il grado 35 è vietato per legge dall'XSD: incompatibile |

Resta non coperto (non toccato dal pacchetto): integrativa con carica 5/6/9 (CasiParticolari non dovuto, `dichiarazione sostitutiva = 3`).
