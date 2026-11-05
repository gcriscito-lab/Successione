# Stampa del modello ministeriale

**Metodo**: il PDF si ottiene con il codice Java ufficiale del componente di controllo SUC13 gia' configurato
(`SUCCESSIONI_CONTROLLI_SUC13`, `SUCCESSIONI_JAVA`): `SUCFornituraDocumentService` -> `SUCConverter.getDichiarazioneMap` ->
`PrintModel` (JasperReports), che sovrappone i valori ai PDF modello ufficiali del componente (`ResSUC13.jar`, `applconf/SUC/`).
Nessuna coordinata o modello e' copiato o riscritto nel repository. La stampa parte dallo STESSO XML del file telematico completo e
aggiornato (impronta registrata nel job `stampa_modello`).

**Driver**: `src/successioni/collegamenti/java/StampaModello.java` (+ classe compilata, Java 8), compilato con
`scripts/compila_stampa.py`. Adattatore: `collegamenti/stampa.py`; servizio: `stampa_modello` / `file_stampa_modello`; API
`POST /api/pratiche/{id}/stampa-modello` e `GET ...stampa-modello.pdf`; MCP `successioni_stampa_modello`; GUI vista File.

**Stati**: `stato_elaborati()["stampa_modello"]` = non_eseguita | aggiornata | obsoleta (obsoleta se cambia l'XML esportato).
Il download verifica l'impronta del PDF.

**Evidenza (2026-11-05, locale, dati sintetici)**: caso A10, 10 pagine (privacy, frontespizio, EA, EB, EC, ER, ED, EE/EF/EG, EH x2);
controllo visivo di frontespizio, EA, EB, EC, ER, ED, EE/EF/EG, EH; `tests/test_stampa_modello.py` verifica i valori principali
nel testo del PDF.

**Limiti noti**: allegati EG presenti solo come flag; non provati prima casa, riduzioni, EI/EL/EM/EN/EO/EP/EQ/ES e pagine
multi-modulo (piu' di 3 eredi); il convertitore emette messaggi non bloccanti (tabelle enum). Non e' una verifica con l'Agenzia,
non e' sottoscritta; la dicitura «conforme» non va usata sulla sola base della grafica (specifica §8).
