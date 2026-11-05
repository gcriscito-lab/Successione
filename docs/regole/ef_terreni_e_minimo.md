# EF: imposta proporzionale inferiore alla fissa e soli terreni

**Fonti**: XSD `fornituraSUC13_v1.xsd`, annotazioni di `ImpostaIpotecariaDovuta`, `ImpostaCatastaleDovuta` e
`ImpostaProporzionale_Imposta` (EF1 ed EF9); Fascicolo I pp. PDF 40 e 43.

**Minimo di 200 euro** (fabbricati o terreni edificabili): la colonna 2 dei righi EF1/EF9 riporta l'imposta calcolata (2% / 1%);
il minimo di 200 euro vale nel totale dovuto (EF5/EF11). Il Fascicolo dice «indicare 200 euro» nella colonna 2, ma il controllo
SUC13 2.3.1, eseguito in locale il 2026-11-05, respinge quella forma («valore corretto» = imposta calcolata) e accetta
l'annotazione XSD. Prevale quindi l'XSD.

**Soli terreni non edificabili senza agevolazioni ne' riduzioni** (tipologia 3, solo quadro EB): valore fiscale = somma dei
redditi dominicali x quota del defunto x 112,5. Se e' inferiore alla somma delle imposte proporzionali, EF1 = 2/3 e EF9 = 1/3 del
valore fiscale (arrotondati all'euro); altrimenti imposta ordinaria con minimo 200 nella colonna 2. Reddito dominicale mancante:
non determinabile, nessun XML. Ogni bene si conta una volta anche se ha piu' righe di devoluzione.

**Evidenza**: `tests/test_ef_minimo_fisso.py` e `tests/test_ef_soli_terreni.py`, con controllo ufficiale locale positivo su tutti
i casi e respinta la variante «200 nella colonna 2».
