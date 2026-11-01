# Revisione esterna Codex — Successioni, beta 1

Data: 1 novembre 2026. Repository: gcriscito-lab/Successione.
Branch richiesto: claude/successioni-dichiarazioni-app-fhcwbe.
Revisione eseguita sul commit congelato, con checkout detached.

## 1. Esito

**NON OK per un primo percorso completo da GUI/MCP e per l'uso professionale.** Sono dimostrati difetti di integrazione dell'export, perdita di modifiche nell'interfaccia e accettazione come completi di casi fiscalmente o tecnicamente non validati. La base resta utile per sviluppo e collaudo.

Output effettivo di git rev-parse HEAD:

    2e2b503d1bb4a22c6ae499600846e2c70d5bdb56

Non attribuisco al progetto difetti nuovi per i limiti dichiarati: veraPDF, Desktop Telematico, servizi Entratel, invio/ricevute reali, client Claude Windows, quadri esclusi e dubbio 82,0875/82,08. I rilievi sotto riguardano comportamenti ulteriori, riprodotti sul codice indicato.

Non ho letto docs/REVISIONE_INDIPENDENTE.md né docs/RISPOSTA_ALLA_REVISIONE.md. Non ho modificato il codice, le fonti o i test, non ho usato credenziali e non ho effettuato trasmissioni. Gli esperimenti hanno utilizzato esclusivamente fixture pubbliche/sintetiche e archivi temporanei separati. Nessun commit o push di questa revisione.

## 2. Quadrature eseguite

### Ambiente e comandi

Ambiente effettivo: Windows, PowerShell, Python 3.14.4; non il container Linux/Python 3.13 dello sviluppo. Dipendenze installate nell'ambiente isolato con la specifica richiesta: mcp 2.3.0, lxml 6.1.3, pypdf 6.21.4, reportlab 5.1.0, starlette 1.10.0, pytest 9.2.0. Ghostscript, qpdf, pdftotext e veraPDF non disponibili nel PATH di prova; componenti ufficiali completi e pacchetto Windows non configurati.

Comandi significativi realmente eseguiti, dalla radice del checkout:

    git fetch origin claude/successioni-dichiarazioni-app-fhcwbe
    git checkout --detach 2e2b503
    git rev-parse HEAD
    python -m venv .venv
    .venv/Scripts/python.exe -m ensurepip --upgrade --default-pip
    .venv/Scripts/python.exe -m pip install -e ".[test]"
    .venv/Scripts/python.exe scripts/verifica_materiali.py --check-xsd
    .venv/Scripts/python.exe -m pytest -q -rs -p no:cacheprovider --basetemp ../pytest_codex_beta1_full

Per i file temporanei sono stati impostati TEMP/TMP sulla cartella di lavoro; PYTHONUTF8=1 e PYTHONDONTWRITEBYTECODE=1. Il primo avvio nell'ambiente limitato è rimasto in attesa durante la creazione del socketpair di asyncio: una prova isolata con faulthandler lo ha localizzato in socket.accept, prima dell'applicazione. La suite completa riportata qui è quella successiva, eseguita con i processi locali di prova abilitati. I processi del tentativo interrotto sono stati fermati.

L'installazione editable ha rigenerato metadati già tracciati in src/successioni.egg-info: sono stati ripristinati da HEAD. Prima della stesura di questo rapporto, git diff --exit-code era pulito.

### Risultati effettivi

- **passato**: 23 fonti integre, cioè 8 PDF, 13 XSD e 2 JNLP; compilazione dello schema principale con le dipendenze.
- Suite completa: **207 passati, 34 saltati, 5 falliti, 1 warning**, in 60,07 secondi. Non confermo quindi 238/8 in questo ambiente.
- Gli 8 salti attesi sono riconducibili a controllo/componenti ufficiali (6), veraPDF (1), pacchetto Windows (1). Gli ulteriori 26 dipendono da Ghostscript (25) e pdftotext (1). I salti non sono errori applicativi.
- Quattro fallimenti: confronto byte per byte dell'XML A10 e verifica delle tre registrazioni del controllo. Causa dimostrata: conversione LF/CRLF al checkout Windows, con core.autocrlf=true; vedere CE09. Tutti i 12 file delle tre registrazioni coincidono invece con le impronte del manifest quando letti come blob Git originali.
- Quinto fallimento: tests/test_installazione.py:112, aspettativa che il PID scritto dal processo coincida con Popen.pid. Osservati PID 6396 e 36172; la GUI aveva risposto alla verifica di avvio prima dell'assert. Il processo tramite launcher della venv Windows richiede una prova adeguata della relazione padre/figlio. Questo fallimento non dimostra da solo che l'app non si avvii.
- I test stdio MCP disponibili sono passati. Non equivalgono all'uso del client Claude reale.

Sono inoltre stati eseguiti programmi temporanei tramite standard input, senza aggiungere test al repository, e prove Playwright sul server reale avviato con tests/e2e/server.py, porta 8813 e archivio sintetico separato. Risultati principali:

| Esperimento | Risultato misurato |
|---|---|
| Export diretto caso_a10 + contesto_caso_a10 | completo=True, zero errori, XML 80.094 byte |
| Stesso caso nel Servizio, con originali acquisiti e riferimenti aggiornati agli ID effettivi | completo=False; due ALLEGATO_NON_DISPONIBILE |
| Germano + unilaterale, quote 1/2 e 1/2 | completo=True, zero errori; solo avviso QUOTE_DI_LEGGE_NON_VERIFICATE |
| Caso tardivo, fabbricato 3.000.000, tempistica 1 / 2 | entrambi completi; imposta successione 44.132; EF19 90.655 / 134.787 |
| Allegato 6.021.671 byte | completo=True, zero errori; XML 8.080.094 byte |
| Backup con originale deliberatamente mancante | ripristino termina senza errore; riga allegato presente, file assente |
| GUI: digitazione durante risposta di salvataggio ritardata | modifica successiva persa; contatore dirty=0; messaggio Salvato |
| GUI: modifica non salvata, eliminazione riga, Salva | bene ricreato con il solo campo descrizione |
| Route statica con separatori Windows e sessione autorizzata | HTTP 200 e lettura di tests/e2e/gui_flusso.js fuori dalla cartella static |
| Arresto simulato del controllo e nuovo adattatore | job in_esecuzione; riprendi e stessa richiesta non lo recuperano |
| Richiesta JSON malformata / aggiornamento invalido | HTTP 422; aggiornamento atomico, revisione invariata |
| Host estraneo / Origin estraneo su scrittura | HTTP 403 / 403 |
| Titolo con markup img/onerror | mostrato come testo; zero immagini, nessuna esecuzione dello script |
| Tastiera nella tabella | ArrowDown trasferisce selezione e focus alla seconda riga |
| Helper ok dell'E2E, chiamato con false | stampa FAIL ma processo Node termina con codice 0 |

### Aree che hanno retto alle verifiche

Le scritture applicative usano transazioni SQLite e controllo della revisione attesa; i test di idempotenza e conflitto del servizio sono passati. Il ripristino su archivio già popolato è rifiutato. Sul caso ordinario i test di backup, riapertura e conservazione degli elaborati sono passati: CE06 riguarda il caso negativo, non smentisce questi risultati.

L'aritmetica usa Decimal/Fraction. Nei casi coperti dai test non ho dimostrato un nuovo errore aritmetico nelle franchigie, nella presunzione DN/BI o nei totali dell'esempio della guida. CE03 e CE04 sono errori di ammissibilità/compilazione sostanziali, non divergenze di centesimi.

La separazione di export, XSD, controllo e trasmissione è presente; le note interne non invalidano l'export e le modifiche dichiarative lo invalidano nei test eseguiti. Il canale di invio reale non è esposto dalla GUI/MCP esaminata. Gli esecutori simulati del controllo sono marcati simulazione.

La costruzione DOM tramite h()/textContent evita l'inserimento HTML nei percorsi verificati. Token, Host e Origin hanno respinto le richieste negative provate. Non ho trovato strumenti MCP che espongano shell o SQL; l'acquisizione MCP applica resolve e controllo del contenimento nella cartella d'ingresso.

## 3. Rilievi per gravità

Nessun rilievo classificato bloccante nel senso di perdita irreversibile dell'intero archivio o trasmissione reale non autorizzata dimostrata. Le anomalie alte seguenti impediscono comunque l'accettazione del primo percorso completo. Tutti i rilievi sono fatti verificati, salvo i limiti esplicitamente indicati.

### CE01 — ALTA — Il servizio non collega gli allegati e l'impegno dell'intermediario al contesto XML

**File/riga:** src/successioni/elaborati.py:57; src/successioni/telematico/quadri_efgh.py:224; src/successioni/telematico/esporta.py:1000.

Il servizio costruisce ContestoExport soltanto con CF fornitore, tipo e scopo. Non valorizza allegati, impegno_codice o data_impegno. GUI e MCP chiamano quel servizio e non offrono parametri alternativi per completarli.

**Riproduzione:** creare la pratica con ops_da_caso(caso_a10()), acquisire i due PDF sintetici attraverso acquisisci_file, aggiornare documenti_ref con gli allegato_id restituiti, quindi chiamare Servizio.esporta con CF_ANNA. Esito: due ALLEGATO_NON_DISPONIBILE e nessun XML. Chiamando direttamente esporta_xml(caso_a10(), contesto_caso_a10()), invece, si ottengono completo=True e zero errori.

Per un fornitore di tipo 10 diverso dal dichiarante è richiesto anche contesto.impegno; il Servizio non lo passa. Il modulo diretto accetta il caso sintetico con codice/data impegno e documento EG7, mentre questi valori non sono configurabili nel contesto tramite il servizio corrente.

**Impatto:** un caso positivo del solo modulo XML non è un percorso positivo dell'app. Il blocco sugli allegati riguarda il caso base obbligatorio, non un quadro escluso dal progetto; il secondo blocco interessa proprio l'uso da intermediario richiesto.

**Fonti:** fornituraSUC13_v1.xsd, QuadroEG/AlberoGenealogico e Frontespizio/ImpegnoATrasmettere; Fascicolo I p.49 e p.51.

**Correzione suggerita:** costruire il contesto dai documenti dell'archivio della stessa pratica, con verifica di ID, ruolo, hash e disponibilità; passare il profilo e l'impegno dell'intermediario. Aggiungere una prova completa attraverso Servizio, API e MCP con allegati reali del corpus sintetico. Non risolvere disattivando EG o i controlli di completezza.

### CE02 — ALTA — Il ciclo del buffer GUI perde modifiche e può ricreare una riga eliminata

**File/riga:** src/successioni/static/app.js:389 e :393; percorso correlato :244.

**Caso A, browser reale:** digitare “Primo salvataggio” nel nome del defunto e premere Salva. Ritardare soltanto la risposta HTTP, lasciando eseguire la scrittura reale; durante l'attesa digitare “Modifica durante attesa”. Prima della risposta il buffer contiene la seconda modifica. Alla risposta salvaTutto svuota indiscriminatamente S.dirty e S.nuove: campo visibile e database tornano a “Primo salvataggio”, dirty=0 e messaggio “Salvato (revisione 2).”.

**Caso B, browser reale:** modificare senza salvare la descrizione di un fabbricato già presente, quindi eliminarlo confermando il dialogo. Il server lo elimina, ma la modifica rimane in S.dirty. Premendo Salva viene eseguito un upsert con lo stesso ID: il bene ricompare con la sola descrizione, perdendo tipo, comune e identificativi nella nuova revisione.

**Impatto:** perdita silenziosa di lavoro non ancora salvato e reintroduzione di una riga parziale contraria all'eliminazione confermata. Le revisioni consentono recuperi dei dati precedentemente salvati; non recuperano la digitazione persa nel caso A.

**Correzione suggerita:** associare il salvataggio a uno snapshot/generazione del buffer; rimuovere soltanto le modifiche effettivamente confermate, preservando quelle intervenute dopo. Serializzare i salvataggi oppure disabilitare coerentemente la modifica durante l'operazione. Alla rimozione di una riga cancellare la relativa modifica pendente. Provare anche risposta lenta, doppio clic, cambio pratica e conflitto.

### CE03 — ALTA — Quote di legge non supportate sono accettate come dichiarazione completa

**File/riga:** src/successioni/telematico/esporta.py:1114 e :1204; controllo condizionato a :598.

**Riproduzione:** partire da caso_a10; impostare grado_parentela e relazione_con_defunto di Anna a “10” e di Luca a “11”, lasciando 1/2 a ciascuno nelle devoluzioni. I due tipi soggetto rimangono “1”. Il modulo restituisce completo=True, zero errori e XML valido XSD. L'assenza di verifica produce soltanto QUOTE_DI_LEGGE_NON_VERIFICATE.

**Fonte:** Fascicolo I, p.69, Allegato 5: in assenza dei familiari prioritari, i fratelli unilaterali conseguono metà della quota dei germani. Per un germano e un unilaterale del caso servono quindi 2/3 e 1/3. Anche l'annotazione Devoluzione/Quota dei quadri EB/EC/ER richiede le quote dell'Allegato 5 quando i tipi EA sono tutti 1 o tutti 3.

**Impatto:** ripartizione patrimoniale sostanzialmente errata accettata come completa. Non è il dubbio sui centesimi. Il fatto che la matrice dichiari le quote non verificate non sostituisce il blocco del caso alla finalizzazione. Inoltre ElaboratiMixin.esporta non restituisce es.avvisi, quindi l'eventuale avviso del modulo non viene propagato dal servizio.

**Correzione suggerita:** implementare e verificare la configurazione oppure trattarla come non_supportato/quadri_mancanti per lo scopo completo. Una bozza tecnica può conservarla solo esplicitando il limite. Propagare gli avvisi dal modulo ai canali applicativi.

### CE04 — ALTA — Pagamento differito ammesso anche oltre il termine che impone quello contestuale

**File/riga:** src/successioni/telematico/quadri_efgh.py:188 e :200.

**Riproduzione:** caso_a10, decesso 10/03/2025, data_riferimento del contesto 01/11/2026, valore del fabbricato portato a 3.000.000, nessun evento che sposti il termine ordinario. Con tempistica_pagamento “1” e “2” il modulo produce in entrambi i casi completo=True e zero errori.

| Campo | Codice 1 accettato | Codice 2 |
|---|---:|---:|
| Imposta successione EF18bis | 44.132 | 44.132 |
| Totale EF19 e ImportoDaVersare | 90.655,00 | 134.787,00 |

**Fonti:** Fascicolo I p.6, termine ordinario di dodici mesi dal decesso; p.48, EF18ter colonna 1: oltre novanta giorni dal termine di presentazione deve essere indicato il codice 2. La medesima pagina disciplina l'inclusione dell'imposta in EF19.

**Impatto:** sono esclusi 44.132 euro dall'addebito contestuale per una scelta di pagamento non ammessa nel caso. Non sostengo che 134.787 sia il debito complessivo finale della pratica tardiva: sanzioni e interessi non sono stati calcolati e sono fuori dal perimetro dichiarato.

**Correzione suggerita:** determinare e validare il termine applicabile, con i casi di differimento espliciti. Finché la tardività non è supportata, bloccare il completamento di questa casistica invece di accettare codice 1. Non inventare scadenze per casistiche particolari mancanti.

### CE05 — ALTA — Il limite degli allegati non partecipa all'accettazione dell'XML completo

**File/riga:** src/successioni/telematico/quadri_efgh.py:236; src/successioni/documenti/base64.py:136, funzione dati_file_attachment. Il controllo separato in documenti/dimensioni.py:441 non è chiamato da questo percorso.

**Riproduzione:** in una cartella temporanea creare un allegato con il contenuto di albero_genealogico.pdf della fixture più 6.000.000 byte di spazi, e sostituirne soltanto il percorso in contesto_caso_a10.allegati. Il file misura 6.021.671 byte, supera sia 5 MB decimali sia 5 MiB. L'export produce completo=True, zero errori, XML di 8.080.094 byte.

**Fonte:** Specifiche_SUC13_20250702.pdf, p.7 §2.3: massimo 5 MB per singolo allegato e necessità di suddividerlo. L'XSD ImageData di reg:FileAttachment_Type non incorpora questo limite, perciò la sola validazione XSD non lo applica.

**Impatto:** un vincolo tecnico esplicito può essere violato da un file dichiarato completo. Questo rilievo riguarda la dimensione, indipendentemente dal limite già noto della validazione PDF/A.

**Correzione suggerita:** controllare dimensioni dei binari prima della Base64 e bloccare lo scopo completo; collegare anche la verifica complessiva della fornitura sull'XML effettivo, mantenendo esplicite le assunzioni sul limite compresso. Non basta l'avviso visualizzato quando il file è acquisito.

### CE06 — MEDIA — Ripristino incompleto accettato senza verifica degli allegati

**File/riga:** src/successioni/archivio.py:150 e :157.

**Riproduzione:** creare una pratica sintetica con un PDF acquisito, fare backup, rimuovere soltanto quel PDF dalla copia temporanea di backup e ripristinare in una destinazione nuova. ripristina termina normalmente; elenca_allegati restituisce la riga, ma il file richiamato non esiste. Output misurato: una riga allegato, presenza fisica False.

**Impatto:** il comando può dichiarare il ripristino riuscito su un archivio documentalmente incompleto. Il backup originale integro usato come sorgente dell'esperimento è rimasto separato; non è dimostrata perdita di dati nell'ordinario backup integro.

**Correzione suggerita:** validare prima schema, integrità DB, presenza/hash dei file allegati e dei job; esiste già parte della logica in scripts/windows/verifica_backup.py. Preparare il ripristino in una destinazione di staging, verificare e pubblicare il risultato soltanto quando completo. Evitare che un errore di copia lasci una destinazione popolata e non riprendibile.

### CE07 — MEDIA — Traversal nella route statica su Windows, con sessione autorizzata

**File/riga:** src/successioni/web.py:65 e :66.

Il filtro vieta “/” e un punto iniziale, ma non i separatori Windows interni. Path interpreta i backslash prima dell'accesso al file.

**Riproduzione nel browser con sessione sintetica autorizzata:**

    const p = 'x\\..\\..\\..\\..\\tests\\e2e\\gui_flusso.js';
    const r = await fetch('/static/' + encodeURIComponent(p));
    // status: 200; corpo: sorgente di tests/e2e/gui_flusso.js

**Impatto dimostrato:** lettura di un file esterno a src/successioni/static, nei privilegi del processo. L'accesso resta protetto dal token e limitato dalle estensioni ammesse; non ho dimostrato un attacco remoto anonimo né esecuzione di codice. Per questo la gravità è media.

**Correzione suggerita:** risolvere il percorso e imporre che appartenga alla directory statica, oppure usare una whitelist esatta dei file serviti. Provare separatori Windows, percorsi assoluti, segmenti parent e codifica URL; il solo controllo testuale di uno slash non basta.

### CE08 — MEDIA — Un controllo interrotto rimane in esecuzione senza recupero

**File/riga:** src/successioni/collegamenti/controllo.py:438 e :538.

**Riproduzione controllata, esito simulazione:** usare ambiente_finto dei test e un esecutore che risponde normalmente alla diagnostica ma solleva una BaseException dopo la transizione in_esecuzione. Riaprire lo stesso archivio con un nuovo ControlloJar. riprendi(job_id) restituisce in_esecuzione; esegui con la stessa chiave restituisce ancora in_esecuzione senza chiamare l'esecutore (zero chiamate). Non è stata eseguita né simulata una trasmissione.

**Impatto:** persistere la riga non rende riprendibile il controllo. Dopo la perdita del processo il job può restare indefinitamente pendente, senza un esito esplicito o un percorso di recupero. La prova non dimostra quale evento di disconnessione del client Claude provochi effettivamente un arresto: quello resta da collaudare.

**Correzione suggerita:** registrare proprietà/heartbeat del processo e prevedere recupero degli output, stato interrotto e riavvio esplicito sicuro del solo controllo. Separare questa logica dalle regole dell'invio: un invio incerto non deve essere ripetuto automaticamente.

### CE09 — MEDIA — Git altera i byte delle evidenze del controllo al checkout Windows

**File/riga:** .gitattributes:1; tests/test_telematico_controllo.py:56 e :223.

La regola generale text=auto lascia soggette a conversione le fixture XML, DGN e WRI. Con core.autocrlf=true, nel checkout Windows gli hash non coincidono più con i manifest: quattro test falliscono.

**Verifica indipendente:** per tutti i dodici file delle tre registrazioni, il blob restituito da git show HEAD:<percorso> ha l'hash atteso; il file del checkout non lo ha; riportando solo CRLF a LF si ottengono esattamente i byte del blob. Il primo scostamento dell'XML è alla posizione 38.

**Impatto:** il materiale probatorio non è riproducibile byte per byte attraverso un normale checkout della piattaforma destinazione. Non è prova che la registrazione ufficiale originale sia falsa o alterata nel commit.

**Correzione suggerita:** dichiarare le evidenze a byte invariati (-text) e verificare gli hash dopo checkout Windows/Linux. Non correggere il problema aggiornando i manifest con hash dei file trasformati e non normalizzare indiscriminatamente i documenti probatori nei test.

### CE10 — MEDIA — Le verifiche booleane dell'E2E non fanno fallire il test

**File/riga:** tests/e2e/gui_flusso.js:9.

L'helper ok stampa “FAIL” quando la condizione è falsa, ma non solleva un errore e non imposta un codice d'uscita negativo. Anche la verifica errs.length===0 usa questo helper.

**Verifica:** estrazione in memoria della definizione reale di ok e chiamata con false: output “FAIL verifica volutamente negativa del solo helper”, processo Node con exit code 0. È una prova isolata del comportamento dell'helper, non una falsa esecuzione dell'intero E2E.

**Impatto:** un esecutore che osserva soltanto il successo del comando può registrare passato anche con verifiche funzionali negative. Un errore Playwright/timeout può comunque far fallire lo script: il difetto riguarda le asserzioni booleane trasformate in soli log.

**Correzione suggerita:** usare assert/expect, chiudere il browser in finally e restituire un codice non nullo a ogni fallimento. Provare che una condizione deliberatamente falsa faccia risultare fallito il comando intero.

## 4. Punti aperti

### Stato effettivo A01–A20

Le parole indicano l'evidenza del requisito completo; la colonna di dettaglio distingue quanto è passato localmente. “fallito” sotto deriva dalle prove negative di questa revisione, non dai componenti esterni assenti.

| ID | Stato | Evidenza e confine |
|---|---|---|
| A01 | da_collaudare | App da sorgente avviata su Windows; pacchetto autonomo non costruito/provato. Un assert sul PID dell'avviatore è fallito. |
| A02 | fallito | Backup/riapertura ordinari passati; ripristino con allegato mancante accettato, CE06. |
| A03 | da_collaudare | Server MCP stdio e archivio condiviso passati; client Claude effettivo non provato. |
| A04 | passato | Idempotenza e conflitti del servizio verificati dai test; non estendere questo esito alla gestione dei buffer GUI di CE02. |
| A05 | fallito | Quote esatte e continuazioni del sottoinsieme hanno test passati; quote di legge errate accettate, CE03; diritti distinti restano fuori copertura. |
| A06 | da_collaudare | Esempio guida, franchigie e DN/BI passati localmente; qualifiche multiple ed eredi/legatari non coperti integralmente. |
| A07 | fallito | Rifiuto pre-2025 verificato; ammissibilità della tempistica nella successione tardiva errata, CE04. Copertura storica completa assente. |
| A08 | da_collaudare | Divergenza sugli arrotondamenti resta aperta e dichiarata; riduzioni/estero esclusi. Nessun nuovo rilievo sul centesimo noto. |
| A09 | fallito | Modulo XML A10 valido XSD; percorso completo del servizio bloccato, CE01. Stampa finale non esposta dal percorso GUI/MCP esaminato. |
| A10 | da_collaudare | Lettori delle registrazioni provati; blob delle evidenze verificati. Controllo ufficiale non rieseguito da questo revisore; conversione dei file al checkout, CE09. |
| A11 | da_collaudare | Nessuna conversione/validazione indipendente eseguita qui: Ghostscript e veraPDF assenti. Nessuna conformità attestata. |
| A12 | fallito | Test disponibili sui formati passati; prove Ghostscript saltate. Il vincolo 5 MB non blocca l'export completo, CE05. |
| A13 | da_collaudare | Nessuna sessione Entratel autenticata o acquisizione reale. |
| A14 | simulazione | Normalizzazione/import ripetuto provati su fixture; servizio reale non provato. |
| A15 | fallito | Persistenza/paginazione simulata presenti; controllo interrotto non recuperabile con riprendi/stessa richiesta, CE08. |
| A16 | passato | Invalidazione selettiva di export e copie nei test locali; non dimostra interoperabilità ufficiale o gestione di ogni allegato futuro. |
| A17 | simulazione | Copie, hash, conferma e blocchi provati a livello adattatore con doppi di test; nessuna preparazione operativa integrata nella GUI. |
| A18 | simulazione | Casi di trasporto interrotto e protezione dai reinvii dei test passati; nessuna prova reale, nessuna garanzia generalizzata sui canali futuri. |
| A19 | simulazione | Associazione e stati distinti provati sui dati di test; nessuna ricevuta reale acquisita. |
| A20 | fallito | Matrice presente ma non sufficiente: alcuni casi non verificati arrivano a completo=True, CE03/CE05. |

### Azioni e incertezze residue

- Correggere prima CE01/CE02 e i blocchi fiscali/tecnici CE03–CE05; ripetere poi un caso completo attraverso i canali applicativi, senza cambiare il riferimento del rapporto: la correzione richiederà un nuovo commit e una nuova verifica.
- Aggiornare la matrice: docs/MATRICE_COPERTURA.md:35 afferma ancora che EF/EG/EH mancano, mentre il modulo A10 li produce; :80 ripete lo stesso limite; :82 presenta A20 come implementato pur in presenza dei blocchi mancanti qui dimostrati. Distinguere modulo, integrazione applicativa e verifica ufficiale.
- Rendere il test dell'avviatore Windows compatibile con il processo effettivo della venv e verificare la chiusura dell'intero albero di processi. Non considerare il semplice confronto errato dei PID un collaudo negativo del pacchetto autonomo.
- Integrare un test E2E realmente assertivo per l'export positivo con allegati, una pratica da intermediario e le due regressioni GUI. Gli attuali test del servizio esercitano soprattutto il rifiuto dell'export incompleto e la bozza tecnica.
- L'addebito e la gestione dei termini devono essere verificati sulle casistiche effettivamente supportate; l'esempio tardivo sopra non autorizza ad automatizzare ravvedimenti.
- Le prove di sicurezza disponibili non dimostrano una protezione completa contro consumo eccessivo di memoria/CPU: upload e parser vanno sottoposti a limiti e corpus ostile dedicati prima dell'uso reale.

## 5. Cosa non ho potuto verificare

- Installazione del pacchetto Windows autonomo, client Claude effettivo, Desktop Telematico e configurazione completa dei componenti SUC13.
- Esecuzione indipendente del controllo ufficiale sui file positivi e negativi: ho verificato lettori, test e impronte dei blob delle registrazioni, non prodotto nuovi diagnostici ufficiali.
- Conversione reale con Ghostscript, conformità con veraPDF, firma digitale e fedeltà visiva dell'intero corpus dopo conversione/suddivisione. Il verificatore strutturale interno resta indicativo.
- Catasto Entratel, completezza dei risultati reali, autenticazione, ambiente di sicurezza, invii, riconciliazioni e ricevute operative. Nessun accesso o invio effettuato.
- Tutte le regole fiscali per casistiche escluse. Le verifiche fiscali di questo rapporto sono ancorate ai documenti/pagine/elementi citati; non costituiscono una validazione normativa universale dell'app.
- Resistenza a PDF/XML molto grandi, decompression bomb, fuzzing esteso e vulnerabilità dei runtime Java/Ghostscript. Ho ispezionato i parser XML con risoluzione delle entità disabilitata e i comandi a lista di argomenti, ma non ho eseguito un collaudo offensivo dei componenti esterni.
- Copertura quantitativa delle linee o dei rami: non è stata misurata. Il numero dei test non è usato come prova di completezza.
- Confronto con le due revisioni vietate: sono rimaste non lette anche alla conclusione del rapporto.

Il rapporto descrive esclusivamente il commit indicato. Nessun esito locale o simulato è qualificato come dichiarazione approvata, trasmessa o pronta per una pratica reale.

