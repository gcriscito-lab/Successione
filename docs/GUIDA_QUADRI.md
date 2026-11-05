# Guida alla compilazione dei quadri

Questa guida spiega, in modo sintetico, come compilare ogni quadro dell'interfaccia telematica per le dichiarazioni di successione. Ogni sezione indica: a cosa serve il quadro, quali campi del modello vanno compilati, un esempio pratico e cosa NON è supportato.

---

## Busta / Intestazione

**A cosa serve:** Dati di identificazione del fornitore e del servizio.

**Campi compilabili:**
- `messaggio`
- `tipo_fornitore`
- `spazio_utente`
- `identificativo`

**Esempio:** CF fornitore = `RSSMRA70A41H501J`, tipo fornitore = `1`, codice fornitura SUC13 = `10`.

**Non supportato:**
- spazio_servizio_telematico (riservato al servizio).

---

## Frontespizio

**A cosa serve:** Dati principali della successione: defunto, presentatore, eredi, stato civile.

**Campi compilabili:**
- `persone` (con `ruolo = defunto` e `ruolo = presentatore`)
- `data_decesso`
- `sesso`
- `comune_decesso`
- `provincia_decesso`
- `grado_parentela`

**Esempio:** Defunto `RSSMRA40A01H501K`, presentatore `RSSNNA70A41H501J` con carica 1.

**Non supportato:**
- integrative (codice 3), testamento con legatari o rappresentanti (EA tipo 2/3, carica 7/9), legge estera, eventi eccezionali, data opzione, beneficio d'inventario, residenza estera, cariche 2-9, rappresentato, casi particolari, Versamento/F24, ImportoDaVersare, campi servizio, lingua.

---

## EA - Eredi, chiamati, legatari e altri soggetti

**A cosa serve:** Registrare le persone coinvolte nella successione (eredi, chiamati, legatari).

**Campi compilabili:**
- `persone` (con `ruolo = erede`, `ruolo = legatario`)
- `cognome`
- `nome`
- `codice_fiscale`
- `data_nascita`
- `luogo_nascita`
- `relazione_con_defunto`
- `grado_parentela`

**Esempio:** Erede `RSSNNA70A41H501J` (Anna Rossi), figlia (grado 02).

**Non supportato:**
- rinunciatari (4), trust (5), altro (6), rinuncia, denominazione (enti), residenza estera, rappresentazione, soggetto su più righi.

---

## EB - Attivo ereditario catasto terreni

**A cosa serve:** Registrare i terreni in Italia non tavolari.

**Campi compilabili:**
- `beni` (con `tipo = terreno`)
- `comune`
- `sezione`
- `foglio`
- `particella`
- `subalterno`
- `diritto`
- `quota_defunto`
- `valore`
- `rendita`
- `natura`
- `tipologia_terreno`
- `reddito_dominicale`

**Esempio:** Terreno a Roma, sezione A, foglio 10, particella 20, valore 15000, diritto proprietà.

**Non supportato:**
- estero (EE), natura diversa da T, bene aziendale, discordanza/passaggi (EI), imposta estera, valore precedenti successioni, agevolazioni/riduzioni.

---

## EC - Attivo ereditario catasto fabbricati

**A cosa serve:** Registrare i fabbricati in Italia non tavolari.

**Campi compilabili:**
- `beni` (con `tipo = fabbricato`)
- `comune`
- `sezione`
- `foglio`
- `particella`
- `subalterno`
- `categoria`
- `diritto`
- `quota_defunto`
- `rendita`
- `valore`

**Esempio:** Fabbricato a Roma, sezione B, foglio 100, particella 200, categoria A/2, valore 126000.

**Non supportato:**
- estero, rendita proposta (DeterminazioneRendita), D10 senza valore, bene aziendale, graffati, diritto di abitazione, EI, imposta estera, agevolazioni (prima casa P/Z/X/Y ecc.).

---

## ED - Passività ed altri oneri

**A cosa serve:** Registrare le passività del defunto (debiti, oneri).

**Campi compilabili:**
- `passivita`
- `descrizione`
- `importo`
- `persona_id`
- `tipo`
- `estremi_documento`
- `data_documento`
- `possesso`

**Esempio:** Mutuo ipotecario da 30000 euro, tipo 3, ripartito 1/2 a ciascun erede.

**Non supportato:**
- continuazione della ripartizione oltre 3 soggetti.
- Per il tipo 11 (legato o onere) il possesso non si indica: il valore e' quello del legato.

---

## EE - Prospetto riepilogativo asse ereditario

**A cosa serve:** Riepilogo dei totali delle dichiarazioni.

**Campi compilabili:** nessuno: il prospetto si calcola dai valori di `beni` e `passivita` al momento dell'esportazione.

**Esempio:** Totale beni 161000, totale devoluzioni 161000, totale passività 32000.

**Non supportato:**
- esclusioni per agevolazione A e bene aziendale; titoli esenti (EO tipo 3); beni esteri.

---

## EF - Liquidazione delle imposte e altri tributi

**A cosa serve:** Calcolo e registrazione delle imposte da versare.

**Campi compilabili:**
- `opzioni.telematico.dichiarazione`
- `importo_da_versare`
- `iban`
- `cf_titolare`

**Esempio:** Importo da versare 44.132 euro, IBAN `IT57A0123456789000000001234`.

**Non supportato:**
- agevolazioni, soli terreni, proporzionale < fissa, copia conforme, crediti, sostitutive con rimborso o tardive con imposta aggiuntiva, sanzioni, rateazione. Le sostitutive codici 1 e 2 sono coperte (vedi `docs/regole/sostitutiva.md`).

---

## EG - Elenco documenti, certificati e dichiarazioni sostitutive

**A cosa serve:** Allegare documenti di supporto (certificati, atti, alberi genealogici).

**Campi compilabili:**
- `documenti_ref`
- `allegato_id`
- `tipo_eg`
- `finalita`
- `persona_id`

**Esempio:** Albero genealogico (`AlberoGenealogico`), fatture spese mediche (`DocumentiPassivita`).

**Non supportato:**
- testamento, inventario, estero, agevolazioni/riduzioni; PDF/A non verificato dall'export.

---

## EH - Dichiarazioni sostitutive, agevolazioni e riduzioni

**A cosa serve:** Dichiarazioni aggiuntive per il calcolo dell'imposta.

**Campi compilabili:**
- `opzioni.telematico.dichiarazione`
- `dichiara_copie_conformi`

**Esempio:** Dichiarazione che le copie sono conformi (`dichiara_copie_conformi = True`).

**Non supportato:**
- sezioni II-IV, separazione, unione civile, disabili/interdetti, rinunce, morte presunta.

---

## EI - Dichiarazioni utili alla voltura catastale

**A cosa serve:** Dati per la voltura catastale (non ancora implementati).

**Campi compilabili:**
- Nessuno (quadro non supportato).

**Esempio:** —

**Non supportato:**
- tutto (discordanze e passaggi intermedi).

---

## EL - Attivo ereditario terreni sistema tavolare

**A cosa serve:** Registrare terreni con partita tavolare in province con sistema tavolare.

**Campi compilabili:**
- `beni` (con `tipo = terreno`, `provincia = BZ` o `sistema_tavolare = 1`)
- `comune`
- `foglio`
- `particella`
- `partita_tavolare`
- `valore`

**Esempio:** Terreno a Bolzano, partita tavolare 1234, valore 8000 euro.

**Non supportato:**
- graffati (EM), rendita proposta, immobili aziendali, mix di comuni (la circoscrizione richiede l'elenco delle conservatorie); l'instradamento dei comuni tavolari di BL, UD, BS, VI richiede la tabella dei comuni (non nelle fonti): flag manuale.

---

## EM - Attivo ereditario fabbricati sistema tavolare

**A cosa serve:** Registrare fabbricati con partita tavolare in province con sistema tavolare.

**Campi compilabili:**
- `beni` (con `tipo = fabbricato`, `provincia = BZ` o `sistema_tavolare = 1`)
- `comune`
- `foglio`
- `particella`
- `categoria`
- `valore`

**Esempio:** Fabbricato a Bolzano, partita tavolare 5678, categoria A/2, valore 90000 euro.

**Non supportato:**
- graffati (EM), rendita proposta, immobili aziendali, mix di comuni (la circoscrizione richiede l'elenco delle conservatorie); l'instradamento dei comuni tavolari di BL, UD, BS, VI richiede la tabella dei comuni (non nelle fonti): flag manuale.

---

## EN - Aziende

**A cosa serve:** Registrare le aziende di cui il defunto è titolare.

**Campi compilabili:**
- `beni` (con `tipo = azienda`)
- `descrizione`
- `codice_fiscale_emittente`
- `valore`

**Esempio:** Azienda `Alfa Impresa Individuale`, CF `00000000018`, valore 20000 euro.

**Non supportato:**
- immobili aziendali (`BeneAziendale`, `ImmobiliAziendali`), inventario (EH10, EG), beni esteri, riduzioni art. 25, agevolazioni A/D/Q/G.

---

## EO - Azioni, Obbligazioni, Altri titoli, Quote sociali

**A cosa serve:** Registrare i titoli di investimento del defunto.

**Campi compilabili:**
- `beni` (con `tipo = titolo`)
- `tipo_titolo`
- `descrizione`
- `quantita`
- `valore`
- `codice_titolo`
- `codice_fiscale_emittente`

**Esempio:** Azioni non quotate, 100 quote, valore totale 10000 euro.

**Non supportato:**
- titoli esenti (3, `ValoreEsente`), beni esteri, riduzioni art. 25 (`ValorePrecSucc`), codice ufficio e registrazione in Anagrafe Tributaria del CF emittente (verificati solo dal controllo ufficiale).

---

## EP - Aeromobili

**A cosa serve:** Registrare gli aeromobili del defunto.

**Campi compilabili:**
- `beni` (con `tipo = aeromobile`)
- `marca_modello`
- `anno_costruzione`
- `nazionalita`
- `anno_immatricolazione`
- `numero_immatricolazione`
- `valore`

**Esempio:** Aeromobile `X1`, anno 1998, nazionalità italiana, immatricolazione 2005, valore 30000 euro.

**Non supportato:**
- beni esteri, riduzioni art. 25 (`ValorePrecSucc`), più navi o aeromobili in EH (secondo modulo).

---

## EQ - Navi e Imbarcazioni

**A cosa serve:** Registrare le imbarcazioni del defunto.

**Campi compilabili:**
- `beni` (con `tipo = nave`)
- `tipo_unita`
- `nazionalita`
- `numero_iscrizione`
- `lunghezza`
- `stazza`
- `valore`

**Esempio:** Barca a vela, tipo 1, nazionalità italiana, iscrizione 98765, lunghezza 9m, valore 12000 euro.

**Non supportato:**
- beni esteri, riduzioni art. 25 (`ValorePrecSucc`), più navi o aeromobili in EH (secondo modulo).

---

## ER - Rendite, crediti e altri beni

**A cosa serve:** Registrare altre forme di attivo ereditario (disponibilità finanziaria, crediti).

**Campi compilabili:**
- `beni` (con `tipo = disponibilita_finanziaria`)
- `descrizione`
- `valore`

**Esempio:** Conto corrente con saldo 20000 euro.

**Non supportato:**
- nessuno specifico per questo quadro.

---

## Note

- I nomi dei campi sono quelli definiti in `schema.py`.
- Gli esempi sono sintetici e basati sui casi di test in `tests/telematico_casi.py`.
- Le informazioni sulle aliquote, franchigie e regole fiscali non sono riportate in questa guida.
- Per verificare la correttezza del documento, esegui: `python scripts/verifica_doc_quadri.py docs/GUIDA_QUADRI.md`.