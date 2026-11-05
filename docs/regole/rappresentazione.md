# Successione per rappresentazione e premorti (quote di legge)

**Fonti**: Fascicolo I pp. PDF 18-19 (chi succede per rappresentazione; esempio: valore dell'immobile diviso per stirpi e poi fra i
rappresentanti di ciascuna stirpe; la rappresentazione opera all'infinito); XSD `fornituraSUC13_v1.xsd`, annotazioni di
`QuadroEA/.../SuccessionePerRappresentazione` (gradi ammessi 04, 06, 08, 15, 20, 27; obbligatoria per 04 e 15 con devoluzione
per legge; rappresentato = figlio 02 oppure fratello 10/11).

**Dati**: per ogni rappresentante, nella persona (o in `opzioni.telematico.persone[id]`): `rappresentato_cf` e
`rappresentato_grado`. Il rappresentato (premorto o rinunciatario) non e' un soggetto del quadro EA.

**Regola**: ogni figlio (o fratello) presente e ogni gruppo di rappresentanti dello stesso rappresentato e' una stirpe che conta
come un figlio (fratello, con peso 2 il germano e 1 l'unilaterale); la quota della stirpe si divide in parti uguali fra i suoi
rappresentanti. Per le combinazioni con coniuge, genitori e fratelli valgono le tabelle di Allegato 5 pp. 69-70.

**Evidenza (2026-11-05, locale, dati sintetici)**: `tests/test_devoluzione_legge_tabelle.py` (esempio ministeriale 10.000/30.000
incluso) e `tests/test_devoluzione_controllo_ufficiale.py`: il controllo SUC13 2.3.1 accetta l'esempio ministeriale, figlio vivo +
nipoti di un figlio premorto, coniuge + figlio + nipoti, e respinge le quote alterate.

**Non coperto/da provare**: nipoti di fratelli (10/11) non ancora provati col controllo; rinunce come soggetti (tipo 4); nonni e
altri ascendenti; stirpi su piu' livelli con rappresentati diversi dal figlio/fratello diretto.
