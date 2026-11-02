# Piano: testamento e legatari (non implementato)

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
