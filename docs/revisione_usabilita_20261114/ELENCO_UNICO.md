# Revisione di usabilità del 14/11/2026: elenco unico

Fonte: quattro revisori indipendenti, ciascuno su una parte del programma, con sole pratiche sintetiche e senza modificare il
programma. I rapporti completi sono in questa cartella (A pagina iniziale e finestre, B quadri e schede, C parte finale e
invio, D pratica intera compilata da capo). Gli screenshot sono rimasti nella cartella di lavoro della sessione.

Richiesta del professionista: «lo trovo ingolfato… troppe informazioni… dovrebbe facilitarmi e su alcune cose lo trovo
difficile». Vincolo: nessuno stravolgimento. Solo togliere, nascondere, accorciare, risparmiare clic.

Tra parentesi i revisori che hanno trovato il punto. Un punto trovato da più revisori indipendenti è più sicuro.

## Stato (14/11/2026)

Fatti: il punto più grave ed E1-E7, E9-E14. E8 («Prepara invio» prima del controllo ufficiale) non toccato: la copia
registra i requisiti mancanti per scelta del progetto, va deciso dal professionista. E6 corretto solo per le devoluzioni (DV);
per le passività (ED) il collegamento a una persona va prima verificato sulle istruzioni. Lotti 1-4 e i tre punti di regole
ancora da fare.

## Il punto più grave

**Il programma dice «tutto a posto», poi il file non si genera** (C, D, A).

- Barra in basso, Controlli e «File e invio» dicono «Nessun rilievo» o «0 rilievi · 0 avvisi».
- Poi «Genera file» si rifiuta. I blocchi veri (devoluzioni, codici comune, EG5, EG6, CF del fornitore, prima casa, IBAN)
  si vedono solo aprendo il quadro EF o nel messaggio rosso dopo il tentativo.
- Vengono fuori a rate: il revisore D ha fatto 4 giri «genera, errore, correggo».

Proposta:
- un elenco unico «Per generare il file manca…» nei Controlli e in «File e invio», ogni voce con «Vai al dato»;
- «Controlla» conta anche questi blocchi;
- l'esito di «Genera file» resta fisso sotto il pulsante invece di un messaggio rosso che sparisce.

## Lotto 1: spazio per i campi

| # | Cosa | Proposta | Chi |
|---|---|---|---|
| 1.1 | Pannello della scheda largo 330-360 px anche a 1910: la scheda EC è alta 2,8 schermate, il centro resta vuoto. Il valore pensato per gli schermi larghi (440) non scatta mai | Larghezza iniziale 480 px sopra i 1600 px (correggere app.js:66/89) | B, D |
| 1.2 | Codice fiscale tagliato nella scheda dell'erede (158 px su 210) | Codice fiscale su una riga intera | B, D |
| 1.3 | «Altri dati (7)» sempre aperta perché contiene «Tipo di bene», che il quadro decide già | Nascondere «Tipo di bene» nei quadri dove è fisso | B |
| 1.4 | Due sezioni quasi omonime: «Altri dati» e «Altri dati del bene» | Rinominare la seconda «Precedenti successioni, graffati, trascrizione» | B |
| 1.5 | Dati generali: 5 campi «residente all'estero» del presentatore sempre aperti | Riquadro chiuso | B, D |
| 1.6 | Valore catastale: 6 righe di fonti normative a vista | Sempre nel suggerimento | B |

## Lotto 2: testi ripetuti e rumore

| # | Cosa | Proposta | Chi |
|---|---|---|---|
| 2.1 | Barra in basso: «Archivio: dati», «Revisione 1», «Controllo ufficiale: vedi File e invio», «Non finalizzabile…» | Tenere solo salvataggio, rilievi e stato del file in parole semplici | A, C, B |
| 2.2 | Barra in alto con pratica aperta: 8 pulsanti; a 1440 px 5 diventano icone | Nascondere Nuova, Importa e Calcolatrice dentro la pratica (sono nella pagina iniziale) | A |
| 2.3 | Pagina iniziale: gli stessi numeri 3 volte, più nota sul termine, versione e percorso dell'archivio | Una sola volta; versione e percorso in Guida › Informazioni | A |
| 2.4 | Riga «Quote come 1/2, importi come…» sotto ogni tabella; «In grassetto i dati richiesti»; identificativo tecnico sotto Salva | Togliere, oppure solo a tabella vuota | B, C |
| 2.5 | Elenco «Da sistemare» identico in EE, EF ed EH | Uno solo (vedi il punto più grave) | C |
| 2.6 | «File e invio»: 5 pillole di stato che ripetono le 5 spunte dei passi; «PROVA SIMULATA» sempre visibile; impronte SHA | Tenere i passi; avviso solo accanto al pulsante di prova; impronte nel suggerimento | C |
| 2.7 | Menu «stato: nessuno» anche sui quadri calcolati (EE, EF, EH) | Nasconderlo lì | C, B |
| 2.8 | Barra laterale: 7 quadri non selezionati, riga tecnica della versione, DV fuori vista a 1000 px | Gruppo ripiegabile «Altri quadri»; versione in Guida | B, A |
| 2.9 | Impostazioni: pagina unica di 3.600 px, 46 campi; nome dello studio e quadri proposti dentro «Aspetto» | Mostrare solo la sezione scelta; spostare le voci fuori posto | A |

## Lotto 3: linguaggio da programmatore

Esempi trovati:
- «L'allegato 'al_albero' non esiste (eliminato o identificativo errato)»;
- «serve esattamente un soggetto con ruolo 'defunto'»;
- «dato obbligatorio per <CodiceComuneAmministrativo>», senza dire di quale bene;
- «(chiavi: altra_casa…)»;
- «Fonti: docs/regole/prima_casa.md»;
- «contesto.allegati… ImageData»;
- «DEFLATE»;
- «DEFUNTO_NON_UNICO · persone»;
- titoli di scheda come «ps_medic01» o «d_38484fce3c3c», anche nella conferma di eliminazione;
- cronologia «gui · utente 2026-11-14T13:31:45+00:00», in ora UTC;
- Calcolatrice con «fornituraSUC13_v1.xsd… QuadroEF/…»;
- errore di importazione del parser in inglese;
- Diagnosi che rimanda a «docs/CONFIGURAZIONE_MCP.md».

Trovati da A, B, C e D.

Proposta: riscrivere questi testi in parole da studio, con il dato e il punto dove andare. Le schede devono avere un titolo
leggibile, per esempio «Fabbricato NAPOLI… → ESPOSITO LUCIA» oppure la descrizione e l'importo della passività. L'ora va
mostrata locale, in formato «14/11/2026 14:31».

## Lotto 4: meno clic

| # | Cosa | Proposta | Chi |
|---|---|---|---|
| 4.1 | Devoluzioni: circa 10 clic per erede e bene; per «metà e metà su tutto» servono 6 righe × 4 scelte; il diritto del bene va riscelto | Pulsante «Aggiungi devoluzione» nel riquadro del bene, con bene e diritto già compilati; voce «Applica le stesse quote a tutti i beni» | B, D |
| 4.2 | Codice catastale solo proposto con «Usa»; codice del comune amministrativo da scrivere a mano, che poi blocca il file | Se il campo è vuoto e il comune è riconosciuto, scriverlo direttamente (anche l'amministrativo e la provincia) | D, B |
| 4.3 | Valore catastale solo dopo aver salvato la riga (Salva, Usa, Salva) | Mostrarlo anche sulla riga nuova | B |
| 4.4 | «Controlla» chiede conferma per salvare | Salvare senza chiedere | A |
| 4.5 | Procedura guidata: il codice fiscale non viene per primo; un passo intero solo per «originaria» | Codice fiscale per primo; unire il passo «Tipo» alla conferma | A, D |
| 4.6 | CF del fornitore da riscrivere anche quando è il dichiarante | Pulsante «Usa CF del dichiarante» | C |
| 4.7 | EG: due modi diversi per aggiungere un documento | Tenerne uno | C, D |
| 4.8 | Stampe sparse in 3 posti, due quasi omonime «per il cliente» | Tutte nel passo 4 di «File e invio», con nomi distinti | C |

## Errori da correggere (non sono gusti)

| # | Errore | Chi |
|---|---|---|
| E1 | Ctrl+S con il cursore ancora nel campo: dice «Salvato», ma restano «Salva (1)» e «1 modifica non salvata», e alla ricarica compare «Abbandonare il sito?» | D |
| E2 | «File XML: aggiornato» in verde accanto a «Nessun file generato» | D |
| E3 | Pagina iniziale a 1440 px: Impostazioni e Guida a sola icona pur con lo spazio (compattaBarra non ricalcola) | A |
| E4 | Procedura guidata: la data di nascita presa dal codice fiscale compare come «1945-03-12» invece di GG/MM/AAAA | A, D |
| E5 | Importazione riuscita mostrata come errore rosso fisso | A |
| E6 | Il defunto compare tra i possibili eredi in DV e tra le persone collegate in ED | D |
| E7 | Avviso visura raggruppato: il rimedio dice «quadro EC» anche per il terreno di EB | C |
| E8 | «Prepara invio» attivo prima del controllo ufficiale positivo (non provato fino in fondo) | C |
| E9 | «0 righe» nell'intestazione con una riga nuova in corso | B |
| E10 | Impostazioni › Densità: la descrizione «aiuto quando entri nel campo» non è più vera dopo la modifica del 10/11 | B |
| E11 | Brogliaccio: diritto grezzo («1», «proprieta») e importi non formattati | C |
| E12 | Calcolatrice: errore rosso dopo aver scritto solo la data | A |
| E13 | Messaggi d'errore che restano a schermo cambiando quadro | C, D |
| E14 | Quadro EF «non calcolabile» se manca solo un file allegato | C |

## Da verificare sulle fonti prima di toccare (regole, non grafica)

- **IBAN obbligatorio anche con pagamento non contestuale.** Il revisore D è rimasto bloccato lì e ha bloccato anche la bozza
  tecnica. Va controllato sulle istruzioni e sull'XSD, non a memoria.
- **EH, domande per gli stati civili 5 e 7 anche con stato civile 2** (D).
- **Ruolo «Erede» e «Tipo di soggetto 1 — Erede»** chiedono la stessa cosa due volte (D): va controllato se il modello li
  distingue davvero.

## Da non toccare (piace a più revisori)

- Compilazione dal codice fiscale.
- «Vai al dato» nei Controlli.
- Somma delle quote «1/1 · completa» sul bene.
- Proposta del codice comune.
- Scheda a gruppi in densità compatta con il pannello sotto: un fabbricato intero in una schermata.
- Alt+N e Alt+D, Invio per passare al campo successivo.
- Albero genealogico generato e convertito in PDF/A.
- Riga dei totali.
- I 5 passi numerati di «File e invio».
- Suggerimenti al passaggio del mouse.

## Non verificato dai revisori

- Invio (simulato o reale), ricevute e controllo ufficiale fino in fondo: la pratica di D si è fermata all'IBAN.
- Tema scuro.
- Archivio con molte pratiche.
- Incolla da Excel.
- Quadri EL, EM, EN, EP ed EQ compilati.
- La finestra reale su Windows.
