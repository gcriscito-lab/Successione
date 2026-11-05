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

## Ascendenti oltre i genitori (nonni, bisavi, trisavi), rinunce e altri parenti (pacchetto 10)

**Fonti**: Fascicolo I p. PDF 55 (Allegato 1: codici 05a/05b nonni, 07a/07b bisavi, 09a/09b trisavi, A = linea paterna, B = materna) e p. 69 (Allegato 5);
XSD `GradoParentela` (codici `5A`, `5B`, `7A`, `7B`, `9A`, `9B`; annotazione: l'ascendente deve essere maggiore di eta' del defunto).
Non c'e' un codice dei nonni «del defunto» con altro nome: sono i codici 5A/5B (i `14`, `19` sono nonno e bisavo del *coniuge*, affini).

**Regola implementata** (`devoluzione_legge.quote_di_legge`, `ASCENDENTI`):
- gli ascendenti oltre i genitori ereditano solo in mancanza di discendenti e di genitori; con i genitori presenti la configurazione non e' coperta;
- si considera solo il grado piu' vicino (nonni 2, bisavi 3, trisavi 4): se ci sono ascendenti di **entrambe le linee** allo stesso grado, meta' a ciascuna
  linea e dentro la linea in parti uguali; se ci sono solo di una linea, parti uguali. Esempi dell'Allegato: 1/4 x4; 1/4, 1/4 e 1/2; 1/2 e 1/2 (nonni paterni, il bisnonno non
  eredita);
- un ascendente di grado piu' lontano **non puo' stare nel quadro EA** (l'XSD vieta soggetti senza devoluzione): se compare, quote non verificate;
- con coniuge e/o fratelli il gruppo degli ascendenti vale come un solo «genitore» (tabelle p. 69-70, righe «Ascendente/i»): coniuge 2/3 + ascendenti 1/3;
  ascendenti + 1 germano 1/2 e 1/2, + 1 unilaterale 2/3 e 1/3, + 2 o piu' fratelli 1/2 e 1/2; coniuge + ascendenti + fratelli 8/12, 3/12, 1/12.

**Evidenza (2026-11-05, controllo SUC13 2.3.1 locale, dati sintetici)**: `tests/test_devoluzione_ascendenti_controllo.py`. Positivi (solo avviso 3345): quattro nonni;
tre nonni (1/4, 1/4, 1/2); solo nonni paterni; due bisavi; coniuge e nonni; nonno + germano; nonno + unilaterale; coniuge + nonno + germano; **due nonni + germano,
tre nonni + unilaterale, coniuge + due nonni + germano** (le righe «Ascendente/i» di p. 70 non dettagliano il caso plurale: il controllo accetta il gruppo come un solo
genitore). Negativi: quote alterate respinte (3117/3118). Test tabellari: `tests/test_devoluzione_legge_ascendenti.py`.

**Rinunce.** L'Allegato 5 non descrive l'accrescimento. Provato col controllo: con un figlio rinunciatario (tipo 3) e due figli beneficiari il controllo **calcola le quote
sui soli beneficiari** («valore corretto» 1/2 e 1/2) e respinge 1/3 e 2/3; coerente con l'esclusione dei rinunciatari dal calcolo (pacchetto «soggetti»).
Con rinunciatario e discendenti che lo rappresentano resta valida la rappresentazione per stirpi (sezione precedente).

**Non coperto, con motivo**: altri parenti oltre i fratelli (zii `16`, cugini `21`, ...): l'Allegato 5 dice solo che «la successione non ha luogo tra i parenti oltre il sesto
grado» e non da' le quote; la rappresentazione di ascendenti non esiste (si rappresentano solo discendenti); rinunce di ascendenti con accrescimento fra linee: non provato.