# Quadro ED e passivita' (pacchetto 8)

**Fonti**: XSD `fornituraSUC13_v1.xsd` (`QuadroED/Modulo/Passivita`, `Ripartizione_Type` con `Continuazione`, `RipartizioneSingola_Type`,
`CodiciPassivita`, annotazioni di `ProgressivoCespite` e di `Quota`); Fascicolo I pp. PDF 36-38 (quadro ED: deducibilita', codici, quota,
progressivo cespite, ripartizione e **Continuazione** con l'esempio «passivita' ripartita tra quattro eredi»), p. PDF 3 (titoli esenti).

## Implementato (accettato dal controllo SUC13 2.3.1 eseguito in locale il 2026-11-05, dati sintetici)

### 1. Ripartizione fra piu' di tre soggetti (Continuazione)
Un rigo ED ripartisce al massimo tre soggetti. Con piu' soggetti si barra `RipartizioneED/Continuazione` e gli altri vanno nella sezione
ripartizione del **rigo che segue**, senza ripetere i dati della passivita' (Fascicolo I p. PDF 38, esempio ED1/ED2). L'esportazione
(`esporta.quadro_ed`) genera i righi di continuazione (anche attraverso i moduli da tre righi); la mappa id -> posizione registra
`righi_continuazione`, come per i beni. Provati col controllo: 4, 5 e 7 destinatari (3+1, 3+2, 3+3+1 righi), e 4 soggetti per stirpi
(rappresentazione: 1/6, 1/6, 1/6, 1/2). **Importazione**: `importa.py` ricompone i righi di continuazione in una sola passivita'
(rifiuta una continuazione senza il rigo che segue o con dati di una nuova passivita').

### 2. Ripartizione da interfaccia e da MCP
Il dato e' `opzioni.telematico.passivita[id].ripartizione = [{persona_id, quota}]` (in alternativa a `persona_id` sul modello). La GUI ha la
tabella «Ripartizione» nel pannello della passivita' (aggiungi/rimuovi soggetti e quote, nessun limite a tre); da MCP si scrive con
`aggiorna_pratica` (sezione `opzioni`). Somma delle quote = 1/1, soggetti del quadro EA, nessun soggetto ripetuto.

### 3. Tipi di passivita' (CodiciPassivita 1-12)
Tutti i tipi 2, 4, 5, 6, 7, 8, 9, 10, 11, 12 (e gia' 1 e 3) sono esportati e **accettati dal controllo**. Regole applicate: tipo 2 massimo 1033 euro;
tipi 3, 4, 5, 7: cespite di riferimento obbligatorio (per il 3 immobile); altri tipi: cespite da non indicare; tipo 11: possesso non valorizzato
(valore del legato). Tipi non «liberi» (diversi da 1, 2, 11, 12): quote della ripartizione secondo l'Allegato 5 (anche per stirpi).
La documentazione delle passivita' (rigo EG5) e' obbligatoria con il quadro ED (gia' implementato).

### 4. Coerenza con le quote di legge
La ripartizione delle passivita' dei tipi non liberi deve coincidere con le quote di legge (`devoluzione_legge.quote_di_legge`, con tabelle,
rappresentazione e premorti): errore `QUOTA_DI_LEGGE` altrimenti. **Nota di prova**: il controllo ufficiale NON verifica queste quote nella
ripartizione delle passivita' (accetta anche quote scambiate fra soggetti): il vincolo viene dall'annotazione XSD di
`RipartizioneED/Ripartizione/Quota` ed e' imposto dall'esportazione, non dal controllo.

## Resta bloccato
- **Titoli esenti con passivita' collegata** (tipi 3, 4, 5, 7 con cespite EO tipo 3): il Fascicolo I p. PDF 36 rende deducibili i debiti per beni
  «compresi nell'attivo ereditario», ma a p. PDF 3 i titoli esenti sono «opzionali» e a «valenza esclusiva nei rapporti con gli operatori finanziari»;
  l'XSD li descrive «compreso nell'attivo» (Titoli_Type 3). L'Allegato di calcolo non tratta il caso e il controllo non e' un arbitro sulla deducibilita'
  (verifica la forma, non la norma). **Le fonti non bastano: resta non supportato** (motivo esplicito, nessun XML).
- Deducibilita' delle passivita' per tipo (debiti degli ultimi sei mesi, limiti mensili di mantenimento, documentazione di sussistenza): sono
  condizioni di merito a carico del professionista; il programma non le valuta.

**File**: `esporta.py` (quadro_ed, ripartizione_ed), `importa.py` (blocco ED), `tests/test_ed_passivita.py`.
