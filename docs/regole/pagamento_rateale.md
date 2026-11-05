# Pagamento rateale dell'imposta di successione (EF18ter col. 2-3)

**Fonti**: XSD `fornituraSUC13_v1.xsd`, annotazioni di `SezioneVBis_ImpostaSuccessione/ImpostaCalcolata/PagamentoRateale`,
`Acconto`, `TotaleDaVersare`; Fascicolo I p. PDF 48 (righi EF18ter e EF19).

**Dati** (`opzioni.telematico.dichiarazione`): `pagamento_rateale` = numero di rate trimestrali (1-12), `acconto` = euro interi.
Il vecchio valore booleano di `pagamento_rateale` non e' piu' ammesso.

**Regole implementate**
- acconto non inferiore al 20% e non superiore all'imposta da versare (EF18bis col. 5);
- residuo (imposta da versare - acconto) non inferiore a 1.000 euro;
- residuo fino a 20.000 euro: al massimo 8 rate; oltre: al massimo 12;
- EF19: con tempistica 2 si somma l'acconto (al posto dell'intera imposta); con tempistica 1 non si somma nulla dell'imposta di
  successione;
- rateazione senza imposta da versare: errore.

**Non coperto**: sanzioni e interessi (Sezione VI: il tasso legale per anno non e' nelle fonti), tardive con imposta dovuta,
trust (carica 9), calendario delle rate (calcolo e F24 delle singole rate).

**Evidenza (2026-11-05, locale, dati sintetici)**: `tests/test_rateazione.py`; il controllo SUC13 2.3.1 accetta la rateazione con
tempistica 1 e 2.
