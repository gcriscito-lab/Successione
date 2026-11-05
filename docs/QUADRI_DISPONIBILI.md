# Quadri disponibili

Stato: **beta tecnica**. Questa tabella riassume la copertura attuale dei quadri per il professionista. Non sostituisce la matrice di copertura completa (`docs/MATRICE_COPERTURA.md`) e non attesta la conformità all'Agenzia delle Entrate.

**Legenda stati:**
- **Controllo locale**: il caso documentato supera il controllo ufficiale SUC13 2.3.1 eseguito in locale (dati sintetici).
- **Verifica ufficiale**: servizi dell'Agenzia delle Entrate (non ancora disponibile).

| Quadro | Cosa copre oggi (in una riga) | Cosa non copre (in una riga) |
|---|---|---|
| Busta / Intestazione | Messaggio, codici fornitore, identificativo, SpazioUtente. | SpazioServizioTelematico (riservato al servizio). |
| Frontespizio | CF defunto, prima dichiarazione o sostitutiva codici 1 e 2, devoluzione per legge/testamento (soli eredi), beneficiari, dati defunto, presentatore (carica 1), firma, impegno a trasmettere. | Integrative (codice 3), legatari/rappresentanti, legge estera, eventi eccezionali, beneficio d'inventario, residenza estera, cariche 2-9, rappresentato, Versamento/F24, ImportoDaVersare, campi servizio, lingua. |
| EA | Eredi (1), chiamati (3), legatari (2, solo con testamento) persone fisiche, grado di parentela, disabilità, moduli da 3. | Rinunciatari (4), trust (5), altro (6), rinuncia, denominazione enti, residenza estera, rappresentazione, soggetto su più righi. |
| EB | Terreni in Italia non tavolari, natura T, superficie, reddito dominicale, possesso, diritto, valore, devoluzione con continuazione. | Estero (EE), nature diverse da T, bene aziendale, discordanze/passaggi (EI), imposta estera, valore precedenti successioni, agevolazioni/riduzioni. |
| EC | Fabbricati in Italia non tavolari, sezione, zona, categoria, classe, consistenza, rendita, possesso, diritto, valore, devoluzione con continuazione. | Estero, rendita proposta, D10 senza valore, bene aziendale, graffati, diritto di abitazione, EI, imposta estera, agevolazioni (prima casa P/Z/X/Y ecc.). |
| ED | Tipo, descrizione, estremi, possesso, valore, progressivo cespite (tipi 3/4/5/7), ripartizione a un soggetto. | Continuazione oltre 3 soggetti. Tipo 11 (legato/onere) implementato ma con limitazioni sulla ripartizione libera e valore del legato. |
| EE | totali di EE calcolati dai quadri esportati: immobili (EB, EC, EL, EM), aziende (EN), titoli (EO), aerei e navi (EP, EQ), altri beni (ER), attivo, passivo, asse netto. | esclusioni per agevolazione A e bene aziendale; titoli esenti (EO tipo 3); beni esteri. |
| EF | Sezioni imposta ipotecaria, catastale, tassa ipotecaria, bollo e V-bis calcolate dai quadri esportati (anche in piu' comuni, con il componente di controllo configurato), EF19, ImportoDaVersare, Versamento. | Agevolazioni, soli terreni, proporzionale < fissa, più comuni, copia conforme, crediti, sostitutive con rimborso o tardive con imposta aggiuntiva, sanzioni, rateazione. |
| EG | EG1, EG5, EG6, EG7, EG8 con ImageData da allegati; obbligatorietà albero (EA), passività (ED), documento d'identità. | Testamento, inventario, estero, agevolazioni/riduzioni; PDF/A non verificato dall'export. |
| EH | Sezione I: presentatore, defunto deceduto, dichiarante carica 1, eredi EA, assenza testamento/interdetti/rinunce, FlagPassivita, firma. | Sezioni II-IV, separazione, unione civile, disabili/interdetti, rinunce, morte presunta. |
| EI_new | — | Voltura: discordanze e passaggi intermedi. |
| EL, EM | Terreni e fabbricati in province BZ, TN, GO, TS (o comuni tavolari BL, UD, BS, VI); luogo tavolare, progressivo cespite mutuo, frontespizio CasiParticolari. | Graffati (EM), rendita proposta, immobili aziendali, mix di comuni (circoscrizione richiede elenco conservatorie); instradamento comuni BL/UD/BS/VI richiede tabella non disponibile (flag manuale). |
| EO | Titoli quotati (1), non quotati (2), fondi comuni (4) con valore, quantità, tipo, data documento, diritto, devoluzione; totale EE; calcolo QE. | Titoli esenti (3), beni esteri, riduzioni art. 25, codice ufficio e registrazione in Anagrafe Tributaria del CF emittente. |
| EP, EQ | Aeromobili e navi con valore, diritto, devoluzione; totale EE; righe EH (EH11, EH12) con un solo mezzo per tipo; calcolo QE. | Beni esteri, riduzioni art. 25, più navi o aeromobili in EH (secondo modulo). |
| EN | Aziende con denominazione, CF, diritto 1/2, valore, devoluzione; totale EE; EH9 (data deposito, camera di commercio); calcolo QE. | Immobili aziendali, inventario (EH10, EG), beni esteri, riduzioni art. 25, agevolazioni A/D/Q/G. |
| ER | Tipi cespite BI, CR, DN, AB; descrizione; possesso; diritto 1/2; valore; devoluzione con continuazione; moduli da 4. | GD, CR senza valore, beni esteri, imposta estera, valore precedenti successioni, agevolazioni A/L. |

**Nota:** I quadri marcati come "parziale" o "non coperto" bloccano l'export se selezionati nella pratica. Il "controllo locale" indica che il caso sintetico ha superato il controllo SUC13 2.3.1 in locale, ma non garantisce l'accettazione da parte dell'Agenzia delle Entrate.