# Beni esteri, imposta versata all'estero e detrazione (pacchetto 4)

**Fonti**: XSD `fornituraSUC13_v1.xsd` (`reg:Luogo_Type` con provincia `EE` in `typesReg_v2.xsd`, `BeniEsteri_Type`,
`CertificazioneImpostaVersataEstero`, annotazioni di `QuadroEE` e `QuadroEF`); Fascicolo I pp. PDF 22, 23, 29, 33, 34 e 39;
Allegato di calcolo «passaggi calcolo imposta di successione» pp. 7-8; lettura statica del componente di controllo SUC13 2.3.1
(`CalcolaImpostaSuccessione.setDET` / `calcolaImpostaEsteraDET`).

## Dati (campi del bene)
| Campo | Dove | Significato |
|---|---|---|
| `provincia = "EE"` | immobili (EB terreni, EC fabbricati) | immobile estero |
| `codice_stato_estero`, `stato_estero`, `indirizzo`; facoltativi `stato_federato`, `localita_estero` | immobili esteri | sezione `Luogo/Estero` (codice a 3 caratteri dell'Appendice del Modello Unico, es. 029 Francia) |
| `bene_estero = 1` | EN, EO, EP, EQ, ER | casella «bene sito all'estero» (`BeniEsteri/BeneSitoEstero`) |
| `imposta_estera` | qualunque bene estero | imposta versata all'estero per l'**intero** cespite, euro interi (`ImpostaVersataEstero`) |

## Regole implementate
- Immobile estero (EB/EC): niente `DatiTerreni`/`DatiFabbricati`; restano possesso, diritto, valore e imposta estera.
  **Il controllo ufficiale respinge anche `TipologiaTerreno`** su un terreno estero (diagnostico 3072, «non devono essere inseriti i dati
  identificativi italiani»), che l'XSD lascerebbe facoltativa: per l'estero non si indica (vince il controllo).
- Gli immobili esteri non entrano nelle basi EF1/EF9, nelle circoscrizioni (EF15) e nel bollo (EF16): annotazioni di `QuadroEF`.
  Il loro valore **entra** nei totali del quadro EE (le annotazioni di `QuadroEE` sommano tutti gli immobili).
- Agevolazioni (P, X, Y, Z: «solo se Provincia diverso da EE») e riduzioni su immobili esteri: errore `REGOLA_AGEVOLAZIONE_ESTERO`.
- Azienda estera (EN): il codice fiscale non e' richiesto; titolo estero (EO): il codice fiscale dell'emittente non deve essere presente.
- Imposta estera senza bene estero, o dati dello Stato su un immobile italiano: `DATI_INCOERENTI`.
- Certificazione dell'imposta estera (EG, rigo EG4 `CertificazioneImpostaVersataEstero`): obbligatoria con imposta estera in un quadro
  qualsiasi; senza, nessun XML (`ALLEGATO_OBBLIGATORIO_MANCANTE`).
- **Detrazione `DET.estero`** nell'imposta di successione (guida pp. 7-8): `e = valore quota del bene estero x ISL / QE`;
  `IE = imposta versata all'estero x quota di devoluzione`; `DET.estero = IE se IE < e, altrimenti e` (somma sui cespiti);
  `ISN = ISL - RID - DET.estero`, non negativa. Candidato «componente» con le scale del componente (ISL/QE a 10 decimali HALF_UP,
  `e` a 4 decimali, quota a 5 decimali); il controllo ufficiale lo accetta e respinge un'imposta senza detrazione.

## Prove (2026-11-05, locale, dati sintetici)
`tests/test_beni_esteri.py` (17 test). Controllo ufficiale **positivo** su: immobile estero senza imposta (EC), terreno estero con imposta e
certificazione (EB), conto estero con e senza imposta (ER), titolo estero (EO), azienda estera (EN), aeromobile e nave esteri (EP, EQ), due
mix italiano+estero con detrazione (uno con IE < e, l'altro con IE > e). **Negativo**: imposta di successione alterata (senza detrazione).

## Dubbi e limiti
- La guida mostra `e = 82,08` per `2.500 x 6.567 / 200.000 = 82,0875`: dubbio gia' documentato
  (`docs/regole/dubbio_arrotondamento.md`); il componente usa 4 decimali (82,0875).
- La guida e il Fascicolo p. 34 divergono sul significato di «proporzionalmente alla quota di devoluzione»: si e' indicato nell'XML l'imposta
  dell'intero cespite (come nell'esempio della guida, 1.000 euro e quota 1/2 -> IE = 500); l'accettazione del controllo conferma la lettura.
- Trattati e accordi internazionali contro la doppia imposizione: non modellati (il Fascicolo p. 23 li esclude dall'indicazione).
- Immobili esteri con `BeneAziendale`, graffati o diritto di abitazione, e codici di Stato non verificati sulla tabella ufficiale (solo 3
  caratteri alfanumerici): non coperti.
