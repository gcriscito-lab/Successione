# Circoscrizioni di pubblicita' immobiliare (EF15, EF16)

**Fonti**: XSD `fornituraSUC13_v1.xsd`, annotazione `SezioneIII_TassaIpotecaria/Circoscrizioni_Numero` (numero di
circoscrizioni individuate in base al codice del comune; elenco delle conservatorie sul sito dell'Agenzia); Fascicolo I
p. PDF 44 (stesso comune = una circoscrizione).

**Tabella**: non e' nelle fonti del repository. Si legge a runtime da `comuni_conservatorie.res`, contenuta in
`controlliXMLREG2013.jar` del componente di controllo SUC13 configurato (`SUCCESSIONI_CONTROLLI_SUC13`); non e' copiata nel
programma. Righe `NOME*CODICE_CATASTALE*UFFICIO*PROVINCIA*CIRCOSCRIZIONE`.

**Regola**: numero di circoscrizioni = numero di valori distinti della colonna CIRCOSCRIZIONE per i comuni degli immobili
EB/EC. EF15 = n x 120 euro, EF16 = n x 85 euro. Comuni diversi con la stessa circoscrizione contano una volta (es. Acerra e
Caserta, CE00). Un solo comune: una circoscrizione, anche senza componente.

**Limiti**: senza componente configurato, immobili in piu' comuni restano non esportabili (motivo esplicito); comuni assenti
dalla tabella o tavolari (`-`) in EB/EC: non coperti.

**Evidenza (2026-11-05, locale, dati sintetici)**: `tests/test_conservatorie.py`; il controllo SUC13 2.3.1 accetta i casi con
1 e 2 circoscrizioni e respinge il numero alterato.
