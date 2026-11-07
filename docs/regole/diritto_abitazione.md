# Diritto di abitazione del coniuge superstite (art. 540 c.c., legato ex lege)

Codice: `src/successioni/telematico/diritto_abitazione.py` (regole e prima casa), `esporta.py` (`riga_ec`, `_riga_immobile_estero`,
`devoluzioni_bene`, `_valori_diritti_distinti`), `quadri_efgh.py` (imponibile EF1/EF9), `calcolo.py`, `importa.py`.
Test: `tests/test_diritto_abitazione.py`. Fonti lette il 2026-11-07; nessuna regola dalla memoria.

## Fonti

| Regola | Fonte |
|---|---|
| La casella si compila solo per l'immobile su cui, con l'apertura della successione, si costituisce il diritto di abitazione del coniuge; codici 1 (P), 2 (Z), 3 (X), 4 (senza prima casa) per il coniuge erede, 5-8 per il coniuge che ha rinunciato all'eredita' ma non al legato ex lege. Chi rinuncia anche al legato non compila la casella | Fascicolo I pp. PDF 31-32 «Diritto di abitazione» |
| La prima casa si estende alle quote degli altri beneficiari della sezione devoluzione; il diritto indicato nella casella e' trascritto e volturato «al pari degli altri diritti presenti nella sezione devoluzione» | Fascicolo I p. PDF 32, N.B. |
| Tipo soggetto 1 anche per il coniuge cui spetta il diritto di abitazione; tipo 4 (con Rinuncia) per il coniuge rinunciatario che mantiene il legato | Fascicolo I p. PDF 17; annotazioni XSD di TipoSoggetto e Rinuncia |
| Condizioni della casella: coniuge (grado 01) in EA; diritto del defunto 1 o 1S; niente trust ne' bene aziendale; 1-4 senza coniuge rinunciatario, 5-8 solo con il tipo soggetto 4; 1/2/3/5/6/7 solo se provincia diversa da EE; con 1/5 righe solo con agevolazione P (o nessuna), con 2/6 solo Z, con 3/7 solo X | annotazione XSD di `QuadroEC/Modulo/Fabbricati/DirittoAbitazione` (fornituraSUC13_v1.xsd, SUC13_20250702) |
| Categoria: 1/2/5/6 categoria A escluse A1, A8, A9, A10 (oppure F3); 3/7 C/2, C/6, C/7 | typesReg_v2.xsd, annotazione di `DatiCatastaliFabbricati_Type/CategoriaCatastale` |
| Valore quota = valore x quota se il diritto devoluto coincide con quello del defunto e non ci sono i diritti aggiuntivi (superficie, uso, abitazione) | annotazione XSD di `DevoluzioneSingolaImmobili_Type/Quota` |
| EF: i righi del bene con 1/2/3/5/6/7 escono dalla base proporzionale (EF1, EF9); EF4 col. 1 conta gli immobili con P o con il codice 1 o 5 (2/6 solo in assenza di 1/5); EF4 col. 2 e' la somma dei valori quota di tutti i beneficiari del bene | annotazioni di `QuadroEF/SezioneI_ImpostaIpotecaria/ImpostaProporzionale`, `PrimaCasa`, `PrimaCasa_Numero`, `AgevolazionePX_Valore`, `SezioneII_ImpostaCatastale/ImpostaProporzionale`, `ImpostaCatastaleFissa` |
| EH Sezione II: immobile principale = codice 1/5, contiguo = 2/6, pertinenze = 3/7, «se il dichiarante ha grado di parentela 01»; EG9 (PrimaCasa) obbligatorio con 1/2/3/5/6/7 per soggetti diversi dal dichiarante | annotazioni di `QuadroEH/PrimoModulo/SezioneII_AgevPrimaCasa` (e figli) e di `QuadroEG/PrimaCasa`, `QuadroEG/DocumentiIdentita` |
| Imposta di successione: la casella non e' un'esclusione ne' una riduzione; la prima casa incide solo su ipotecaria e catastale | Guida al calcolo pp. 1 e 5; Fascicolo I p. PDF 57 (quadro sinottico) |
| Riga con il diritto di abitazione (codice 3): ammesso «in aggiunta» ai diritti scomponibili della proprieta' (1); per legge i codici delle righe coincidono con quello del defunto | annotazione XSD di `CodiceDiritto_Rip`; Fascicolo I p. PDF 67 (Allegato 4: codice 3; abitazione costituita per testamento) |
| Valore del diritto di abitazione = piena proprieta' x saggio legale x coefficiente per eta' (tabella «Usufrutto, uso e abitazione»); proprieta' gravata = piena proprieta' meno il diritto che la grava | Fascicolo I pp. PDF 25 e 30; coefficienti e saggio 2,5% in `usufrutto.py` (allegato 4 D.Lgs. 123/2025) |

## Comportamento

1. **Casella (legato ex lege)**: `beni.diritto_abitazione` (o `opzioni.telematico.beni.<id>.diritto_abitazione`) con il codice 1-8.
   Le righe di devoluzione restano quelle della proprieta' (codice 1, valore quota = valore x quota): **non** si aggiunge una riga
   di abitazione ne' una nuda proprieta'. E' cio' che fanno le dichiarazioni reali dello studio prodotte con il compilatore
   ufficiale (FNTLRT e DNZRME, codice 1; in DNZRME il coniuge non compare nemmeno fra i beneficiari del bene) ed e' l'unica forma
   ammessa per legge, dove i codici delle righe devono coincidere con quello del defunto.
2. **Prima casa (1, 2, 3, 5, 6, 7)**: il bene entra fra i beni agevolati (estensione a tutti i beneficiari); il codice 1/5 conta
   nel rigo EF4. Se il coniuge e' il dichiarante, la Sezione II del quadro EH riporta il bene (si uniscono le righe P/Z/X del
   coniuge, se ci sono, che devono riguardare lo stesso immobile principale); altrimenti servono la richiesta EG9 e il documento
   d'identita' EG7 (sempre cosi' per i codici 5-8: il rinunciatario non puo' essere il dichiarante).
3. **Riga con codice diritto 3** (diritto di abitazione devoluto, es. per testamento): solo su fabbricato EC in proprieta' (1) del
   defunto, con righe di proprieta' (1) che coprono l'intero e righe di abitazione per 1/1; valore = valore x quota x 2,5% x
   coefficiente per l'eta' del titolare al decesso; proprieta' gravata = valore x quota meno la quota proporzionale
   dell'abitazione. Con la devoluzione per legge e' un errore (va usata la casella).
4. **Imponibile EF1/EF9 non intero** (somma di valori quota con centesimi, es. 1/3 di 1.465): arrotondato all'euro meta' per
   eccesso con avviso `ARROTONDAMENTO_SOMMA_VALORI_QUOTA` (regola unica, docs/regole/dubbio_arrotondamento.md §7). Le fonti non danno il criterio; riscontro del controllo ufficiale SUC13
   2.3.1 locale (2026-11-07): arrotondamento accettato, troncamento respinto; la dichiarazione reale DNZRME riporta lo stesso
   valore. Non e' distinguibile dal calcolo «valore x quota esatto» del componente: coincidono finche' l'errore accumulato delle
   righe resta sotto 50 centesimi.
5. **Importazione**: la casella si importa nel campo del bene senza avvisi; le Sezioni II di EH si ricostruiscono e si
   confrontano con l'originale.

## Esiti

- Controllo ufficiale SUC13 locale positivo: codice 1 (coniuge dichiarante), 4, 1 con coniuge non dichiarante (EG9+EG7),
  5 e 8 con coniuge rinunciatario (tipo 4), riga con codice 3 per testamento, imponibile non intero arrotondato.
- Negativi del controllo: casella alterata da 1 a 4 (EF4 non piu' coerente); imponibile troncato.
- Dichiarazioni reali FNTLRT e DNZRME (copie in cartella temporanea, archivio temporaneo): importate e riesportate con lo stesso
  ImportoDaVersare (3.708,00 e 14.742,53), stessi QuotaValore e DirittoAbitazione, quadro EF e Sezione II di EH identici foglia
  per foglia. Il controllo ufficiale non e' stato eseguito sulle riesportazioni reali (allegati EG da riacquisire).

## Casi non coperti (blocco con motivo)

- Quadro EM (fabbricati tavolari), come per la prima casa.
- Codici 2/3/6/7 senza un immobile con codice 1 o 5; piu' immobili principali (errore) o contigui.
- Categorie A/11 e F/3 con i codici 1/2/5/6 (le fonti le ammettono, il modulo prima casa non le classifica).
- Casella e riga con codice 3 sullo stesso immobile (combinazione non descritta).
- Riga con codice 3 insieme a usufrutto/nuda proprieta' o su proprieta' superficiaria (3S); riga 3 per quote diverse da 1/1.
- Successioni aperte prima del 2025 per la riga con codice 3 (prospetto dei coefficienti, come l'usufrutto).
- Somma non intera dei valori quota degli immobili prima casa (EF4 col. 2) o con agevolazione G/M: resta bloccata come prima
  (l'arrotondamento provato col controllo riguarda solo l'imponibile EF1/EF9).
- Il caso «separazione per colpa con devoluzione per legge» resta bloccato a monte (il coniuge non puo' essere beneficiario).
