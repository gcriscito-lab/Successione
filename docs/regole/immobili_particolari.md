# Immobili particolari (pacchetto 5): EI con piu' estremi, rendita proposta, graffati, immobili aziendali, diritto di abitazione

Codice: `esporta.py` (`rendita_proposta_ec`, `graffati_ec`, `flag_aziendale`, `immobili_aziendali_en`, `verifica_immobili_aziendali`,
`diritto_abitazione_ec`, `avviso_diritto_abitazione`), `quadri_efgh.py` (`quadro_ei`, `_estremi_ei`, ganci EG), `calcolo.py` (immobili aziendali).
Test: `tests/test_immobili_particolari.py` (controllo ufficiale SUC13 2.3.1 eseguito in locale il 2026-11-05, dati sintetici).

## Riepilogo
| Funzione | Stato | Evidenza col controllo ufficiale |
|---|---|---|
| EI: piu' di tre estremi per immobile (`Continuazione`) | coperto, con un limite scoperto dal controllo | 5 positivi, 1 negativo; 3 combinazioni restano bloccate |
| Rendita proposta (`DeterminazioneRendita` = 1) | coperto | 3 positivi |
| Immobili graffati nel quadro EC (fino a 4) | coperto | 3 positivi (anche con sezione urbana) |
| Immobili aziendali (casella in EB/EC + `ImmobiliAziendali` in EN) | coperto | 3 positivi (anche con imposta di successione dovuta), 1 negativo |
| Diritto di abitazione del coniuge (codici 1-8) | **bloccato con motivo** + avviso | non provabile: dipende dai diritti distinti |
| Caselle discordanza/passaggi nei beni tavolari (EL/EM) | **non previste dall'XSD**: restano non supportate | - |

## EI con piu' di tre estremi
**Fonti**: XSD `QuadroEI_new/PrimoModulo/SezioneII_DatiIntestatario` e `Modulo/SezioneII_DatiIntestatario`: massimo 3 `EstremiTrascrizione` e 3
`EstremiRegistrazione` per modulo; `Continuazione` «puo' essere barrata solo se sono presenti 3 righe» e il modulo successivo riporta gli ulteriori
estremi **senza** `Immobile`; la firma e' solo nel primo modulo. Fascicolo I p. 54.

**Regola**: i moduli necessari sono `ceil(max(n_trascrizioni, n_registrazioni) / 3)`; ogni modulo ha al piu' 3 estremi per tipo; tutti tranne l'ultimo
hanno `Continuazione`.

**Limite scoperto col controllo** (diagnostici 3413/3414): se in un modulo **entrambe** le liste sono piene (3 + 3) il modulo successivo deve contenere
almeno un estremo di **ciascun** tipo; con l'overflow di uno solo (es. 3 trascrizioni + 4 registrazioni, o 5 + 3) il controllo scarta il file anche se
l'XSD lo ammette. Vince il controllo: quei casi restano **bloccati** con un motivo (`non_supportato`). Casi positivi provati: 4+1, 2+5, 6+2, 4+4, 7+7;
negativo: tolta la casella `Continuazione` il controllo respinge.

## Rendita proposta (DOCFA)
**Fonti**: Fascicolo I pp. PDF 29-30 («nel campo "rendita catastale" va indicato il valore della rendita proposta ... nel campo "Determinazione
rendita" il codice 1»; la volonta' va espressa con una dichiarazione sostitutiva allegata nel quadro EG); XSD `reg:DatiCatastaliFabbricati_Type/DeterminazioneRendita`
(tipo `Rendita proposta(1)`).

**Dati**: `beni.rendita_proposta` = si/no (EC). **Regola**: con «si» si scrive `DeterminazioneRendita` = 1 accanto a `RenditaCatastale`; serve la rendita
proposta nel campo rendita e una categoria non fittizia (F); manca la dichiarazione sostitutiva nel quadro EG (rigo «Altro»): `ALLEGATO_OBBLIGATORIO_MANCANTE`.
Fabbricati tavolari (EM): non supportato.

## Immobili graffati (EC)
**Fonti**: XSD `QuadroEC/.../Graffati` (`GraffatiType`: fino a 4 `ImmobiliGraffati` con `DatiCatastali` e `SezioneUrbana` «obbligatoria se presente nei dati
generali»; `ContinuazioneGraffati`; «non puo' essere indicato piu' volte lo stesso immobile graffato»), `reg:DatiCatastali_Type` («nel caso di immobile graffato
riportare solo la prima particella»); Fascicolo I p. PDF 29-32.

**Dati**: `beni.graffati` = lista di `{sezione, foglio, particella, subalterno}` (maschera «Immobile graffato» nel pannello dell'immobile). **Regola**: nei dati
principali si indica la sola prima particella; sezione urbana obbligatoria nei graffati se l'immobile principale ha la sezione, vietata altrimenti; duplicati e
oltre 4 immobili: bloccati (`ContinuazioneGraffati` su un rigo successivo senza dati identificativi: non supportata). Il quadro EB non ha l'elemento; i graffati
dei fabbricati tavolari (EM, `GraffatiTavolareType`) non sono supportati.

## Immobili aziendali
**Fonti**: XSD `BeneAziendale` (EB/EC: «dovra' essere compilato il quadro EN»), `QuadroEN/.../ImmobiliAziendali` (fino a 9, `IdentificazioneBene_Type` =
quadro + rigo + modulo; «sezione obbligatoria in almeno un rigo ... in presenza di casella bene aziendale»; stesso immobile una sola volta per azienda),
annotazioni di `Agevolazioni` («in presenza di bene aziendale il campo non deve essere presente oppure deve avere valore D o Q o G»), di `QuadroEE`
(`TotaleValoreImmobili` al netto dei beni aziendali); Fascicolo I pp. PDF 21 e 29 («il quadro EN, indicandone l'intero valore»).

**Dati**: `beni.bene_aziendale` = si/no (EB/EC); nell'azienda (EN) `beni.immobili_aziendali` = lista di id di immobili (maschera «Immobile aziendale»).
**Regole**: ogni immobile con la casella deve essere richiamato da un'azienda (e viceversa solo immobili con la casella); quadro EN obbligatorio; agevolazioni
ammesse D, Q, G (con P, X, Y, Z ecc.: errore); il valore dell'immobile aziendale esce dal totale immobili di EE; nel calcolo dell'imposta di successione i righi
dell'immobile aziendale non entrano nella QE (il valore e' compreso nell'azienda): provato col controllo, che accetta il caso con imposta dovuta e respinge
un'imposta alterata. Nelle ipotecaria/catastale (EF) l'immobile aziendale resta nelle basi (l'XSD non lo esclude).

**Non supportato**: immobili aziendali nei quadri tavolari (EL/EM), con immobile estero, con agevolazione Q o G nel calcolo (`CALCOLO_NON_SUPPORTATO`), piu' di
9 immobili per azienda (`ContinuazioneImmobiliAziendali`).

## Diritto di abitazione del coniuge superstite
**Fonti**: XSD `DirittoAbitazione` (`DirittoAbitazione_Type`, valori 1-8: prima casa P/Z/X o nessuna, per il coniuge che accetta (1-4) o che ha rinunciato
all'eredita' ma non al legato (5-8); molte condizioni), Fascicolo I pp. PDF 31-32 («il diritto di abitazione ... viene riportato nella trascrizione ... al
pari degli altri diritti presenti nella sezione devoluzione»).

**Perche' bloccato**: il diritto va riportato nella devoluzione insieme alla nuda proprieta' degli altri beneficiari, cioe' con **diritti distinti** dal
diritto del defunto e valutati con i coefficienti del TUS (Fascicolo I pp. PDF 24-27). L'esportazione della devoluzione non supporta oggi diritti diversi da
quello del defunto (`devoluzioni_bene`: «diritto devoluto diverso ...: non supportato»). Il campo `beni.diritto_abitazione` (menu dei codici) si conserva in
bozza e blocca l'XML completo con un motivo esplicito. In piu' l'export emette l'avviso non bloccante `DIRITTO_ABITAZIONE_DA_VERIFICARE` quando fra gli
eredi c'e' un coniuge e fra i beni un'abitazione (categoria A esclusa A/1, A/8, A/9): l'omissione sarebbe altrimenti silenziosa.

## Modifiche a app.js (minime)
Due tabelle nel pannello del bene, riusando l'helper `tabella` esistente: «Immobile graffato» (quadro EC, campi sezione, foglio, particella, subalterno) e
«Immobile aziendale» (quadro EN, riferimento a un bene). I campi si/no e il menu del diritto di abitazione sono voci di `STRUTTURATI` (nessun codice JS).
`tests/test_maschere_strutturati.py`: `beni.graffati` e `beni.immobili_aziendali` aggiunti all'elenco delle maschere dedicate; elenco delle pagine del
Fascicolo citabili negli aiuti esteso a 21, 29, 29-30, 31-32.
