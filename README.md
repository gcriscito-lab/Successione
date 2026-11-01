# Successioni

Progetto per un'applicazione locale Windows destinata alla compilazione delle dichiarazioni di successione e delle domande di volture catastali.

Il repository contiene i materiali di partenza e le istruzioni operative. L'applicazione è da sviluppare.

## Inizia qui

1. Leggi `CLAUDE.md`.
2. Esegui dalla radice `python scripts/verifica_materiali.py`.
3. Leggi `docs/01_PROMPT_CLAUDE_CODE.md` e `docs/02_SPECIFICA_E_COLLAUDO.md`.
4. Procedi con il codice collaudabile nell'ambiente corrente; usa `docs/COLLAUDO_CLOUD_WINDOWS.md` per le prove da completare su Windows o con servizi autenticati.

I materiali sono nel repository. Non occorre accedere al PC del committente, a Google Drive o a cartelle di caricamento per iniziare lo sviluppo.

## Requisiti principali

- Compilazione manuale e tramite MCP, sullo stesso archivio e con le stesse regole.
- Conversione locale PDF/A, con verifica del risultato e conservazione dell'originale.
- Acquisizione delle risultanze catastali tramite Entratel e importazione selettiva dei beni.
- Preparazione/invio e raccolta di ricevute ed esiti tramite collegamenti ufficiali verificati.

L'AI rimane esterna: nessun LLM, chat o chiave API AI dentro il programma.

## Materiali

`fonti/` contiene 23 file ministeriali forniti dal committente: 8 PDF, 13 XSD e 2 avviatori JNLP. Le relative impronte sono in `fonti/manifest.json`. Il manuale commerciale storico SEAC 2021 non è incluso e non è necessario per avviare il progetto.

I documenti e i componenti dell'Agenzia rimangono materiali dei rispettivi titolari; la loro presenza non autorizza a presentare il progetto come un prodotto ufficiale dell'Agenzia. Gli avviatori JNLP non sono sorgenti dell'applicazione.

Non inserire nel repository pratiche reali, credenziali, certificati privati, cookie o ricevute con dati personali. Usa dati sintetici per lo sviluppo locale.
