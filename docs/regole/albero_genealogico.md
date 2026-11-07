# Albero genealogico generato dai dati (quadro EG, rigo EG6)

**Fonti**
- Fascicolo I (`fonti/Istruzioni/Succ_FASCICOLO_I_Nov_23.pdf`) p. PDF 6, «Quali documenti occorrono»: l'albero genealogico
  deve far risultare nome, cognome, luogo e data di nascita del coniuge e dei soggetti beneficiari legati al defunto da vincoli
  di parentela.
- Fascicolo I p. PDF 49, quadro EG: allegazione sempre obbligatoria dell'albero (rigo EG6); allegati in PDF/A-1a, PDF/A-1b o
  TIF/TIFF, pena lo scarto.
- XSD SUC13 `QuadroEG/AlberoGenealogico` (`AlberoGenealogicoNum` = 1: un solo documento); descrizioni dei codici da
  `GradoParentela_Type` e `TipoSoggetto_Type` (lette dagli XSD, non scritte nel codice).

**Cosa fa** (`src/successioni/albero_genealogico.py`)
- Dai soggetti della pratica: defunto in alto (nome, nascita, codice fiscale, data del decesso), coniuge (grado 01) accanto,
  poi i rami discendenti (02, 04, 06, 08), ascendenti (03, 5A-9B), collaterali (10, 11, 15, 16, 20, 21, 27, ...), affini
  (12-14, 17-19, 23-26) e altri beneficiari (estranei, enti, legatari senza grado).
- Per ogni beneficiario: cognome e nome, luogo (provincia) e data di nascita, codice fiscale, grado con descrizione ufficiale,
  qualita' (erede, legatario, chiamato, rinunciatario, coniuge rinunciatario tipo 4).
- Rappresentazione: i soggetti con `rappresentato_cf` sono disegnati sotto il rappresentato. Se la pratica contiene una persona
  con quel codice fiscale (es. ruolo «altro» con `data_decesso`) se ne usano i dati («premorto/a il ...»); se il rappresentato
  e' un rinunciatario del quadro EA i rappresentanti stanno sotto di lui; altrimenti si mostra solo il codice fiscale con la
  dicitura «premorto/a o rinunciatario/a (non indicato nella pratica)».
- Piede di ogni pagina: data di redazione e dichiarante (presentatore); se manca: «non indicato nella pratica».
- **Non inventa**: i dati assenti (o «da confermare») sono scritti come non indicati e riepilogati in «Dati da completare»;
  il codice fiscale non viene usato per dedurre data o luogo di nascita.

**Allegato e PDF/A**: PDF con reportlab, conversione e validazione con `prepara_pdfa` (Ghostscript; conformita' solo con
veraPDF). Il PDF/A (o, se la conversione non riesce, il PDF con avviso) e' collegato all'unico rigo EG6; i file generati sono
marcati in `analisi.generato` (impronta dei dati rappresentati). Con dati invariati la generazione risponde `gia_aggiornato`;
dopo una modifica lo stato risulta «da rigenerare». Gli alberi generati non piu' usati si eliminano (si rigenerano).

**Albero caricato a mano**: se il rigo EG6 punta a un file non generato, la generazione risponde `conferma_richiesta` e non
cambia nulla; con la conferma (`sostituisci_manuale`) il rigo passa all'albero generato e il file manuale resta fra i documenti
della pratica (mai cancellato). Viceversa, caricando un file sul rigo EG6 dall'interfaccia, il file prende il posto
dell'albero presente (con conferma se era a sua volta manuale).

**Accesso**: interfaccia, quadro EG, sezione «Albero genealogico (rigo EG6)» con «Genera albero genealogico dai dati» e
anteprima (`GET/POST /api/pratiche/{pid}/albero-genealogico`, `GET /api/allegati/{aid}/file`); MCP
`successioni_genera_albero_genealogico` (scrittura, bloccato in sola lettura).

**Evidenza (2026-11-07, locale, dati sintetici)**: `tests/test_albero_genealogico.py` (figli, coniuge e figli, rappresentazione
con premorto e senza dati del rappresentato, fratelli e nipoti di fratello, rinunciatario con rappresentanti, dati mancanti,
collegamento EG6, rigenerazione, conferma per l'albero manuale, rotte web, PDF/A valido con veraPDF);
`tests/e2e/gui_albero.js`.

**Limiti**: impaginazione a elenco ad albero (non un grafo genealogico con tutte le generazioni); fratelli unilaterali non
distinti per linea paterna/materna oltre al codice; il rappresentato di secondo livello (stirpi su piu' livelli) e' mostrato
solo se presente come persona nella pratica; non verifica la coerenza fra grado e quote (resta alle regole di devoluzione);
non sostituisce la dichiarazione sostitutiva sullo stato di famiglia (rigo EG1) ne' il controllo del professionista.
