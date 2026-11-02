# Piano: testamento e legatari (testamento con soli eredi: fatto; legatari: non implementati)

Stato al 2026-11-02. **Nessuna regola qui sotto e' stata trasformata in codice.** Le citazioni sono le annotazioni dell'XSD ufficiale
come riportate in `docs/regole/mappa_xsd_albero.md` (numeri di riga di quel file). I valori numerici (quote, franchigie, aliquote per
legatari) vanno letti da Fascicolo I e dalle specifiche tecniche in `fonti/` con pagina, non dedotti.

## Perche' non e' un passo piccolo
Il tipo soggetto 2 (legatario) in EA vale solo con «Devoluzione per testamento» = 1 (o legge estera): riga 139. Quindi legatari e testamento
vanno fatti **insieme**, e toccano almeno questi punti:

| Punto | Fonte (albero XSD) | Cosa implica |
|---|---|---|
| Frontespizio: `DevoluzionePerTestamento`, sezione `Testamento` (pubblicazione, registrazione, testamento estero) | righe 31-46 | nuovi dati nel modello e nella GUI; date >= data decesso |
| `NumeroLegatari` = numero dei soggetti EA con tipo 2 | riga 52 | conteggio da persone con ruolo legatario |
| Codice carica 7 (esecutore testamentario), 3 (rappresentante di legatario) con `CodiceFiscaleRappresentato` | righe 68, 86 | nuovi casi del presentatore |
| EA tipo soggetto 2; PresenzaDichiarante / FlagAssenzaDichiarante con codice carica 2 | righe 139, 566-567 | EA, EH sez. I |
| Quote di legge (Allegato 5) valgono solo senza testamento | righe 215, 220, 284, 289, 317 | con testamento le quote sono libere: cambia la validazione delle devoluzioni |
| ER `TipoCespite` GD solo con successione testamentaria | riga 341 | sblocca beni oggi non coperti |
| EG: documento di testamento; EH: sezioni dedicate | matrice di copertura (EG, EH) | allegati e dichiarazioni aggiuntive |
| ED tipo 11 (legati e oneri), ripartizione libera | `devoluzione_legge.py` `TIPI_PASSIVITA_LIBERE` | tipo 11 oggi blocca |
| Calcolo: legatari esclusi dalla presunzione su denaro/gioielli/mobilia; franchigie e aliquote per legatario | matrice, voce "Calcolo" | **regole fiscali da leggere in guida p. 3-4 e Fascicolo I, con revisore** |

## Ordine proposto
1. Modello dati e GUI: devoluzione per testamento, sezione testamento, ruolo legatario (solo dati, con validazione di formato).
2. Esportazione frontespizio + EA con legatari, **senza** calcolo, finche' il calcolo blocca con `non_supportato`.
3. ED tipo 11 e ripartizioni libere.
4. Calcolo per legatari, dopo lettura delle fonti e revisione indipendente.
5. Ogni passo: test locali, XSD, controllo SUC13 locale (Java 8, JAR in `SUCCESSIONI_CONTROLLI_SUC13`), poi aggiornamento della matrice.

## Cosa NON si delega agli agenti gratuiti
Calcolo, quote, esportazione XML, regole di invio. I passi 1 (solo maschere) si possono delegare con file di sola lettura.

## Aggiornamento 2026-11-02
Fatto e provato (controllo ufficiale SUC13 locale, Java 8, dati sintetici; stesso esito del caso base: positivo con la sola anomalia 3345):
**successione testamentaria con soli eredi** (tipo soggetto 1): frontespizio `DevoluzionePerTestamento` + sezione `Testamento`
(pubblicazione e registrazione, ufficio da enumerazione XSD, serie `[1-4][A-Z]?`), EG rigo 2 (`TestamentoNum`/`TestamentoAll`, obbligatorio con
testamento e vietato senza), EH `PresenzaTestamento` con gli estremi di registrazione uguali al frontespizio, quote di devoluzione libere
(nessuna verifica Allegato 5). Test: `tests/test_telematico_testamento.py`, `tests/test_telematico_testamento_controllo.py`.
Restano: legatari (EA tipo 2 e rappresentanti, codici carica 2/3/7/9, calcolo per legatari), testamento estero con EG/EH, secondo testamento
in EH (`RegistrazioneTestamento` fino a 2), ED tipo 11, TipoCespite GD.

## Aggiornamento 2026-11-02 (sera): legatari persone fisiche
Letta la guida al calcolo (`GUIDA_CALCOLO` pag. 3-4): la franchigia dipende dal grado di parentela (non dalla qualifica); la presunzione su denaro,
mobilia e gioielli «si calcola solo se il soggetto NON e' legatario»; con qualifiche multiple la franchigia e' unica (non coperto).
Il calcolo era gia' predisposto; mancava lo sblocco in esportazione. Fatto: EA tipo soggetto 2 con devoluzione per testamento (errore di dato
senza testamento), regole sui gradi «per legge» limitate alla devoluzione per legge. Caso sintetico: legatario estraneo (grado 35), terreno 10.000 euro,
imposta dovuta con tempistica 1, riferimento entro 12 mesi: controllo SUC13 locale positivo (solo anomalia 3345), come il caso base.
Restano: rappresentanti di legatario (carica 3), esecutore (7), trustee (9), qualifiche multiple, ED tipo 11, testamento estero, secondo testamento.

## Aggiornamento 2026-11-02 (notte): ED tipo 11
Fascicolo I p. 38: per il tipo 11 il valore e' quello del legato; XSD (PossessoNumeratore/Denominatore): non valorizzare. Implementato con errore
`REGOLA_POSSESSO_TIPO_11` se il possesso e' indicato; ripartizione libera (gia' prevista). Corretta una perdita silenziosa: la riga senza denominatore
del possesso veniva scartata senza segnalazioni (ora solo per i tipi diversi da 11). Controllo SUC13 locale positivo (anomalia 3345 come il caso base).
