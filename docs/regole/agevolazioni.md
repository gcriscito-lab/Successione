# Agevolazioni A, C, D, E, G, H, M, N (pacchetto 2)

Codice: `src/successioni/telematico/agevolazioni.py`. Test: `tests/test_agevolazioni.py`. Le agevolazioni P, X, Y, Z sono in
`prima_casa.py`; L, Q, R, F e le riduzioni 1-5 in `riduzioni_art25.py`.

## Fonti
- XSD `fornituraSUC13_v1.xsd`: annotazione di `Devoluzione/Agevolazioni` (quadri ammessi, gradi di parentela, esclusivita' per bene),
  di `QuadroEF` (ImpostaProporzionale, AgevolazioneG, AgevolazioneM, Circoscrizioni_Numero), di `QuadroEE` (esclusione di A),
  di `QuadroEG` (Altro, AgevolazioniImposteIpocatastali, RiduzioniImposteSuccessione), di `QuadroEH/SezioneIV_AltreAgevRiduz`.
- Fascicolo I p. PDF 40-41 (righi EF1-EF3), p. PDF 56 (Allegato 2), p. PDF 57 (**quadro sinottico**: I, C, S per codice).
- Guida di calcolo «All. Specifiche tecniche» p. 1: la QE esclude i righi con A, D, C, G, N, E, H (non M).

## Effetti per codice
| Codice | Ipotecaria | Catastale | Successione | Altro |
|---|---|---|---|---|
| A beni culturali (vincolo anteriore) | base proporzionale | base proporzionale | esente | esclusa da EE (TotaleValoreImmobili); EH sez. IV `AgevolazTipoA` (num. protocollo e data) o EG11 |
| N boschi montani | base proporzionale | base proporzionale | esente | solo EB/EL; gradi 01-04, 5A, 5B, 06, 7A, 7B, 08, 9A, 9B |
| C compendio unico (zone montane) | esente | esente | esente | EH sez. IV `FlagC` o EG10 |
| E compendio unico generale | esente | esente | esente | EH sez. IV `FlagE` o EG10 |
| D aziende e immobili | esente | esente | esente | EH sez. IV `FlagD` o EG10; gradi 01, 02, 04, 06, 08 |
| H immobili demoliti/inagibili | esente | esente | esente | EG8 «Altro» obbligatorio; esclusi dalle circoscrizioni (EF15/EF16); solo persone fisiche |
| M fondi rustici montani | fissa 200 (EF3) | esente | **dovuta** | esteso a tutti i beneficiari del bene |
| G giovani imprenditori agricoli | fissa 200 (EF2) | esente | esente | EF2 somma solo EB-EM; **solo EN** in questa versione; meno di 40 anni al decesso |

Regole generali: per ogni bene una sola tipologia fra A, C, D, E, L, M, N, P, X, Y, Z (F, G, Q, R possono convivere); le agevolazioni non
sono ammesse con beneficiari trust (tipo 5); la richiesta di un beneficiario diverso dal dichiarante va allegata (EG10 per C, D, E; EG11 per A)
con il documento d'identita' (EG7).

## Aggancio nel codice
- Lettura riga e validazioni: `agevolazioni.leggi_riga` (dopo `PC.leggi_riga` e `RA.leggi_riga`), regole incrociate `agevolazioni.valida`.
- EF (`quadri_efgh.quadro_ef`): i righi C, D, E, G, H, M escono dalle basi EF1/EF9; blocchi `AgevolazioneG`/`AgevolazioneM` nell'imposta
  ipotecaria; se tutti gli immobili sono esenti non si emettono le sezioni I e II; H esce dal conteggio delle circoscrizioni.
- EE (`esporta.quadro_ee`): i beni con A sono esclusi dal totale immobili.
- Calcolo (`calcolo._leggi`): i righi esenti (A, C, D, E, G, H, N) non entrano nella QE.
- EH/EG: `riduzioni_art25.sezione_eh` (A come L, flag C/D/E insieme a Q) e `quadri_efgh.quadro_eg` (EG10, EG8 per H).

## Evidenze (controllo ufficiale SUC13 2.3.1 locale, 2026-11-05, dati sintetici)
Positivi: N, M, A (dichiarante), C, E, D su fabbricato, H su fabbricato, H su entrambi i beneficiari, D in EN, G in EN con beneficiario di 29 anni,
e i tre casi con imposta di successione dovuta (conto da 2.400.000 e terreno da 1.000.000): senza agevolazioni 65.736; con N su entrambe le
quote 21.736; con C solo sulla quota del dichiarante 43.736; con M 65.736 (S dovuta). L'imposta calcolata dal programma coincide in ogni caso
con quella verificata dal controllo. Negativo: la base proporzionale con il rigo C rimesso dentro e' respinta.

## Non coperto (blocco con motivo)
- **G su terreni e fabbricati** (EB, EC, EL, EM): l'annotazione richiede che siano beni aziendali, non supportati. G e' ammessa solo in EN.
- **Quadri EL ed EM** (tavolari) con queste agevolazioni: non provati col controllo.
- **D in EC/EB**: provato su fabbricato (EC); i requisiti soggettivi (discendenti e coniuge) si controllano solo sul grado di parentela.
- **Requisiti soggettivi** (coltivatore diretto, IAP, impegno a coltivare per sei anni): l'XSD non definisce campi dedicati per G, M, N;
  restano dichiarazioni del professionista.
- **Combinazioni** con riduzioni art. 25 sulla stessa riga: gia' bloccate (riduzioni_art25.py); con prima casa sullo stesso bene: errore
  `REGOLA_AGEVOLAZIONE_ESCLUSIVA`.
- Beni aziendali (`BeneAziendale`, immobili aziendali), beni esteri, trust: fuori perimetro.
