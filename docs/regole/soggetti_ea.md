# Soggetti del quadro EA: rinunciatari, enti, residenza estera, soggetto su piu' righi

**Fonti**: XSD `fornituraSUC13_v1.xsd` (annotazioni di `QuadroEA/Modulo/Soggetto`: `CodiceFiscale`, `TipoSoggetto`, `Rinuncia`,
`GradoParentela`, `PortatoreHandicap`, `ResidenzaEstera`; `QuadroEH/.../Rinuncia`, `PresenzaRinuncia`); Fascicolo I pp. PDF 17-18
(tipo soggetto, rinuncia, residente all'estero, trust); Guida di calcolo p. 3 (stesso soggetto su piu' righi: franchigia unica) e p. 10 (esenti).

## Implementato (accettato dal controllo SUC13 2.3.1 eseguito in locale il 2026-11-05, dati sintetici)
| Funzione | Dati sulla persona (`opzioni.telematico.persone[id]`) | Regola |
|---|---|---|
| **Rinunciatario (tipo 3)** | `tipo_soggetto: "3"`, `rinuncia: true`, `rinuncia_estremi {ufficio_registrazione, serie, numero_registrazione, sottonumero_registrazione, data_registrazione}` | EA: `Rinuncia=1`; EH rigo 8: `PresenzaRinuncia` con rigo/modulo del soggetto ed estremi dell'atto. Mai per l'erede (tipo 1); non per il dichiarante. |
| **Coniuge rinunciatario (tipo 4)** | `tipo_soggetto: "4"` (la rinuncia e' implicita), stessi `rinuncia_estremi`; grado 01, stato civile 2/3/5/7; uno solo | come sopra |
| **Piu' rinunciatari** | uno per volta | il primo nel primo modulo EH; dal secondo, uno per modulo (`Modulo/SezioneI_DichSost/PresenzaRinuncia`) |
| **Residenza estera** | `residenza_estera {codice_stato, stato, stato_federato, localita, indirizzo}` | `CodiceStatoEstero` di 3 caratteri validato sulla tabella `stati_esteri_cod.res` del componente di controllo (letta a runtime, non copiata); `StatoEstero` (nome) e `IndirizzoEstero` obbligatori |
| **Enti e denominazione** | `denominazione` + `grado_parentela` 35, 37, 38 o 39 (codice fiscale a 11 cifre) | `Denominazione` al posto dei dati anagrafici (anche nell'elenco EH); solo con testamento (con la legge i gradi 35/37/38/39 sono vietati dall'XSD); imposta di successione nulla per 37-39 (guida p. 10); righe degli enti fuori dalle basi EF1/EF9 (Fascicolo I pp. 40, 43) |
| **Soggetto su piu' righi** | due persone con lo stesso codice fiscale (es. erede + legatario) | stesso grado e stessa disabilita', tipi diversi; 1, 3 e 4 non coesistono. L'elenco EH conta i soggetti, non i righi (controllo 2092). Calcolo: franchigia unica scomputata in sequenza |

**Effetti sul resto**: i rinunciatari non hanno devoluzioni (errore `DEVOLUZIONE_RINUNCIATARIO`), restano fuori dalle quote di legge e dalla
regola «ogni soggetto compare in una devoluzione»; il calcolo dell'imposta di successione non li blocca piu'.

**Soggetto su piu' righi nel calcolo**: la guida dice che la franchigia e' unica e va scomputata «prima su una quota e poi il restante importo
sulle successive», senza fissare l'ordine. Si calcolano tutti gli ordini e il caso si accetta solo se l'imposta non ne dipende; altrimenti
il quadro EF non si genera con il motivo «l'imposta dipende dall'ordine ... che la guida non definisce».

## Resta bloccato (con motivo esplicito nell'export)
- **Trust (tipo 5)**: servono le sezioni Trust del quadro EA, TrustDisab, EF3bis, il dichiarante con carica 9, l'atto istitutivo in EG e il
  perimetro del modello telematico (Fascicolo I p. 17): non provato col controllo.
- **Altro (tipo 6)**: con questo tipo non possono esserci altri soggetti nel quadro.
- **Stato (grado 36)**: l'XSD vieta di indicarlo nelle devoluzioni; senza devoluzioni il quadro dei beni non e' compilabile.
- **Rinuncia del legatario (tipo 2)**: ammessa dall'XSD, non coperta dalle fonti sul modo di dichiararla.
- **Soggetto su piu' righi con tipi diversi da 1-4**, e casi in cui l'imposta dipende dall'ordine di scomputo della franchigia.
- Quote di legge con rinunciatari quando restano tipi misti non coperti dalle tabelle (l'export segnala `QUOTE_DI_LEGGE_NON_VERIFICATE`).

**Evidenza**: `tests/test_soggetti_ea.py` (23 test): rinuncia tipo 3, tipo 4 e due rinunciatari, residenza estera (Francia, USA con stato federato,
Germania), erede+legatario sullo stesso soggetto, enti gradi 37, 38, 39, ente co-erede del fabbricato, denominazione con grado 35: tutti
con controllo ufficiale positivo (solo l'avviso 3345 sull'attestazione); negativi: rinuncia tolta dal quadro EA (respinta), codice Stato estero
inesistente (respinto dall'export).
