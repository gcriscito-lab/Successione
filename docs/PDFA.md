# Documenti, allegati EG e PDF/A (area 2)

Aggiornato: 2026-11-02. Collaudo Windows e correzioni: `docs/COLLAUDO_WINDOWS_CODEX_20261102.md`.
Codice: `src/successioni/pdfa.py`, `src/successioni/allegati.py`, `src/successioni/documenti/`.
Test: `tests/test_pdfa.py`, `tests/test_documenti_*.py`. Stato riprendibile: `docs/STATO_area2.md`.

| Requisito | Stato | Evidenza |
|---|---|---|
| A11 conversione PDF -> PDF/A-1b, pagine e testo conservati, originale invariato | **controllo locale passato** (Ghostscript 10.02.1, Linux) | `tests/test_documenti_corpus.py`, `tests/test_pdfa.py` |
| A11 validazione con validatore indipendente (veraPDF) | **passato sul corpus sintetico Windows** | 2026-11-02: veraPDF 1.30.3, Ghostscript 10.08.0, 9 derivati conformi, 15 originali invariati; vedi rapporto Windows |
| A11 non conforme respinto | **passato con veraPDF sul corpus sintetico** | font non incorporati, ordinario e falso PDF/A respinti; `test_a11_collaudo_reale_verapdf` eseguito |
| A12 protetto / danneggiato / non PDF / firmato con esito esplicito | controllo locale passato (corpus sintetico, firma **simulata**) | `test_a12_*` |
| A12 riduzione, suddivisione e soglie senza perdita | controllo locale passato | `tests/test_documenti_dimensioni.py` |
| Accettazione degli allegati da parte dell'Agenzia (CIVIS / software di controllo) | **da_collaudare** | nessuna prova con i servizi dell'Agenzia |
| Fedelta' visiva su un insieme rappresentativo di documenti reali | **da_collaudare** | solo indicatore automatico su corpus sintetico (par. 6) |

Le prove sul corpus sintetico sono controlli locali: **non dimostrano compatibilita' con l'Agenzia**.

## 1. Fonti

| Fonte | Punto | Citazione / contenuto |
|---|---|---|
| `fonti/Specifiche tecniche/Specifiche_SUC13_20250702.pdf` (2 luglio 2025) | p.3 par. 1 | "La fornitura deve contenere i dati relativi ad una sola dichiarazione." "la dimensione complessiva delle dichiarazioni di successione da trasmettere non può eccedere il limite previsto di 40 MB compressi." Oltre il limite: presentazione presso un ufficio territoriale. |
| idem | p.7 par. 2.3 | "Sono accettati documenti con formato file: TIF e/o TIFF e PDF/A (PDF/A-1a o PDF/A-1b)." TIFF: "risoluzione non superiore a 300 DPI, selezionare il colore B/N e specificare la Compressione CCITT Group IV (modalità Fax)." "Ogni file allegato non deve superare la dimensione massima di 5 MB. Nel caso in cui il file superi la dimensione massima è necessario suddividerlo in più file." Servizio ufficiale: "CIVIS - Presentazione documenti per controllo formale - Funzione di validazione e conversione file" (utenti abilitati). Allegati non conformi: scarto della dichiarazione. |
| idem | p.263-281, p.794-796, p.902 | `QuadroEG/<Sezione>/<Sezione>All` di tipo `reg:FileAttachment_Type`; `FileType` (application/pdf, image/tif, image/tiff), `FileName` (cm:DatoAN_Type, maxLength 100), `FileDescription` (cm:DatoAN_Type, facoltativo), `ImageData` (xs:base64Binary). |
| `fonti/.../registro/xsd/typesReg_v2.xsd` | righe 419-431, 3177 | `FileAttachment_Type`, `FileType_Type` (letti dai test, sola lettura). |
| `fonti/.../common/xsd/typesDati_v2.xsd` | righe 13-20 | pattern di `DatoAN_Type`: solo maiuscole, cifre e alcuni segni. |
| `fonti/.../SUC/xsd/fornituraSUC13_v1.xsd` | righe 1160-1310 | 11 elementi allegato del quadro EG (DichSostAll ... RiduzioniImposteSuccessioneAll). |
| `fonti/Istruzioni/Succ_FASCICOLO_I_Nov_23.pdf` | p.49 | "La documentazione da allegare deve avere una bassa risoluzione (200x200dpi, colore Bianco e Nero), purché leggibile ... PDF/A–1a, PDF/A–1b oppure TIF e/o TIFF". Indicazione di prassi: usata come primo tentativo di riduzione (200 dpi). |
| Tabella regole PDF/A-1 di veraPDF, https://raw.githubusercontent.com/wiki/veraPDF/veraPDF-validation-profiles/PDFA-Part-1-rules.md | consultata 2026-11-01 | identificativi delle regole ISO 19005-1 usati dal verificatore strutturale (la norma ISO non è in `fonti/`). |
| https://docs.verapdf.org/install/ e https://docs.verapdf.org/cli/validation/ | consultate 2026-11-01 | installer `verapdf-installer.zip`, `vera-install.bat`, installazione automatica, profili `-f 1b`, rapporto XML predefinito con `isCompliant`. |
| Sito dell'Agenzia (www.agenziaentrate.gov.it, telematici.agenziaentrate.gov.it) | tentativi del 2026-11-01 | gli URL provati per le schede sulla successione hanno restituito 404: nessuna informazione aggiuntiva su unità di misura o punto di misura. |

## 2. Flusso e funzioni

Originale acquisito e mai modificato -> `pdfa.analizza_pdf` (esito `leggibile | firmato | protetto | danneggiato |
non_pdf | tiff`) -> `Servizio.prepara_pdfa` -> derivato PDF/A-1b (Ghostscript) + `pdfa.valida_pdfa` + confronto pagine,
testo (pdftotext) e immagine -> se oltre 5 MB: `Servizio.suddividi_allegato` (`documenti.dimensioni.riduci_o_suddividi`)
-> allegato EG (`documenti.base64.dati_file_attachment`) -> `documenti.dimensioni.verifica_fornitura`.

- `prepara_pdfa`: se l'originale dichiara PDF/A-1 **e veraPDF lo giudica conforme**, è conservato senza riscrittura (la
  firma resta integra). Senza veraPDF si crea sempre il derivato. Un derivato con numero di pagine diverso **non viene
  registrato** (`conversione_fallita`). Avvisi: firma non conservata, testo con differenze, differenze visive,
  derivato oltre 5 MB (`azione_richiesta = suddividi_allegato`).
- `suddividi_allegato(allegato_id, limite_byte=None)`: registra ogni parte come `derivato` collegato all'originale, con
  rapporto (hash, intervallo di pagine, validazione, verifica testo).
- PDF/A-1a: non prodotto (richiede struttura taggata; Ghostscript non la crea). Il livello predefinito è 1b.

## 3. Esiti (parole fisse)

| Funzione | Valori |
|---|---|
| `valida_pdfa(...)["esito"]` | `conforme` / `non_conforme` **solo con il rapporto di veraPDF**; altrimenti `non_verificato` con `esito_collaudo: da_collaudare` |
| `verifica_indicativa["esito"]` (strutturale interno) | `indicativo_ok` / `indicativo_ko` con motivi, clausole, controlli eseguiti e NON eseguiti; mai `conforme` |
| `verifica_tiff(...)["esito"]` | `indicativo_ok` / `indicativo_ko` (requisiti di p.7); accettazione CIVIS da collaudare |
| `confronta_visivo(...)["esito"]` | `simili` / `da_controllare` (indicatore; l'anteprima dell'utente resta necessaria) |

Il rapporto XML di veraPDF è conservato nel rapporto del derivato (`validazione.rapporto_xml`, non esposto
nell'elenco degli allegati).

## 4. Verificatore strutturale (indicativo)

`documenti/pdfa_strutturale.py`: intestazione e commento binario, ID nel trailer, cifratura, dati dopo `%%EOF`, xref
stream, LZW, riferimenti esterni, file incorporati, contenuti opzionali, XMP (forma, `pdfaid`), OutputIntent GTS_PDFA1
con profilo ICC incorporato e coerente, colori device rispetto all'OutputIntent, font incorporati, trasparenza,
ExtGState TR/TR2, intento di rendering, BitsPerComponent, azioni/JavaScript, annotazioni (tipi, flag, AP, C/IC), moduli,
limiti di implementazione sugli oggetti; per 1a: MarkInfo, StructTreeRoot, ToUnicode. L'elenco dei controlli **non
eseguiti** (content stream, glifi, CharSet/CIDSet, corrispondenza Info/XMP, schemi di estensione, ...) è restituito
con ogni esito.

Difetti corretti il 2026-11-01: (1) `BooleanObject(True) is True` è sempre falso in pypdf, quindi NeedAppearances,
Interpolate e Marked non erano mai rilevati (test di regressione `test_need_appearances_vero_rilevato`); (2) più
violazioni con lo stesso codice conservavano solo il primo messaggio.

## 5. Dimensioni, unità e punto di misura

ASSUNZIONI dichiarate (le fonti non le risolvono):

1. **Unità di "MB"**: i limiti si passano in byte. Predefinito **decimale** (5 000 000 e 40 000 000 byte), più severo
   del binario (5 242 880 e 41 943 040). `limiti.limite_byte(5, "binaria")` per l'alternativa.
2. **Limite per allegato**: misurato sul file binario **prima** della codifica Base64 (Base64 aggiunge 4/3).
3. **40 MB compressi**: `verifica_fornitura(..., punto_misura=...)`: `xml_deflate` (predefinito: XML della fornitura
   con allegati Base64 compresso DEFLATE livello 9; algoritmo e contenitore reali dell'Agenzia/Entratel non indicati),
   `xml_non_compresso` (prudenziale), `allegati_base64_deflate` (senza XML: limite inferiore, `completa: false`).
   Ogni errore riporta misura, limite in byte/MB/MiB e punto di misura.

`riduci_o_suddividi(pdf, limite_byte)`: nessuna azione se già entro il limite e PDF/A; altrimenti ricompressione delle
immagini con Ghostscript (`(200 dpi, Q 0.4)`, poi `(150 dpi, Q 0.6)`; parametro `tentativi`, opzione `scala_di_grigi`);
se non basta, suddivisione per pagine del candidato più piccolo con qpdf (`--object-streams=disable`, conserva XMP e
OutputIntent) o, in mancanza, pypdf; composizione su stima per pagina e misura reale di ogni parte, con ulteriore
divisione se eccede. Una pagina che da sola supera il limite produce `LIMITE_NON_RAGGIUNGIBILE` (mai perdita
silenziosa). Ogni uscita è rivalidata; pagine contate, testo confrontato per pagina, SHA-256 dell'originale
riverificato; rapporto JSON accanto alle parti.

Controlli di `verifica_fornitura`: una sola dichiarazione, allegato oltre limite, formato non PDF/TIFF, FileType fuori
enumerazione o incoerente col contenuto, FileName non conforme, file mancante, esito di validazione diverso da
`conforme` (se indicato), fornitura oltre il limite compresso, XML assente (con `richiedi_xml=True`).

## 6. Base64, FileName e TIFF

- `ImageData` (xs:base64Binary): **nessuna faccetta** (né lunghezza massima né pattern). Si produce la forma canonica
  (alfabeto RFC 2045, `=` di riempimento, nessun a capo): 4·ceil(n/3) caratteri. La decodifica accetta gli spazi XML.
  Round-trip bit per bit provato su lunghezze 0-9, 1000, 65537 byte e su PDF fino a qualche MB.
- `FileName`/`FileDescription` (cm:DatoAN_Type): **solo maiuscole**; niente minuscole né `_`; primo carattere cifra,
  A-Z, `-` o `"`. `normalizza_nome_file_eg` converte (es. `certificato di morte_2024.pdf` -> `CERTIFICATO DI
  MORTE-2024.PDF`). Equivalenza fra pattern Python e validatore XSD (lxml sullo schema ufficiale) provata su 16 nomi.
- TIFF: `verifica_tiff` legge le IFD senza dipendenze (Compression=4, 1 bit B/N, risoluzione <= 300 DPI con
  ResolutionUnit); `converti_in_tiff_g4` usa il dispositivo Ghostscript `tiffg4` (predefinito 200 dpi). Incognite: TIFF
  multipagina (non citato dalle specifiche, accettato qui), TIFF senza risoluzione (respinto in via prudenziale).

Indicatore visivo (`documenti/anteprima.py`): rendering a 40 dpi e differenza per pixel. Rileva pagine mancanti,
bianche o molto diverse; **non** rileva sostituzioni di carattere (prova: due PDF con font diversi risultano `simili`).

## 7. Corpus sintetico e prove eseguite

`python -m successioni.documenti.corpus_sintetico <cartella>`: ordinario (TrueType incorporato), font non
incorporati, immagini grandi (14,3 MB), multipagina (40 pagine di testo), cifrato, protetto senza password utente,
troncato, firmato (**firma simulata**, nessun valore crittografico), falso PDF/A (XMP con pdfaid ma font non
incorporati), JavaScript, trasparenza, PNG con estensione .pdf, TIFF LZW a colori, già PDF/A, TIFF G4. `corpus.json`
riporta descrizione, esito atteso e SHA-256.

Esito reale del 2026-11-01 (Linux, Python 3.13, Ghostscript 10.02.1, qpdf 11.9.0, pypdf 6.17.0, veraPDF assente):
`python3 -m pytest -q` -> **179 passati, 2 saltati** (intera suite, ultima esecuzione; il totale cresce con i test delle altre aree); area 2: 87 passati, 1 saltato
(`test_a11_collaudo_reale_verapdf`, richiede veraPDF). Riduzione reale: immagini_grandi 14 342 795 -> 180 344 byte
a 200 dpi.

## 8. Limiti residui

1. **Ghostscript 10.02.1 non conserva il ToUnicode** del TrueType incorporato prodotto da reportlab (`pdffonts`: `uni
   no`, anche con `pdfwrite` semplice e con `-dWantsToUnicode=true`): resa visiva uguale, ma le lettere accentate non
   sono più estraibili/ricercabili nel derivato. Il confronto del testo lo segnala come differenza minore (avviso),
   non in silenzio. Da provare con una versione recente di Ghostscript per Windows e su documenti reali (il PDF delle
   specifiche dell'Agenzia è prodotto con Ghostscript 10.05.0).
2. La riscrittura in PDF/A **non conserva la firma digitale**; l'originale firmato è conservato tal quale solo se veraPDF
   lo giudica già conforme. Verifica di formato e verifica della firma non sono intercambiabili: la seconda non è
   implementata.
3. La suddivisione conserva le strutture di documento della base (segnalibri, moduli) che possono riferirsi a pagine
   di altre parti; le parti sono comunque rivalidate.
4. Il verificatore strutturale non analizza i content stream né i programmi dei font.
5. Le dipendenze di sistema per Windows (Ghostscript, qpdf facoltativo, pdftotext facoltativo, veraPDF + Java) vanno
   installate e rilevate sulla postazione; senza pdftotext il testo si confronta con pypdf.

## 9. Procedura riprendibile: veraPDF sul PC del professionista e collaudo A11

Procedura eseguita sul corpus sintetico il 2026-11-02: **passato localmente**. Restano da collaudare il corpus
professionale reale e CIVIS. Non serve nessuna credenziale per la prova locale; non si inviano file all'esterno.

1. **Prerequisiti**: programma Successioni installato (Python dell'app); Ghostscript per Windows (`gswin64c --version`;
   se non è nel PATH impostare `SUCCESSIONI_GS` con il percorso completo di `gswin64c.exe`); un Java Runtime
   (`java -version`; la documentazione d'installazione mostra un'esecuzione con Java 17: verificare il requisito
   della release scaricata).
2. **Scaricare** `https://software.verapdf.org/releases/verapdf-installer.zip` e la firma
   `https://software.verapdf.org/releases/verapdf-installer.zip.asc` (link della pagina https://docs.verapdf.org/install/).
   Facoltativo ma consigliato: `gpg --keyserver keyserver.ubuntu.com --recv 78B17FE7` e
   `gpg --verify verapdf-installer.zip.asc` (impronta pubblicata: `13DD 102B 4DD6 9354 D12D E5A8 3184 8632 78B1 7FE7`).
3. **Installare**: estrarre lo zip e avviare `vera-install.bat`; cartella consigliata senza spazi, es. `C:\veraPDF`;
   selezionare almeno il componente "veraPDF CLI". In alternativa installazione automatica con il file XML generato
   dall'installer: `vera-install.bat auto-install.xml`.
4. **Verificare**: individuare il lanciatore (`dir /s /b C:\veraPDF\verapdf.bat`), poi `C:\veraPDF\verapdf.bat --version`
   e `C:\veraPDF\verapdf.bat --list` (devono comparire `1a` e `1b`). Annotare la versione.
5. **Configurare**: `setx SUCCESSIONI_VERAPDF "C:\veraPDF\verapdf.bat"` e aprire un nuovo terminale. Nell'app, lo stato
   degli strumenti (`strumenti_pdfa.veraPDF` dello strumento MCP `capacita`, `pdfa.veraPDF` di `GET /api/info` nella GUI)
   deve diventare `true`.
6. **Collaudo sul corpus sintetico**: `python -m successioni.documenti.corpus_sintetico C:\collaudo_a11 --collaudo`.
   Produce `C:\collaudo_a11\collaudo_a11.json` con ambiente, versioni, hash ed esiti. Atteso: derivati di
   `ordinario.pdf` e `gia_pdfa.pdf` -> `conforme`; originali `font_non_incorporati.pdf` e `falso_pdfa.pdf` ->
   `non_conforme`; protetti/danneggiati/non PDF respinti; `originale_invariato: true` ovunque.
7. **Test automatico**: dalla cartella del codice `python -m pytest -q tests/test_documenti_corpus.py tests/test_pdfa.py`;
   `test_a11_collaudo_reale_verapdf` non deve più essere saltato e deve passare.
8. **Insieme rappresentativo reale** (solo in locale, documenti autorizzati dal professionista): 10-20 allegati tipici
   (scansioni a colori e B/N, certificati, atti notarili, PDF firmati, PDF da moduli). Per ciascuno: `prepara_pdfa`,
   lettura del rapporto (validazione veraPDF, avvisi testo/visivi) e **anteprima a schermo pagina per pagina** contro
   l'originale. Per gli allegati oltre 5 MB: `suddividi_allegato` e controllo delle parti.
9. **Facoltativo, verifica ufficiale**: caricare un derivato nel servizio CIVIS "Presentazione documenti per controllo
   formale - Funzione di validazione e conversione file" (Specifiche p.7, utente abilitato) e annotarne l'esito. È una
   prova distinta da veraPDF.
10. **Registrare** nella tabella sotto (data, operatore, versioni, esiti, file JSON conservato). Un esito parziale resta
    parziale; in caso di `non_conforme` inatteso conservare `collaudo_a11.json` e il rapporto XML di veraPDF.

### Registro dei collaudi

| Data | Postazione | veraPDF | Ghostscript | Corpus sintetico | Insieme reale (n, anteprima) | CIVIS | Esito A11 |
|---|---|---|---|---|---|---|---|
| 2026-11-01 | container Linux (sviluppo) | assente | 10.02.1 | controlli locali passati, esiti `non_verificato` | non eseguito | non eseguito | **da_collaudare** |
| 2026-11-02 | Windows 11, collaudo Codex | 1.30.3 | 10.08.0 | 15 originali invariati, 9 derivati conformi e negativi attesi confermati | non eseguito; anteprima sulle 3 pagine sintetiche | non eseguito | **passato sul corpus sintetico** |
