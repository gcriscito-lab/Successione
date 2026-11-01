# Albero XSD SUC13 (generato) — fornituraSUC13_v1.xsd (SUC13_20250702)

Generato da `python -m successioni.telematico.mappa` a partire dagli XSD in `fonti/`. Non modificare a mano.
Notazione: `[min..max]` occorrenze; **grassetto** = elemento complesso; testo dopo — = annotazione XSD integrale (regole applicative NON eseguite dalla validazione di schema).

## Busta e intestazione

- **Fornitura** `[1..1]`
  - **Intestazione** `[1..1]`
    - _(estensione di `suc:Intestazione_Type`)_
    - TipoFornitore `[1..1]` : `cm:DatoAN_Type` — Assume i valori: 1 - Soggetti che inviano le proprie dichiarazione. 10 - C.A.F. dipendenti e pensionati; C.A.F. imprese; Societa' ed enti di cui all'art.3, comma 2 del DPR 322/98 (se tale societa' appartiene a un gruppo puo' trasmettere la propria dichiarazione e quelle delle aziende del gruppo); Altri intermediari di cui all'art.3. comma 3 lett a), b), c) ed e) del DPR 322/98; Societa' degli Ordini di cui all' art. 3 Decr. Dir. 18/2/99; Soggetto che trasmette le dichiarazioni per le quali l'impegno a trasmettere e' stato assunto da un professionista deceduto;
    - SpazioUtente `[0..1]` : `cm:DatoAN_Type`
  - **Dichiarazione** `[1..1]` : `suc:Dichiarazione_SUC_Type`
    - _(estensione di `cm:Documento_Type`)_
    - @identificativo : `Identificativo_Type` uso required

## Frontespizio

- **Frontespizio** `[1..1]`
  - _(estensione di `suc:FrontespizioSUC_Type`)_
  - CodiceFiscaleDefunto `[1..1]` : `cm:DatoCF_Type` — È il codice fiscale del contribuente defunto al quale si riferisce la dichiarazione e deve essere registrato in Anagrafe Tributaria. La non registrazione comporta lo scarto della dichiarazione in fase di accettazione.
  - **TipoDichiarazione** `[1..1]`
    - _scelta `[1..1]` fra:_
      - PrimaDichiarazione `[1..1]` : `cm:DatoCB_Type`
      - _sequenza `[1..1]`:_
        - DichiarazioneSostitutiva `[1..1]` : `suc:DichiarazioneSostitutiva_Type`
        - **EstremiPrimaDichiarazione** `[1..1]` : `suc:EstremiPrimaDichiarazione_Type`
          - Anno `[1..1]` : `cm:DatoDA_Type` — non può essere inferiore al 2014
          - Volume `[1..1]` : `cm:DatoNP_Type` {'maxLength': '5'} — Puo' assumere i valori '88888' e '88889'.
          - Numero `[1..1]` : `cm:DatoTL_Type` {'maxLength': '6'}
    - **Devoluzione** `[1..1]` — Obbligatorio almeno uno dei due campi tra "Devoluzione per Legge" e "Devoluzione per Testamento".
      - DevoluzionePerLegge `[0..1]` : `cm:DatoCB_Type` — Puo' essere presente insieme con "Devoluzione per Testamento".
      - DevoluzionePerTestamento `[0..1]` : `cm:DatoCB_Type` — Puo' essere presente insieme con "Devoluzione per Legge". Se selezionato va compilata la sezione "Testamento". Obbligatorio in assenza del campo Legge estera se il codice carica del dichiarante = 2. Obbligatorio se il codice carica del dichiarante = 7 o 9
      - **Testamento** `[0..1]` — Obbligatorio se campo 'Devoluzione per Testamento' = '1'. La sezione non deve essere compilata se campo 'Devoluzione per Testamento' diversa da '1'.
        - **Pubblicazione** `[0..1]` — Obbligatorio se non si tratta di testamento estero
          - PubblicoUfficiale `[1..1]` : `cm:DatoAN_Type` {'maxLength': '50'}
          - DataPubblicazioneTestamento `[1..1]` : `cm:DatoDT_Type` — Deve essere maggiore o uguale alla 'Data del decesso'.
        - **Registrazione** `[0..1]` — Obbligatorio se non si tratta di testamento estero La data di registrazione deve essere maggiore o uguale al campo 'Data pubblicazione testamento' e maggiore o uguale alla 'Data del decesso'.
          - _(estensione di `reg:EstremiRegistrazione_Type`)_
          - UfficioDiRegistrazione `[1..1]` : `reg:UfficioDiRegistrazione_Type`
          - Serie `[1..1]` : `reg:Serie_Type` {'maxLength': '2', 'minLength': '1'}
          - NumeroRegistrazione `[1..1]` : `cm:DatoNU_Type` {'maxLength': '6'}
          - SottonumeroRegistrazione `[0..1]` : `cm:DatoNU_Type` {'maxLength': '3'}
          - DataRegistrazione `[1..1]` : `cm:DatoDT_Type`
        - TestamentoEstero `[0..1]` : `cm:DatoCB_Type`
      - LeggeEstera `[0..1]` : `cm:DatoCB_Type` — Obbligatorio in assenza del campo devoluzione per testamento se il codice carica del dichiarante = 2
    - EventiEccezionali `[0..1]` : `cm:DatoN1_Type` valori ['1']
    - DataOpzione `[0..1]` : `cm:DatoDT_Type` — Deve essere precedente alla data del decesso e non inferiore al 1° gennaio 2017
  - **Beneficiari** `[0..1]`
    - NumeroEredi `[0..1]` : `cm:DatoNP_Type` {'maxLength': '3'} — Deve essere uguale al numero dei soggetti del quadro EA per i quali il campo 'Tipo soggetto' assume valore '1'.
    - NumeroChiamati `[0..1]` : `cm:DatoNP_Type` {'maxLength': '3'} — Deve essere uguale al numero dei soggetti del quadro EA per i quali il campo 'Tipo soggetto' assume valore '3'.
    - NumeroLegatari `[0..1]` : `cm:DatoNP_Type` {'maxLength': '3'} — Deve essere uguale al numero dei soggetti del quadro EA per i quali il campo 'Tipo soggetto' assume valore '2'.
    - AccettazioneConBeneficioInventario `[0..1]` : `cm:DatoCB_Type`
  - **DatiDefunto** `[1..1]`
    - **DatiAnagrafici** `[1..1]` : `reg:Dati_Anagrafici_Type` — Se nato in Italia i campi 'Comune di nascita' e 'Provincia di nascita' devono essere congruenti. Per i nati all'estero inserire 'EE' nel campo 'Provincia di nascita' e lo stato estero nel campo 'Comune di nascita' .
      - Cognome `[1..1]` : `reg:DatoAN2_Type` {'maxLength': '80'}
      - Nome `[1..1]` : `reg:DatoAN2_Type` {'maxLength': '80'}
      - Sesso `[1..1]` : `sc:Sesso_Type`
      - DataNascita `[1..1]` : `cm:DatoDT_Type`
      - ComuneNascita `[1..1]` : `cm:DatoAN_Type` {'maxLength': '50'}
      - ProvinciaNascita `[1..1]` : `cm:PN_Type`
    - **UlterioriDati** `[1..1]`
      - DataDecesso `[1..1]` : `cm:DatoDT_Type` — Deve essere maggiore o uguale al campo 'Data di nascita' del defunto e maggiore del 2 ottobre 2006. Se dichiarazione sostitutiva è = '1' o '2' l'anno deve essere minore o uguale al campo 'Anno prima dichiarazione'.' In assenza di residenza estera e di morte presunta la non corrispondenza con quanto presente in Anagrafe Tributaria comporta lo scarto della dichiarazione in fase di accettazione.
      - StatoCivile `[1..1]` : `reg:StatoCivile_Type`
      - ResidenzaEstera `[0..1]` : `reg:ResidenzaEstera_Type`
  - **Presentatore** `[1..1]`
    - CodiceFiscale `[1..1]` : `cm:DatoCF_Type` — Deve essere diverso dal campo 'Codice fiscale del defunto'. Deve essere relativo ad un soggetto maggiorenne.
    - CodiceCarica `[1..1]` : `reg:CodiciCarica_Type` — Può valere '7' (esecutore testamentario) solo se il campo 'Devoluzione per testamento' = '1'. Se vale '5' (curatore dell’eredità giacente) nel quadro EA deve essere presente solo un soggetto e con 'Tipo soggetto' = 6 (Altro) in caso di prima dichiarazione. Se vale '9' (trustee o suo rappresentante) nel quadro EA deve essere presente un soggetto con codice fiscale uguale al dichiarante e 'Tipo soggetto' = 5 (Trust). Se nel quadro EA è presente un soggetto con Tipo soggetto' = 5 (Trust) deve valere '9' (trustee o suo rappresentante) Se vale '1' o '2' (erede, legatario, chiamato all’eredità) il cf del soggetto che presenta la dichiarazione deve essere presente nel Quadro EA ed il tipo soggetto presente nel quadro EA deve essere coerente.
    - DecorrenzaTerminePresentazione `[0..1]` : `cm:DatoDT_Type` — Se presente non deve essere inferiore alla 'data decesso'
    - **DatiAnagrafici** `[1..1]` : `reg:Dati_Anagrafici_Type` — Se nato in Italia i campi 'Comune di nascita' e 'Provincia di nascita' devono essere congruenti. Per i nati all'estero inserire 'EE' nel campo 'Provincia di nascita' e lo stato estero nel campo 'Comune di nascita' .
      - Cognome `[1..1]` : `reg:DatoAN2_Type` {'maxLength': '80'}
      - Nome `[1..1]` : `reg:DatoAN2_Type` {'maxLength': '80'}
      - Sesso `[1..1]` : `sc:Sesso_Type`
      - DataNascita `[1..1]` : `cm:DatoDT_Type`
      - ComuneNascita `[1..1]` : `cm:DatoAN_Type` {'maxLength': '50'}
      - ProvinciaNascita `[1..1]` : `cm:PN_Type`
    - Telefono `[0..1]` : `cm:DatoTL_Type` — deve essere presente almeno uno dei campi Telefono o Email
    - Email `[0..1]` : `cm:DatoEM_Type` — deve essere presente almeno uno dei campi Telefono o Email
    - **ResidenteEstero** `[0..1]`
      - _(estensione di `sc:Residenza_Estera_Type`)_
      - CodiceStatoEstero `[1..1]` : `cm:DatoAN_Type` {'maxLength': '3', 'minLength': '3'}
      - StatoFederato `[0..1]` : `cm:DatoAN_Type` {'maxLength': '24'}
      - LocalitaEstero `[0..1]` : `cm:DatoAN_Type`
      - IndirizzoEstero `[1..1]` : `cm:DatoAN_Type`
      - StatoEstero `[1..1]` : `cm:DatoAN_Type` {'maxLength': '34'}
    - CodiceFiscaleRappresentato `[0..1]` : `cm:DatoCF_Type` — obbligatorio se codice carica = 3 (rappresentante legale o tutore di legatario) o 4 (rappresentante legale, tutore). Non deve essere presente se codice carica = 1 (erede, chiamato all’eredità) o 2 (legatario) o 5 (curatore dell’eredità giacente) o 6 (amministratore dell’eredità) o 7 (esecutore testamentario) Può essere presente se codice carica = 8 (persona immessa nel possesso temporaneo dei beni dell’assente) o 9 (trustee o suo rappresentante) Deve essere diverso dal codice fiscale del defunto e del soggetto che presenta il modello
  - **FirmaModello** `[1..1]` : `suc:Firma_ModelloSuc_Type`
    - CasellaEA `[0..1]` : `cm:DatoCB_Type`
    - CasellaEB `[0..1]` : `cm:DatoCB_Type`
    - CasellaEC `[0..1]` : `cm:DatoCB_Type`
    - CasellaED `[0..1]` : `cm:DatoCB_Type`
    - CasellaEE `[0..1]` : `cm:DatoCB_Type`
    - CasellaEF `[0..1]` : `cm:DatoCB_Type`
    - CasellaEG `[0..1]` : `cm:DatoCB_Type`
    - CasellaEH `[0..1]` : `cm:DatoCB_Type`
    - CasellaEI `[0..1]` : `cm:DatoCB_Type`
    - CasellaEL `[0..1]` : `cm:DatoCB_Type`
    - CasellaEM `[0..1]` : `cm:DatoCB_Type`
    - CasellaEN `[0..1]` : `cm:DatoCB_Type`
    - CasellaEO `[0..1]` : `cm:DatoCB_Type`
    - CasellaEP `[0..1]` : `cm:DatoCB_Type`
    - CasellaEQ `[0..1]` : `cm:DatoCB_Type`
    - CasellaER `[0..1]` : `cm:DatoCB_Type`
    - FirmaDichiarante `[1..1]` : `cm:DatoCB_Type`
  - **CasiParticolari** `[0..1]` — Non può essere presente se dichiarazione sostitutiva = 3 (Dichiarazione integrativa con sola presentazione di documentazione).
    - CasiParticolari `[0..1]` : `cm:DatoCB_Type` — Obbligatorio in assenza dei quadri EB, EC ed in presenza di almeno uno dei quadri EL, EM. Obbligatorio in presenza di soli immobili con codice diritto ‘10’ nei quadri EB, EC. Obbligatorio se tutti i soggetti del quadro EA hanno codice ‘3’ (chiamato). Obbligatorio se codice carica del frontespizio 5 (curatore dell’eredità giacente) o 6 (amministratore dell’eredità) o 9 (trustee o suo rappresentante) se non è dichiarazione sostitutiva = 3
    - CopiaConforme `[0..1]` : `cm:DatoCB_Type`
    - FirmaDichiarante `[1..1]` : `cm:DatoCB_Type` — Campo obbligatorio in presenza di uno dei due campi precedenti
  - **ImpegnoATrasmettere** `[0..1]` — La sezione è obbligatoria se il TipoFornitore è impostato con il valore 10 ed il codice fiscale del responsabile della fornitura è diverso dal codice fiscale del richiedente. Non può essere presente negli altri casi.
    - _(estensione di `reg:ImpegnoATrasmettere_Type`)_
    - CFintermediario `[1..1]` : `cm:DatoCF_Type` — Il codice fiscale deve essere formalmente corretto e registrato in Anagrafe tributaria. La non registrazione comporta lo scarto della richiesta in fase di accettazione.
    - ImpegnoATrasmettere `[1..1]` : `reg:ImpegnoPresentazione_Type`
    - DataImpegno `[1..1]` : `cm:DatoDT_Type`
    - FirmaIntermediario `[1..1]` : `cm:DatoCB_Type`
  - IdentificativoProdSoftware `[0..1]` : `cm:DatoAN_Type` {'maxLength': '16'}
  - _scelta `[1..1]` fra:_
    - **Versamento** `[0..1]` : `reg:Versamento_Type` — La sezione e' obbligatoria in presenza del campo EF19 o dei campi EF24 colonna 1 o EF24 colonna 2 (importi diversi da zero) ed in assenza della sezione F24
      - IBAN `[1..1]` : `cm:DatoAN_Type` {'length': '27'}
      - CodiceFiscaleTitolareCC `[1..1]` : `cm:DatoCF_Type` — Se il Tipo fornitore vale '1' deve essere uguale al Codice fiscale del richiedente la registrazione o del Soggetto rappresentato, se presente Se il Tipo fornitore vale '10' deve essere uguale al Codice fiscale del fornitore o del richiedente la registrazione o del Soggetto rappresentato, se presente
    - **F24** `[0..1]` — La sezione è obbligatoria in presenza del campo EF19 o dei campi EF24 colonna 1 o EF24 colonna 2 (importi diversi da zero) ed in assenza della sezione versamento Può essere presente solo per le dichiarazioni inviate tramite Ufficio delle Entrate
      - Comune `[1..1]` : `cm:DatoAN_Type`
      - Provincia `[1..1]` : `cm:PE_Type` — Congruente con il campo 'Codice comune' se diverso da 'EE''.
      - CodiceComune `[0..1]` : `cm:DatoAN_Type` — Obbligatorio se 'Provincia' diverso da 'EE''. Se 'provincia' = 'EE' non valorizzare. Congruente con il campo 'Provincia'. Il codice deve essere tra quelli riportati nel sito "www.agenziaentrate.gov.it".
      - Indirizzo `[1..1]` : `cm:DatoAN_Type`
  - ImportoDaVersare `[0..1]` : `cm:DatoVP_Type` — E' obbligatorio in presenza del del campo EF17 o dei campi EF22 colonna 1 o EF22 colonna 2 (importi diversi da zero) Può anche essere uguale a zero.
  - **CampiServizio** `[0..1]` — Può essere presente solo per le dichiarazioni inviate tramite Ufficio delle Entrate
    - Flag `[0..1]` : `cm:DatoCB_Type`
    - Data `[0..1]` : `cm:DatoDT_Type` — non può essere inferiore al 23/01/2017
    - Flag2 `[0..1]` : `cm:DatoCB_Type`
    - Flag3 `[0..1]` : `cm:DatoCB_Type`
  - Lingua `[0..1]` : `cm:DatoN1_Type` valori ['1', '2']

## QuadroEA

- **QuadroEA** `[0..1]` : `suc:QuadroEA_Type` — Se codice carica del frontespizio = 1 (erede, chiamato all’eredità) o 2 (legatario), il dichiarante deve essere presente nel quadro EA. Se codice carica del frontespizio = 5 (curatore dell’eredità giacente) il dichiarante non deve essere presente nel quadro EA. Se codice carica del frontespizio = 3 (rappresentante legale o tutore di legatario) o 4 (rappresentante legale, tutore) e se il campo 'Prima dichiarazione del frontespizio = '1' , il dichiarante non deve essere presente nel quadro EA oppure deve essere presente nel quadro EA come rinunciatario. Se nel frontespizio è presente il codice fiscale del soggetto rappresentato, questo deve essere presente nel quadro EA ed il dichiarante non deve essere presente nel quadro EA salvo che non sia rinunciatario con codice carica 3 o 4 nel frontespizio Non deve essere presente se 'Dichiarazione sostitutiva è uguale a '3'
  - **Modulo** `[1..n]` : `suc:ModuloEA_Type`
    - **Soggetto** `[1..3]` : `suc:Soggetto_Type` — Non possono essere presenti soggetti che non siano indicati nella sezione devoluzione di almeno un quadro relativo ai beni (EB, EC, EL, EM, EN, EO, EP, EQ, ER) o che non siano rinunciatari
      - CodiceFiscale `[1..1]` : `cm:DatoCF_Type` — Il campo Codice fiscale può essere indicato su più righi. In assenza delle sezioni 'Successione per rappresentanza' o 'Parte riservata al trust' il grado di parentela deve essere uguale su tutti i righi e il tipo soggetto deve essere diverso. In presenza di almeno una sezione 'Successione per rappresentanza' o 'Parte riservata al trust' il grado di parentela può essere differente. Deve assumere valore diverso da quello indicato nel campo 'Codice fiscale del defunto' Se tipo soggetto = 5 (Trust) deve essere uguale al codice fiscale del dichiarante. Se compilato il campo denominazione deve essere relativo ad un soggetto diverso da persona fisica.
      - TipoSoggetto `[1..1]` : `suc:TipoSoggetto_Type` — Puo' valere '2' (Legatario) solo se 'Devoluzione per testamento' del frontespizio = '1' o se 'legge estera' del frontespizio = 1. Puo' valere '4' (Coniuge/Parte dell’unione civile superstite rinunciatario) solo se 'Stato civile' del frontespizio = '2' (coniugato/a in regime di comunione dei beni) o '3' (coniugato/a in regime di separazione dei beni) o '5' (separato/a) o '7' (Parte dell’unione civile). Puo' valere '5' (Trust) solo se il campo 'Devoluzione per Testamento' del frontespizio e' valorizzato. Se è presente il valore '6' (Altro) non possono essere presenti altri soggetti nel quadro. E' ammesso un solo rigo con il tipo soggetto = ‘4’ (Coniuge/Parte dell’unione civile superstite rinunciatario) ed in tal caso il Grado di parentela deve essere ‘01’ (Coniuge/Parte dell’unione civile);. Se codice carica del frontespizio = 9 (trustee o suo rappresentante) deve essere sempre = 5 (Trust). In caso di beneficiario presente su più righi, il tipo soggetto non può assumere il valore 3 (Chiamato) se esiste un altro rigo per lo stesso beneficiario con tipo soggetto = 1 (Erede) o 4 (Coniuge/Parte dell’unione civile superstite rinunciatario). In caso di beneficiario presente su più righi, il tipo soggetto non può assumere il valore 1 (Erede) se esiste un altro rigo per lo stesso beneficiario con tipo soggetto = 3 (Chiamato) o 4 (Coniuge/Parte dell’unione civile superstite rinunciatario). In caso di beneficiario presente su più righi, il tipo soggetto non può assumere il valore 4 (Coniuge/Parte dell’unione civile superstite rinunciatario) se esiste un altro rigo per lo stesso beneficiario con tipo soggetto = 1 (Erede) o 3 (Chiamato).
      - Rinuncia `[0..1]` : `cm:DatoCB_Type` — Dato obbligatorio se tipo soggetto = '4' (Coniuge/Parte dell’unione civile superstite rinunciatario). Non può essere presente se si tratta del dichiarante (se non è presente per lo stesso soggetto un altro rigo del quadro EA in cui non è presente la rinuncia). Non può essere presente se tipo soggetto = '1' (Erede). In presenza di eredi rinunciatari nel quadro EH deve essere presente almeno un rigo del quadro EA con questo campo impostato. Non deve essere presente in assenza di eredi rinunciatari nel quadro EH
      - GradoParentela `[1..1]` : `suc:GradoParentela_Type` — E' ammesso un solo rigo con il campo 'Grado di parentela' = '01' (Coniuge/Parte dell’unione civile del defunto). Può assumere valore '01' (Coniuge/Parte dell’unione civile) solo se il campo 'Stato civile' del frontespizio assume valore '2' (coniugato/a in regime di comunione dei beni) o '3' (coniugato/a in regime di separazione dei beni) o '5' (separato/a) o '7' (Parte dell’unione civile). Deve assumere valore '01' (Coniuge/Parte dell’unione civile) se 'Tipo soggetto' = '4' (Coniuge/Parte dell’unione civile superstite rinunciatario). Deve assumere il valore '35' (Estraneo/a) se 'Tipo soggetto' = 5 (Trust) e codice fiscale beneficiario finale assente su tutti i righi del quadro EA. Se compilato il campo 'Denominazione' ed il tipo soggetto non è uguale a 5 può assumere solo i seguenti valori: 35 (Estraneo/a), 36 (Stato), 37, 38, 39. Se è uguale a 36 (Stato), 37, 38, 39 ed il tipo soggetto non è uguale a 5 deve essere presente la denominazione. In presenza di devoluzione per legge (e in assenza di devoluzione per testamento e se 'legge estera' del frontespizio = 0), deve essere diverso da 12, 13, 14, 17, 18, 19, 23, 24, 25, 26 (affini), 35, 37, 38, 39. In presenza di devoluzione per legge (e in assenza di devoluzione per testamento e se 'legge estera' del frontespizio = 0), può essere uguale a 36 (Stato) solo se non sono presenti altri soggetti nel quadro. In caso di beneficiario presente su più righi e tipo soggetto diverso da “5” (Trust), il grado di parentela deve coincidere su tutti i righi interessati Se Grado di parentela: 02 (Figlio/a), 04 (Nipote (figlio/a di figlio/a)), 06 (Pronipote) o 08 (Figlio/a del Pronipote), il soggetto deve avere un’età non superiore a quella del defunto; Se Grado di parentela: 03 (Genitore), 5A o 5B (Nonno/a), 7A o 7B (Bisavo) o 9A o 9B (Trisavo), il soggetto deve essere maggiore di età del defunto; Se Grado di parentela: 01 (Coniuge/Parte dell’unione civile del defunto), il soggetto deve essere minore di età dei soggetti con grado di parentela 12 (Genitore del Coniuge/Parte dell’unione civile), 14 (Nonno/a del Coniuge/Parte dell’unione civile) e 19 (Bisavo del Coniuge/Parte dell’unione civile);
      - PortatoreHandicap `[0..1]` : `cm:DatoCB_Type` — Puo' valere '1' solo se 'Tipo soggetto' = 1 (Erede), 2 (Legatario), 3 (Chiamato), 4 (Coniuge/Parte dell’unione civile superstite rinunciatario) , 5 (Trust). Non può essere presente se 'Grado di parentela' uguale a '36', '37', '38' o '39'. Non può essere presente se tipo soggetto = 5 (Trust) e codice fiscale beneficiario finale assente. In caso di soggetto presente su più righi e tipo soggetto diverso da “5” (Trust), il campo persona con disabilità deve coincidere su tutti i righi interessati.
      - _scelta `[1..1]` fra:_
        - **DatiAnagrafici** `[1..1]` : `reg:Dati_Anagrafici_Type`
          - Cognome `[1..1]` : `reg:DatoAN2_Type` {'maxLength': '80'}
          - Nome `[1..1]` : `reg:DatoAN2_Type` {'maxLength': '80'}
          - Sesso `[1..1]` : `sc:Sesso_Type`
          - DataNascita `[1..1]` : `cm:DatoDT_Type`
          - ComuneNascita `[1..1]` : `cm:DatoAN_Type` {'maxLength': '50'}
          - ProvinciaNascita `[1..1]` : `cm:PN_Type`
        - Denominazione `[1..1]` : `reg:DatoAN2_Type` {'maxLength': '150'}
      - **ResidenzaEstera** `[0..1]`
        - _(estensione di `sc:Residenza_Estera_Type`)_
        - CodiceStatoEstero `[1..1]` : `cm:DatoAN_Type` {'maxLength': '3', 'minLength': '3'}
        - StatoFederato `[0..1]` : `cm:DatoAN_Type` {'maxLength': '24'}
        - LocalitaEstero `[0..1]` : `cm:DatoAN_Type`
        - IndirizzoEstero `[1..1]` : `cm:DatoAN_Type`
        - StatoEstero `[1..1]` : `cm:DatoAN_Type` {'maxLength': '34'}
      - **SuccessionePerRappresentazione** `[0..1]` — La sezione non deve essere compilata se 'Tipo soggetto' = '5'. (Trust) La sezione non deve essere compilata se il grado di parentela del beneficiario (campo 3) è diverso da 04 (Nipote (figlio/a di figlio/a)), 06 (Pronipote), 08 (Figlio/a del Pronipote), 15 (Nipote (figlio/a di fratello/sorella)), 20 (Figlio/a di nipote) e 27 (Nipote di nipote) In presenza di devoluzione per legge (e in assenza di devoluzione per testamento e se 'legge estera' del frontespizio = 0) la sezione è obbligatoria se il grado di parentela del beneficiario (campo 3) è uguale a 04 (Nipote (figlio/a di figlio/a)) o 15 (Nipote (figlio/a di fratello/sorella))
        - CodiceFiscaleSoggettoRappresentato `[1..1]` : `cm:DatoCF_Type` — Deve essere diverso dal codice fiscale del soggetto e dal codice fiscale del defunto. Non può essere uguale al codice fiscale del soggetto presente in altri righi del quadro EA, a meno che questi non sia rinunciatario
        - GradoParentela `[1..1]` : `suc:GradoParentela2_Type` — Deve essere = 2 (Figlio/a) se il grado di parentela del beneficiario (campo 3) = 04 (Nipote (figlio/a di figlio/a)), 06 (Pronipote), 08 (Figlio/a del Pronipote). Deve essere = 10 (Fratello/sorella germano) o 11 (Fratello/sorella unilaterale) se il grado di parentela del beneficiario (campo 3) = 15 (Nipote (figlio/a di fratello/sorella)), 20 (Figlio/a di nipote) e 23 (Nipote di nipote). Se il Codice fiscale del soggetto rappresentato è presente più volte nel quadro EA (sia come beneficiario che come rappresentato) , il grado di parentela corrispondente deve essere sempre lo stesso
      - **Trust** `[0..1]` — Obbligatorio se 'Tipo soggetto' = '5' (Trust) e grado di parentela diverso da 35 (estraneo). Obbligatorio se 'Tipo soggetto' = '5' (Trust) e Persone con disabilità uguale a 1. Se tipo soggetto = 1,2,3,4,6 la sezione non deve essere compilata. Se tipo soggetto = 5 e grado di parentela = 35 (estraneo) la sezione può essere compilata
        - CodiceFiscaleTrust `[0..1]` : `cm:DatoCF_Type` — Deve essere diverso dal codice fiscale del soggetto, dal codice fiscale del defunto e dal codice fiscale del beneficiario finale
        - CodiceFiscaleBeneficiario `[0..1]` : `cm:DatoCF_Type` — Obbligatorio se 'Tipo soggetto' = '5' (Trust) e grado di parentela diverso da 35 (estraneo). Deve essere diverso dal codice fiscale del soggetto, dal codice fiscale del defunto e dal codice fiscale del trust. Non può essere uguale al codice fiscale del beneficiario finale presente in altri righi del quadro EA.

## QuadroEB

- **QuadroEB** `[0..1]` — Non deve essere presente se 'Dichiarazione sostitutiva è uguale a '3'. In presenza di almeno un rigo del quadro EC con categoria = D10 e valore = 0 o di un rigo del quadro EB con natura = R e valore = 0, deve essere presente almeno un rigo con natura = T. In presenza di codice ‘1’ nella casella ‘Dichiarazione sostitutiva’ dei Dati Generali, deve essere presente almeno un quadro tra EB e EC
  - **Modulo** `[1..n]`
    - **Terreni** `[1..2]` — Possono essere presenti righe duplicate (comune, foglio, particella, subalterno) solo se hanno codice diritto diverso
      - **Luogo** `[0..1]` : `reg:Luogo_Type` — obbligatorio se non è presente il campo continuazione del rigo precedente
        - Provincia `[1..1]` : `reg:PENonTavolare_Type` — provincie italiane in vigore (con esclusione di quelle in vigore nel catasto tavolare) e “EE” che indica un paese estero.
        - _scelta `[1..1]` fra:_
          - **Italia** `[1..1]` : `reg:ItaliaType` — Obbligatorio se 'Provincia' diverso da 'EE''. Se 'provincia' = 'EE' non valorizzare.
            - ComuneAmministrativo `[1..1]` : `cm:DatoAN_Type` {'maxLength': '50'}
            - CodiceComune `[1..1]` : `cm:DatoAN_Type` — Congruente con il campo 'Provincia'.
            - Indirizzo `[0..1]` : `reg:TipologiaIndirizzo_Type`
            - CodiceComuneAmministrativo `[1..1]` : `cm:DatoAN_Type` — Congruente con il campo 'Comune amministrativo '
          - **Estero** `[1..1]` — Obbligatorio se 'Provincia' = 'EE''. Se 'provincia' diverso da 'EE' non valorizzare.
            - _(estensione di `sc:Residenza_Estera_Type`)_
            - CodiceStatoEstero `[1..1]` : `cm:DatoAN_Type` {'maxLength': '3', 'minLength': '3'}
            - StatoFederato `[0..1]` : `cm:DatoAN_Type` {'maxLength': '24'}
            - LocalitaEstero `[0..1]` : `cm:DatoAN_Type`
            - IndirizzoEstero `[1..1]` : `cm:DatoAN_Type`
            - StatoEstero `[1..1]` : `cm:DatoAN_Type` {'maxLength': '34'}
      - **DatiTerreni** `[0..1]` : `reg:DatiTerreni_Type` — Obbligatorio se 'Provincia' diverso da 'EE'. Se 'provincia' = 'EE' non valorizzare.
        - **DatiCatastali** `[1..1]` : `reg:DatiCatastali_Type`
          - Foglio `[1..1]` : `cm:DatoAN_Type` {'maxLength': '4'}
          - Particella `[1..1]` : `reg:Particella_Type` {'maxLength': '5'} — Riportare il numero di particella, indicato nel documento catastale. Nel caso di immobile graffato riportare solo la prima particella.
          - Subalterno `[0..1]` : `cm:DatoAN_Type` {'maxLength': '4'}
        - **DatiTerreni** `[1..1]` : `reg:DatiCatastaliTerreni_Type`
          - **Superficie** `[0..1]`
            - SuperficieEttari `[0..1]` : `cm:DatoNP_Type` {'maxLength': '5'}
            - SuperficieAre `[0..1]` : `cm:DatoNP_Type` {'maxLength': '2'}
            - SuperficieCentiare `[0..1]` : `cm:DatoNP_Type` {'maxLength': '2'}
          - Natura `[1..1]` : `reg:CodiciNatura_Type`
          - RedditoDominicale `[0..1]` : `cm:DatoVP_Type` — Obbligatorio se natura è uguale a R e valore = 0
      - **Possesso** `[0..1]` : `suc:Possesso_Type` — obbligatorio se non è presente il campo continuazione del rigo precedente
        - PossessoNumeratore `[1..1]` : `cm:DatoVP_Type`
        - PossessoDenominatore `[1..1]` : `cm:DatoNP_Type` {'maxLength': '6'}
      - CodiceDiritto_P `[0..1]` : `suc:CodiciDirittoImmobili_Type` — obbligatorio se non è presente il campo continuazione del rigo precedente.
      - BeneAziendale `[0..1]` : `cm:DatoCB_Type` — se barrata la casella “Bene aziendale", dovra' essere compilato il quadro EN. Obbligatorio se è presente nella sezione devoluzione almeno un rigo con agevolazione Q o G.
      - DiscordanzaDatiIntestatario `[0..1]` : `cm:DatoCB_Type` — Se selezionato e' obbligatoria la presenza di un modulo del quadro EI.
      - PassaggiSenzaAttiLegali `[0..1]` : `cm:DatoCB_Type` — Se selezionato e' obbligatoria la presenza di un modulo del quadro EI.
      - ImpostaVersataEstero `[0..1]` : `cm:DatoNP_Type` — Se presente deve essere presente il campo EG4
      - TipologiaTerreno `[0..1]` : `reg:TerrenoEdificabile_Type` — Vale: 1 (terreno edificabile) , 2 (terreno parzialmente edificabile) , 3 (terreno non edificabile) Obbligatorio se non è presente il campo continuazione del rigo precedente.
      - Valore `[0..1]` : `cm:DatoNP_Type` {'maxLength': '13'} — obbligatorio se non è presente il campo continuazione del rigo precedente e se natura è diversa da R.
      - ValorePrecSucc `[0..1]` : `cm:DatoNP_Type` {'maxLength': '13'} — Non può essere presente in assenza di riduzioni art. 25 c. 1 nella sezione devoluzione. Campo obbligatorio in presenza di riduzioni art. 25 c. 1 nella sezione devoluzione. Non può essere superiore al campo valore.
      - **DevoluzioneEB** `[0..1]` : `suc:DevoluzioneImmobili_Type` — Se il numero dei soggetti a cui sono devoluti i singoli beni supera il numero dei campi disponibili, barrare la casella continuazione e riportare l’indicazione degli ulteriori soggetti nella sezione devoluzione del rigo che segue senza compilare la parte relativa ai dati identificativi del bene. In presenza del Quadro EA la sezione deve essere compilata.
        - **Devoluzione** `[0..3]` — la sezione non puo' essere presente in assenza di quadro EA
          - _(estensione di `suc:DevoluzioneSingolaImmobili_Type`)_
          - **IdentificazioneSoggetto** `[1..1]` : `suc:IdentificazioneRigo_Type` — Non può essere indicato un soggetto (rigo-modulo) non presente nel quadro EA. Non può essere indicato un soggetto (rigo-modulo) rinunciatario. In presenza di devoluzione per legge (e in assenza di devoluzione per testamento e se 'legge estera' del frontespizio = 0) non può essere indicato un soggetto (rigo-modulo) con grado di parentela = 01 (Coniuge/Parte dell’unione civile) se nel quadro EH è barrata la casella di separazione per colpa o la casella di scioglimento dell'unione civile. In presenza di devoluzione per legge (e in assenza di devoluzione per testamento e se 'legge estera' del frontespizio = 0), se nel Quadro EA i tipi soggetto sono tutti ‘1’ (erede) o tutti ‘3’ (chiamati) o '4' (Coniuge/Parte dell’unione civile superstite rinunciatario), nella sezione Devoluzione devono essere riportati i dati identificativi (Rigo n. e Mod. N.) dei soggetti indicati nel Quadro EA, in ordine progressivo; Nel caso di un soggetto che eredita diversi diritti sullo stesso bene (ad es. 1/3 nuda proprietà e 2/3 di usufrutto), ripetere l’indicazione del soggetto su tanti righi quanti sono i diritti a lui devoluti. Nella sezione Devoluzione, lo stesso beneficiario può essere presente su più righi solo se i codici diritto sono diversi;
            - Rigo `[1..1]` : `cm:DatoN1_Type`
            - Modulo `[1..1]` : `cm:DatoNP_Type` {'maxLength': '3'}
          - **Quota** `[1..1]` : `suc:Quota_Type` — In presenza di devoluzione per legge (e in assenza di devoluzione per testamento e se 'legge estera' del frontespizio = 0), se nel Quadro EA i tipi soggetto sono tutti ‘1’ (erede) o tutti ‘3’ (chiamati) o '4' (Coniuge/Parte dell’unione civile superstite rinunciatario), il campo quota deve essere compilato in base al grado di parentela, come riportato nell'allegato 5 al modello. Se il codice diritto presente nella sezione devoluzione coincide con il codice diritto del defunto e non sono presenti in devoluzione i tre diritti aggiuntivi (superficie, uso e abitazione), il campo valore quota è uguale al prodotto del valore del bene per la quota devoluzione.
            - **QuotaElementi** `[1..1]` : `suc:QuotaElementi_Type` — La somma delle quote di devoluzione/ripartizione deve essere uguale all'intero (1/1).
              - QuotaNumeratore `[1..1]` : `cm:DatoNP_Type`
              - QuotaDenominatore `[1..1]` : `cm:DatoNP_Type`
            - QuotaValore `[0..1]` : `cm:DatoVP_Type` — Obbligatorio per i fabbricati se categoria catastale è diversa da D10. Obbligatorio per i terreni se natura è diversa da R. Il valore della singola quota non può essere maggiore del campo 'Valore' del bene oggetto della devoluzione/ripartizione (per il quadro EO non può essere maggiore della somma dei campi 'Valore' e 'Valore esente'). La somma dei valori delle quote deve essere uguale al campo 'Valore' del bene oggetto della devoluzione/ripartizione (per il quadro EO deve essere uguale alla somma dei campi 'Valore' e 'Valore esente'); è accettabile uno scostamento massimo pari all’1% del valore del bene oggetto della devoluzione/ripartizione (per il quadro EO della somma dei campi 'Valore' e 'Valore esente'), e comunque, in valore assoluto, non superiore a 100 €
          - CodiceDiritto_Rip `[1..1]` : `suc:CodiciDiritto_Type` — In presenza di devoluzione per legge (e in assenza di devoluzione per testamento e se 'legge estera' del frontespizio = 0), se nel Quadro EA i tipi soggetto sono tutti ‘1’ (erede) o tutti ‘3’ (chiamati) o '4' (Coniuge/Parte dell’unione civile superstite rinunciatario), i codici diritto presenti nella sezione devoluzione devono coincidere con il codice diritto del defunto. Per i quadri EN, EO, EP, EQ, ER sono ammessi solo i codici 1, 2, 7, 8 In presenza di devoluzione per testamento o se 'legge estera' del frontespizio = 1 ed in assenza di "discordanza dati intestatario” e/o “passaggi senza atti legali", nei quadri EB, EC, EL e EM deve esserci coerenza tra il codice diritto del defunto e quelli indicati nella sezione devoluzione secondo la seguente tabella: diritti scomponibili (1, 1s, 1t): - se il de cuius trasferisce la proprietà (1), nella sezione devoluzione possono essere indicati: proprietà (1) e/o proprietà superficiaria (1s) + proprietà per l’area (1t) e/o nuda proprietà (2) + usufrutto (8) e/o diritto del concedente (4) + enfiteusi (5) e/o proprietà superficiaria (1s) + nuda proprietà per l’area (2t) + usufrutto su proprietà per l’area (8t) e/o nuda proprietà superficiaria (2s) + usufrutto su proprietà superficiaria (8s) + proprietà per l’area (1t) e/o nuda proprietà superficiaria (2s) + usufrutto su proprietà superficiaria (8s) + nuda proprietà per l’area (2t) + usufrutto su proprietà per l’area (8t); i diritti di uso (7), abitazione (3) e superficie (6) possono essere presenti in aggiunta a tutti i diritti sopra riportati o in qualsiasi loro combinazione. - se il de cuius trasferisce la proprietà superficiaria (1s), nella sezione devoluzione possono essere indicati: proprietà superficiaria (1s) e/o nuda proprietà superficiaria (2s) + usufrutto su proprietà superficiaria (8s); i diritti di uso su proprietà superficiaria (7s) e abitazione su proprietà superficiaria (3s) possono essere presenti in aggiunta a tutti i diritti sopra riportati o in qualsiasi loro combinazione. - se il de cuius trasferisce la proprietà per l’area (1t), nella sezione devoluzione possono essere indicati: proprietà per l’area (1t) e/o nuda proprietà per l’area (2t) + usufrutto su proprietà per l’area (8t). diritti non scomponibili (2, 2s, 2t, 4, 5, 6, 10): se il de cuius trasferisce uno di questi diritti, nella sezione devoluzione può essere indicato solo lo stesso diritto
          - Agevolazioni `[0..1]` : `suc:CodiciAgevolazioni_Type` — In presenza di bene aziendale il campo non deve essere presente oppure deve avere valore = D o Q o G. I codici agevolazione P, Z, X e Y possono essere selezionati solo nella sezione devoluzione dei quadri EC, EM e se 'Provincia' diverso da 'EE''. L’agevolazione “P” può essere presente per uno stesso soggetto più volte solo se relative allo stesso immobile (codice comune, sezione urbana, foglio, particella, subalterno) L’agevolazione “X” o "Y" può essere presente per uno stesso soggetto per un solo immobile per ciascuna delle categorie: C/2, C/6, C/7. L’agevolazione “X” può essere presente soltanto se esiste una agevolazione "P" per quel soggetto. L’agevolazione “Y” non può essere presente se esiste una agevolazione "P" per quel soggetto. Il codice agevolazione H può essere selezionato solo nella sezione devoluzione dei quadri EC, EM e solo a favore di persone fisiche. Il codice agevolazione F può essere selezionato solo nella sezione devoluzione dei quadri EC, EM. Il codice agevolazione G può essere selezionato solo nella sezione devoluzione dei quadri EB, EC, EL, EM, EN. Il codice agevolazione N può essere selezionato solo nella sezione devoluzione dei quadri EB, EL. I codici agevolazione C, D, E, M, N, F, R, G non possono essere selezionati nella sezione devoluzione dei Quadri EP, EQ e ER. Per il quadro EN sono ammessi solo i codici agevolazione D, G, Q. Per il quadro EO sono ammessi solo i codici agevolazione D, Q. Per il quadro ER sono ammessi solo i codici agevolazione A (solo per tipo cespite AB, BI), L. Per ogni bene è possibile indicare soltanto una delle seguenti tipologie di agevolazione: ‘A’, ‘C’, ’D’, ‘E’, 'L', ‘M’, ‘N’, ‘P’, 'Z', 'X' e ‘Y’ ed in tal caso non possono essere presenti altre agevolazioni. Le agevolazioni ‘F’, ‘G’, ‘Q’ e ‘R’ possono invece essere presenti in contemporanea L' agevolazione N non può essere richiesta da soggetti con grado di parentela diverso da: '01' (Coniuge/Parte dell’unione civile), ‘02’ (Figlio/a), ‘03’ (Genitore), ‘04’ Nipote (figlio/a di figlio/a)), ‘5A’ (Nonno/a paterno/a), ‘5B’ (Nonno/a materno/a), ‘06’ (Pronipote (figlio/a di figlio/a di figlio/a)), ‘7A’ (Bisavo paterno), ‘7B’ (Bisavo materno), ‘08’ (Figlio/a del Pronipote), ‘9A’ (Trisavo paterno), ‘9B’ (Trisavo materno). L' agevolazione D non può essere richiesta da soggetti con grado di parentela diverso da: '01' (Coniuge/Parte dell’unione civile), ‘02’ (Figlio/a), ‘04’ Nipote (figlio/a di figlio/a)), ‘06’ (Pronipote (figlio/a di figlio/a di figlio/a)), ‘08’ (Figlio/a del Pronipote). L' agevolazione R non può essere richiesta da soggetti con grado di parentela diverso da: '01' (Coniuge/Parte dell’unione civile), ‘02’ (Figlio/a), ‘03’ (Genitore), ‘04’ Nipote (figlio/a di figlio/a)), ‘5A’ (Nonno/a paterno/a), ‘5B’ (Nonno/a materno/a), ‘06’ (Pronipote (figlio/a di figlio/a di figlio/a)), ‘7A’ (Bisavo paterno), ‘7B’ (Bisavo materno), ‘08’ (Figlio/a del Pronipote), ‘9A’ (Trisavo paterno), ‘9B’ (Trisavo materno), ‘10’ (Fratello/sorella germano), ‘11’ (Fratello/sorella unilaterale). L' agevolazione F non può essere richiesta da soggetti con grado di parentela diverso da: '01' (Coniuge/Parte dell’unione civile), ‘02’ (Figlio/a), ‘03’ (Genitore), ‘04’ Nipote (figlio/a di figlio/a)), ‘5A’ (Nonno/a paterno/a), ‘5B’ (Nonno/a materno/a), ‘06’ (Pronipote (figlio/a di figlio/a di figlio/a)), ‘7A’ (Bisavo paterno), ‘7B’ (Bisavo materno). L' agevolazione Q non può essere richiesta da soggetti con grado di parentela diverso da: '01' (Coniuge/Parte dell’unione civile), ‘02’ (Figlio/a), ‘03’ (Genitore), ‘04’ Nipote (figlio/a di figlio/a)), )), ‘5A’ (Nonno/a paterno/a), ‘5B’ (Nonno/a materno/a), ‘06’ (Pronipote (figlio/a di figlio/a di figlio/a ‘7A’ (Bisavo paterno), ‘7B’ (Bisavo materno), ‘10’ (Fratello/sorella germano), ‘11’ (Fratello/sorella unilaterale), ‘15’ (Nipote (figlio/a di fratello/sorella), ‘16’ (Zio/a (Fratello/sorella di genitore)). L' agevolazione ‘G’ non può essere richiesta da soggetti con grado di parentela diverso da 02, 03, 04, 5A, 5B, 06, 7A, 7B nè da soggetti con almeno 40 anni al momento dell’apertura della successione (data decesso) nè per terreni/fabbricati che non siano beni aziendali. Se codice carica del frontespizio = 5 (curatore dell’eredità giacente) o 6 (amministratore dell’eredità) non sono ammesse agevolazioni diverse da A,C,D,E,M,N,L. Non può essere presente in presenza di devoluzione a soggetti di tipo 5 (trust).
          - Riduzioni `[0..1]` : `suc:CodiciRiduzioni25comma1_Type` — Obbligatorio e deve assumere lo stesso valore in tutti i righi della devoluzione se è presente il campo Valore precedenti successioni. Non può essere presente in presenza di devoluzione a soggetti di tipo 5 (trust).
        - Continuazione `[0..1]` : `cm:DatoCB_Type` — se è barrata la casella, nel rigo successivo devono essere indicati gli ulteriori soggetti nella sezione devoluzione senza compilare la parte relativa ai dati identificativi del bene

## QuadroEC

- **QuadroEC** `[0..1]` — Non deve essere presente se 'Dichiarazione sostitutiva è uguale a '3' In presenza di codice ‘1’ nella casella ‘Dichiarazione sostitutiva’ dei Dati Generali, deve essere presente almeno un quadro tra EB e EC
  - **Modulo** `[1..n]`
    - **Fabbricati** `[1..2]` — Possono essere presenti righe duplicate (codice comune, sezione urbana, foglio, particella, subalterno) solo se hanno codice diritto diverso In presenza di uno stesso immobile (codice comune, sezione urbana, foglio, particella, subalterno) su più righi con codice diritto diverso, devono essere uguali anche provincia, comune amministrativo, codice comune amministrativo, zona censuaria, categoria, classe, consistenza e rendita catastale
      - **Luogo** `[0..1]` : `reg:Luogo_Type` — obbligatorio se non è presente il campo continuazione (devoluzione) nè il campo continuazione (graffati) del rigo precedente. Il campo indirizzo è obbligatorio se 'provincia' diverso da 'EE'
        - Provincia `[1..1]` : `reg:PENonTavolare_Type` — provincie italiane in vigore (con esclusione di quelle in vigore nel catasto tavolare) e “EE” che indica un paese estero.
        - _scelta `[1..1]` fra:_
          - **Italia** `[1..1]` : `reg:ItaliaType` — Obbligatorio se 'Provincia' diverso da 'EE''. Se 'provincia' = 'EE' non valorizzare.
            - ComuneAmministrativo `[1..1]` : `cm:DatoAN_Type` {'maxLength': '50'}
            - CodiceComune `[1..1]` : `cm:DatoAN_Type` — Congruente con il campo 'Provincia'.
            - Indirizzo `[0..1]` : `reg:TipologiaIndirizzo_Type`
            - CodiceComuneAmministrativo `[1..1]` : `cm:DatoAN_Type` — Congruente con il campo 'Comune amministrativo '
          - **Estero** `[1..1]` — Obbligatorio se 'Provincia' = 'EE''. Se 'provincia' diverso da 'EE' non valorizzare.
            - _(estensione di `sc:Residenza_Estera_Type`)_
            - CodiceStatoEstero `[1..1]` : `cm:DatoAN_Type` {'maxLength': '3', 'minLength': '3'}
            - StatoFederato `[0..1]` : `cm:DatoAN_Type` {'maxLength': '24'}
            - LocalitaEstero `[0..1]` : `cm:DatoAN_Type`
            - IndirizzoEstero `[1..1]` : `cm:DatoAN_Type`
            - StatoEstero `[1..1]` : `cm:DatoAN_Type` {'maxLength': '34'}
      - **DatiFabbricati** `[0..1]` : `reg:DatiFabbricati_Type` — Obbligatorio se 'Provincia' diverso da 'EE'. Se 'provincia' = 'EE' non valorizzare.
        - **DatiCatastali** `[1..1]` : `reg:DatiCatastali_Type`
          - Foglio `[1..1]` : `cm:DatoAN_Type` {'maxLength': '4'}
          - Particella `[1..1]` : `reg:Particella_Type` {'maxLength': '5'} — Riportare il numero di particella, indicato nel documento catastale. Nel caso di immobile graffato riportare solo la prima particella.
          - Subalterno `[0..1]` : `cm:DatoAN_Type` {'maxLength': '4'}
        - **DatiFabbricati** `[1..1]` : `reg:DatiCatastaliFabbricati_Type`
          - SezioneUrbana `[0..1]` : `cm:DatoAN_Type` {'maxLength': '3'}
          - ZonaCensuaria `[0..1]` : `cm:DatoAN_Type` {'maxLength': '3'}
          - CategoriaCatastale `[0..1]` : `reg:CodiciCategoriaCatastale_Type` — Obbligatorio se 'Provincia' diverso da 'EE'' Se 'provincia' = 'EE' non valorizzare. In presenza di agevolazione “P” o "Z" la categoria catastale deve essere “A” escluso A1, A8, A9 e A10 oppure F3. In presenza di agevolazione “X” o "Y" la categoria catastale deve essere C/2, C/6 o C/7. In presenza del campo diritto di abitazione con valore = 1 o 2 o 5 o 6 la categoria catastale deve essere “A” escluso A1, A8, A9 e A10 oppure F3. In presenza del campo diritto di abitazione con valore = 3 o 7 la categoria catastale deve essere C/2, C/6 o C/7
          - Classe `[0..1]` : `cm:DatoAN_Type` {'maxLength': '2'}
          - Consistenza `[0..1]` : `cm:DatoVP_Type` — Dato obbligatorio se il campo 'categoria' assume valori da 'A1' ad 'A11', da B1 a B8, da C1 a C7. Non valorizzare per tutti gli altri valori del campo 'Categoria'. (Il campo non va compilato per gli immobili censiti nelle categorie D, E o non classati)
          - RenditaCatastale `[0..1]` : `cm:DatoVP_Type` — Obbligatoria se categoria ha un valore diverso da F1, F2, F3, F4, F5, F6, F7. Non può essere compilata se categoria ha un valore uguale a F1, F2, F3, F4, F5, F6, F7 Obbligatoria se categoria catastale è uguale a D10 e valore = 0
          - DeterminazioneRendita `[0..1]` : `reg:DeterminazioneRendita_Type` — Obbligatorio se 'Rendita catastale' non valorizzato e provincia diversa da 'EE' e se categoria ha un valore diverso da F1, F2, F3, F4, F5, F6, F7. Se categoria ha valore F1, F2, F3, F4, F5, F6, F7 non può essere presente. Se 'provincia' = 'EE' non valorizzare.
      - **Possesso** `[0..1]` : `suc:Possesso_Type` — obbligatorio se non è presente il campo continuazione (devoluzione) nè il campo continuazione (graffati) del rigo precedente
        - PossessoNumeratore `[1..1]` : `cm:DatoVP_Type`
        - PossessoDenominatore `[1..1]` : `cm:DatoNP_Type` {'maxLength': '6'}
      - CodiceDiritto_P `[0..1]` : `suc:CodiciDirittoImmobili_Type` — obbligatorio se non è presente il campo continuazione (devoluzione) nè il campo continuazione (graffati) del rigo precedente.
      - BeneAziendale `[0..1]` : `cm:DatoCB_Type` — se barrata la casella "Bene aziendale", dovra' essere compilato il quadro EN. Obbligatorio se è presente nella sezione devoluzione almeno un rigo con agevolazione Q o G.
      - ImpostaVersataEstero `[0..1]` : `cm:DatoNP_Type` — Se presente deve essere presente il campo EG4
      - Valore `[0..1]` : `cm:DatoNP_Type` {'maxLength': '13'} — obbligatorio se non è presente il campo continuazione (devoluzione) nè il campo continuazione (graffati) del rigo precedente e se categoria catastale è diversa da D10
      - ValorePrecSucc `[0..1]` : `cm:DatoNP_Type` {'maxLength': '13'} — Non può essere presente in assenza di riduzioni art. 25 c. 1 nella sezione devoluzione. Campo obbligatorio in presenza di riduzioni art. 25 c. 1 nella sezione devoluzione. Non può essere superiore al campo valore.
      - DiscordanzaDatiIntestatario `[0..1]` : `cm:DatoCB_Type` — Se selezionato e' obbligatoria la presenza di un modulo del quadro EI.
      - PassaggiSenzaAttiLegali `[0..1]` : `cm:DatoCB_Type` — Se selezionato e' obbligatoria la presenza di un modulo del quadro EI.
      - DirittoAbitazione `[0..1]` : `suc:DirittoAbitazione_Type` — Può essere presente solo se è presente nel quadro EA un rigo con Grado di parentela = ‘01’ (Coniuge/Parte dell’unione civile). Può essere presente solo se codice diritto de cuius è = ‘1’ (piena proprietà) o '1S' (proprietà superficiaria). Non può essere presente in presenza di devoluzione per legge (e in assenza di devoluzione per testamento e se 'legge estera' del frontespizio = 0) se nel quadro EH è barrata la casella di separazione per colpa o la casella di scioglimento dell'unione civile. Non può essere presente in presenza di almeno un rigo di devoluzione a soggetti di tipo 5 (trust). Non può essere presente in presenza di bene aziendale. Può assumere valore 1 o 2 o 3 o 4 solo se non è presente nel quadro EA un rigo con grado di parentela = ‘01’ (Coniuge/Parte dell’unione civile) e casella rinuncia barrata Può assumere valore 5 o 6 o 7 o 8 solo se è presente nel quadro EA un rigo con tipo soggetto = ‘4’ (Coniuge/Parte dell’unione civile superstite rinunciatario). Può assumere valore 1 o 2 o 3 o 5 o 6 o 7 solo se 'Provincia' diverso da 'EE'' In presenza di valore 1 o 5 non possono essere presenti nella sezione devoluzione righi con agevolazioni diverse da P In presenza di valore 2 o 6 non possono essere presenti nella sezione devoluzione righi con agevolazioni diverse da Z In presenza di valore 3 o 7 non possono essere presenti nella sezione devoluzione righi con agevolazioni diverse da X
      - **Graffati** `[0..1]` : `suc:GraffatiType` — Se il numero degli immobili graffati supera quello dei campi disponibili, barrare la casella continuazione e riportare l’indicazione degli ulteriori immobili nella sezione ‘immobili graffati’ del rigo che segue senza compilare la parte relativa ai dati identificativi del bene. Se 'provincia' = 'EE' non valorizzare. Non può essere indicato più volte lo stesso immobile graffato (sezione - foglio - particella - subalterno) nell'ambito dello stesso immobile.
        - **ImmobiliGraffati** `[0..4]`
          - **DatiCatastali** `[1..1]`
            - _(estensione di `reg:DatiCatastali_Type`)_
            - Foglio `[1..1]` : `cm:DatoAN_Type` {'maxLength': '4'}
            - Particella `[1..1]` : `reg:Particella_Type` {'maxLength': '5'} — Riportare il numero di particella, indicato nel documento catastale. Nel caso di immobile graffato riportare solo la prima particella.
            - Subalterno `[0..1]` : `cm:DatoAN_Type` {'maxLength': '4'}
            - SezioneUrbana `[0..1]` : `cm:DatoAN_Type` {'maxLength': '3'} — Dato obbligatorio se e' presente il campo 'sezione urbana' nei dati generali dell'immobile.
        - ContinuazioneGraffati `[0..1]` : `cm:DatoCB_Type` — se è barrata la casella, nel rigo successivo devono essere indicati gli ulteriori immobili nella sezione graffati senza compilare la parte relativa ai dati identificativi del bene
      - **DevoluzioneEC** `[0..1]` : `suc:DevoluzioneImmobili_Type` — Se il numero dei soggetti a cui sono devoluti i singoli beni supera il numero dei campi disponibili, barrare la casella continuazione e riportare l’indicazione degli ulteriori soggetti nella sezione devoluzione del rigo che segue senza compilare la parte relativa ai dati identificativi del bene. In presenza del Quadro EA la sezione deve essere compilata.
        - **Devoluzione** `[0..3]` — la sezione non puo' essere presente in assenza di quadro EA
          - _(estensione di `suc:DevoluzioneSingolaImmobili_Type`)_
          - **IdentificazioneSoggetto** `[1..1]` : `suc:IdentificazioneRigo_Type` — Non può essere indicato un soggetto (rigo-modulo) non presente nel quadro EA. Non può essere indicato un soggetto (rigo-modulo) rinunciatario. In presenza di devoluzione per legge (e in assenza di devoluzione per testamento e se 'legge estera' del frontespizio = 0) non può essere indicato un soggetto (rigo-modulo) con grado di parentela = 01 (Coniuge/Parte dell’unione civile) se nel quadro EH è barrata la casella di separazione per colpa o la casella di scioglimento dell'unione civile. In presenza di devoluzione per legge (e in assenza di devoluzione per testamento e se 'legge estera' del frontespizio = 0), se nel Quadro EA i tipi soggetto sono tutti ‘1’ (erede) o tutti ‘3’ (chiamati) o '4' (Coniuge/Parte dell’unione civile superstite rinunciatario), nella sezione Devoluzione devono essere riportati i dati identificativi (Rigo n. e Mod. N.) dei soggetti indicati nel Quadro EA, in ordine progressivo; Nel caso di un soggetto che eredita diversi diritti sullo stesso bene (ad es. 1/3 nuda proprietà e 2/3 di usufrutto), ripetere l’indicazione del soggetto su tanti righi quanti sono i diritti a lui devoluti. Nella sezione Devoluzione, lo stesso beneficiario può essere presente su più righi solo se i codici diritto sono diversi;
            - Rigo `[1..1]` : `cm:DatoN1_Type`
            - Modulo `[1..1]` : `cm:DatoNP_Type` {'maxLength': '3'}
          - **Quota** `[1..1]` : `suc:Quota_Type` — In presenza di devoluzione per legge (e in assenza di devoluzione per testamento e se 'legge estera' del frontespizio = 0), se nel Quadro EA i tipi soggetto sono tutti ‘1’ (erede) o tutti ‘3’ (chiamati) o '4' (Coniuge/Parte dell’unione civile superstite rinunciatario), il campo quota deve essere compilato in base al grado di parentela, come riportato nell'allegato 5 al modello. Se il codice diritto presente nella sezione devoluzione coincide con il codice diritto del defunto e non sono presenti in devoluzione i tre diritti aggiuntivi (superficie, uso e abitazione), il campo valore quota è uguale al prodotto del valore del bene per la quota devoluzione.
            - **QuotaElementi** `[1..1]` : `suc:QuotaElementi_Type` — La somma delle quote di devoluzione/ripartizione deve essere uguale all'intero (1/1).
              - QuotaNumeratore `[1..1]` : `cm:DatoNP_Type`
              - QuotaDenominatore `[1..1]` : `cm:DatoNP_Type`
            - QuotaValore `[0..1]` : `cm:DatoVP_Type` — Obbligatorio per i fabbricati se categoria catastale è diversa da D10. Obbligatorio per i terreni se natura è diversa da R. Il valore della singola quota non può essere maggiore del campo 'Valore' del bene oggetto della devoluzione/ripartizione (per il quadro EO non può essere maggiore della somma dei campi 'Valore' e 'Valore esente'). La somma dei valori delle quote deve essere uguale al campo 'Valore' del bene oggetto della devoluzione/ripartizione (per il quadro EO deve essere uguale alla somma dei campi 'Valore' e 'Valore esente'); è accettabile uno scostamento massimo pari all’1% del valore del bene oggetto della devoluzione/ripartizione (per il quadro EO della somma dei campi 'Valore' e 'Valore esente'), e comunque, in valore assoluto, non superiore a 100 €
          - CodiceDiritto_Rip `[1..1]` : `suc:CodiciDiritto_Type` — In presenza di devoluzione per legge (e in assenza di devoluzione per testamento e se 'legge estera' del frontespizio = 0), se nel Quadro EA i tipi soggetto sono tutti ‘1’ (erede) o tutti ‘3’ (chiamati) o '4' (Coniuge/Parte dell’unione civile superstite rinunciatario), i codici diritto presenti nella sezione devoluzione devono coincidere con il codice diritto del defunto. Per i quadri EN, EO, EP, EQ, ER sono ammessi solo i codici 1, 2, 7, 8 In presenza di devoluzione per testamento o se 'legge estera' del frontespizio = 1 ed in assenza di "discordanza dati intestatario” e/o “passaggi senza atti legali", nei quadri EB, EC, EL e EM deve esserci coerenza tra il codice diritto del defunto e quelli indicati nella sezione devoluzione secondo la seguente tabella: diritti scomponibili (1, 1s, 1t): - se il de cuius trasferisce la proprietà (1), nella sezione devoluzione possono essere indicati: proprietà (1) e/o proprietà superficiaria (1s) + proprietà per l’area (1t) e/o nuda proprietà (2) + usufrutto (8) e/o diritto del concedente (4) + enfiteusi (5) e/o proprietà superficiaria (1s) + nuda proprietà per l’area (2t) + usufrutto su proprietà per l’area (8t) e/o nuda proprietà superficiaria (2s) + usufrutto su proprietà superficiaria (8s) + proprietà per l’area (1t) e/o nuda proprietà superficiaria (2s) + usufrutto su proprietà superficiaria (8s) + nuda proprietà per l’area (2t) + usufrutto su proprietà per l’area (8t); i diritti di uso (7), abitazione (3) e superficie (6) possono essere presenti in aggiunta a tutti i diritti sopra riportati o in qualsiasi loro combinazione. - se il de cuius trasferisce la proprietà superficiaria (1s), nella sezione devoluzione possono essere indicati: proprietà superficiaria (1s) e/o nuda proprietà superficiaria (2s) + usufrutto su proprietà superficiaria (8s); i diritti di uso su proprietà superficiaria (7s) e abitazione su proprietà superficiaria (3s) possono essere presenti in aggiunta a tutti i diritti sopra riportati o in qualsiasi loro combinazione. - se il de cuius trasferisce la proprietà per l’area (1t), nella sezione devoluzione possono essere indicati: proprietà per l’area (1t) e/o nuda proprietà per l’area (2t) + usufrutto su proprietà per l’area (8t). diritti non scomponibili (2, 2s, 2t, 4, 5, 6, 10): se il de cuius trasferisce uno di questi diritti, nella sezione devoluzione può essere indicato solo lo stesso diritto
          - Agevolazioni `[0..1]` : `suc:CodiciAgevolazioni_Type` — In presenza di bene aziendale il campo non deve essere presente oppure deve avere valore = D o Q o G. I codici agevolazione P, Z, X e Y possono essere selezionati solo nella sezione devoluzione dei quadri EC, EM e se 'Provincia' diverso da 'EE''. L’agevolazione “P” può essere presente per uno stesso soggetto più volte solo se relative allo stesso immobile (codice comune, sezione urbana, foglio, particella, subalterno) L’agevolazione “X” o "Y" può essere presente per uno stesso soggetto per un solo immobile per ciascuna delle categorie: C/2, C/6, C/7. L’agevolazione “X” può essere presente soltanto se esiste una agevolazione "P" per quel soggetto. L’agevolazione “Y” non può essere presente se esiste una agevolazione "P" per quel soggetto. Il codice agevolazione H può essere selezionato solo nella sezione devoluzione dei quadri EC, EM e solo a favore di persone fisiche. Il codice agevolazione F può essere selezionato solo nella sezione devoluzione dei quadri EC, EM. Il codice agevolazione G può essere selezionato solo nella sezione devoluzione dei quadri EB, EC, EL, EM, EN. Il codice agevolazione N può essere selezionato solo nella sezione devoluzione dei quadri EB, EL. I codici agevolazione C, D, E, M, N, F, R, G non possono essere selezionati nella sezione devoluzione dei Quadri EP, EQ e ER. Per il quadro EN sono ammessi solo i codici agevolazione D, G, Q. Per il quadro EO sono ammessi solo i codici agevolazione D, Q. Per il quadro ER sono ammessi solo i codici agevolazione A (solo per tipo cespite AB, BI), L. Per ogni bene è possibile indicare soltanto una delle seguenti tipologie di agevolazione: ‘A’, ‘C’, ’D’, ‘E’, 'L', ‘M’, ‘N’, ‘P’, 'Z', 'X' e ‘Y’ ed in tal caso non possono essere presenti altre agevolazioni. Le agevolazioni ‘F’, ‘G’, ‘Q’ e ‘R’ possono invece essere presenti in contemporanea L' agevolazione N non può essere richiesta da soggetti con grado di parentela diverso da: '01' (Coniuge/Parte dell’unione civile), ‘02’ (Figlio/a), ‘03’ (Genitore), ‘04’ Nipote (figlio/a di figlio/a)), ‘5A’ (Nonno/a paterno/a), ‘5B’ (Nonno/a materno/a), ‘06’ (Pronipote (figlio/a di figlio/a di figlio/a)), ‘7A’ (Bisavo paterno), ‘7B’ (Bisavo materno), ‘08’ (Figlio/a del Pronipote), ‘9A’ (Trisavo paterno), ‘9B’ (Trisavo materno). L' agevolazione D non può essere richiesta da soggetti con grado di parentela diverso da: '01' (Coniuge/Parte dell’unione civile), ‘02’ (Figlio/a), ‘04’ Nipote (figlio/a di figlio/a)), ‘06’ (Pronipote (figlio/a di figlio/a di figlio/a)), ‘08’ (Figlio/a del Pronipote). L' agevolazione R non può essere richiesta da soggetti con grado di parentela diverso da: '01' (Coniuge/Parte dell’unione civile), ‘02’ (Figlio/a), ‘03’ (Genitore), ‘04’ Nipote (figlio/a di figlio/a)), ‘5A’ (Nonno/a paterno/a), ‘5B’ (Nonno/a materno/a), ‘06’ (Pronipote (figlio/a di figlio/a di figlio/a)), ‘7A’ (Bisavo paterno), ‘7B’ (Bisavo materno), ‘08’ (Figlio/a del Pronipote), ‘9A’ (Trisavo paterno), ‘9B’ (Trisavo materno), ‘10’ (Fratello/sorella germano), ‘11’ (Fratello/sorella unilaterale). L' agevolazione F non può essere richiesta da soggetti con grado di parentela diverso da: '01' (Coniuge/Parte dell’unione civile), ‘02’ (Figlio/a), ‘03’ (Genitore), ‘04’ Nipote (figlio/a di figlio/a)), ‘5A’ (Nonno/a paterno/a), ‘5B’ (Nonno/a materno/a), ‘06’ (Pronipote (figlio/a di figlio/a di figlio/a)), ‘7A’ (Bisavo paterno), ‘7B’ (Bisavo materno). L' agevolazione Q non può essere richiesta da soggetti con grado di parentela diverso da: '01' (Coniuge/Parte dell’unione civile), ‘02’ (Figlio/a), ‘03’ (Genitore), ‘04’ Nipote (figlio/a di figlio/a)), )), ‘5A’ (Nonno/a paterno/a), ‘5B’ (Nonno/a materno/a), ‘06’ (Pronipote (figlio/a di figlio/a di figlio/a ‘7A’ (Bisavo paterno), ‘7B’ (Bisavo materno), ‘10’ (Fratello/sorella germano), ‘11’ (Fratello/sorella unilaterale), ‘15’ (Nipote (figlio/a di fratello/sorella), ‘16’ (Zio/a (Fratello/sorella di genitore)). L' agevolazione ‘G’ non può essere richiesta da soggetti con grado di parentela diverso da 02, 03, 04, 5A, 5B, 06, 7A, 7B nè da soggetti con almeno 40 anni al momento dell’apertura della successione (data decesso) nè per terreni/fabbricati che non siano beni aziendali. Se codice carica del frontespizio = 5 (curatore dell’eredità giacente) o 6 (amministratore dell’eredità) non sono ammesse agevolazioni diverse da A,C,D,E,M,N,L. Non può essere presente in presenza di devoluzione a soggetti di tipo 5 (trust).
          - Riduzioni `[0..1]` : `suc:CodiciRiduzioni25comma1_Type` — Obbligatorio e deve assumere lo stesso valore in tutti i righi della devoluzione se è presente il campo Valore precedenti successioni. Non può essere presente in presenza di devoluzione a soggetti di tipo 5 (trust).
        - Continuazione `[0..1]` : `cm:DatoCB_Type` — se è barrata la casella, nel rigo successivo devono essere indicati gli ulteriori soggetti nella sezione devoluzione senza compilare la parte relativa ai dati identificativi del bene

## QuadroED

- **QuadroED** `[0..1]` — Non deve essere presente se 'Dichiarazione sostitutiva è uguale a '3'
  - **Modulo** `[1..n]`
    - **Passivita** `[1..3]`
      - Tipo `[0..1]` : `suc:CodiciPassivita_Type` — obbligatorio se non è presente il campo continuazione del rigo precedente
      - Descrizione `[0..1]` : `cm:DatoAN_Type` {'maxLength': '250'} — obbligatorio se non è presente il campo continuazione del rigo precedente
      - EstremiDocumento `[0..1]` : `cm:DatoAN_Type` {'maxLength': '50'} — obbligatorio se non è presente il campo continuazione del rigo precedente
      - DataDocumento `[0..1]` : `cm:DatoDT_Type` — obbligatorio se non è presente il campo continuazione del rigo precedente
      - **Possesso** `[0..1]` : `suc:Possesso2_Type` — obbligatorio se non è presente il campo continuazione del rigo precedente
        - PossessoNumeratore `[0..1]` : `cm:DatoNP_Type` — Se campo 'Tipo passività' = '11' (Legato o altro onere che grava su una quota ereditaria o sul legato stesso) non valorizzare.
        - PossessoDenominatore `[0..1]` : `cm:DatoNP_Type` {'maxLength': '6'} — Se campo 'Tipo passività' = '11' (Legato o altro onere che grava su una quota ereditaria o sul legato stesso) non valorizzare.
        - Valore `[1..1]` : `cm:DatoNP_Type` {'maxLength': '13'} — In presenza di Tipo passività = 2 (Spese funerarie) l'importo non può essere maggiore di 1033.
      - **ProgressivoCespite** `[0..1]` — Se campo 'Tipo' = '3' (Mutui, contratti per l'acquisto di immobili), '4' (Debiti verso aziende o istituti di credito), '5' (Debiti inerenti l'esercizio di imprese), '7' (Debiti verso lo Stato, ecc) è obbligatorio. Altrimenti non valorizzare. Non può essere indicato un cespite (rigo-modulo) non presente nel quadro indicato.
        - Quadro `[1..1]` : `cm:DatoAN_Type` {'maxLength': '2'} valori ['EB', 'EC', 'EL', 'EM', 'EN', 'EO', 'EP', 'EQ', 'ER'] — Se campo 'Tipo' = '3' (Mutui, contratti per l'acquisto di immobili) i valori ammessi sono 'EB', 'EC', 'EL', 'EM'.
        - Rigo `[1..1]` : `cm:DatoNP_Type` {'maxLength': '3'}
        - Mod `[1..1]` : `cm:DatoNP_Type` {'maxLength': '3'}
      - **RipartizioneED** `[0..1]` : `suc:Ripartizione_Type` — Se il numero dei soggetti che hanno sostenuto le passività supera il numero dei campi disponibili, barrare la casella continuazione e riportare l’indicazione degli ulteriori soggetti nella sezione ripartizione del rigo che segue senza compilare la parte relativa ai dati identificativi del bene. In presenza del Quadro EA la sezione deve essere compilata.
        - **Ripartizione** `[0..3]` — la sezione e' obbligatoria in presenza di quadro EA
          - _(estensione di `suc:RipartizioneSingola_Type`)_
          - **IdentificazioneSoggetto** `[1..1]` : `suc:IdentificazioneRigo_Type` — Non può essere indicato un soggetto (rigo-modulo) non presente nel quadro EA. Non può essere indicato un soggetto (rigo-modulo) rinunciatario. Non può essere indicato un soggetto (rigo-modulo) con grado di parentela = 36 (Stato). In presenza di devoluzione per legge (e in assenza di devoluzione per testamento e se 'legge estera' del frontespizio = 0) non può essere indicato un soggetto (rigo-modulo) con grado di parentela = 01 (Coniuge/Parte dell’unione civile) se nel quadro EH è barrata la casella di separazione per colpa o la casella di scioglimento dell'unione civile. In presenza di devoluzione per legge (e in assenza di devoluzione per testamento e se 'legge estera' del frontespizio = 0), se nel Quadro EA i tipi soggetto sono tutti ‘1’ (erede) o tutti ‘3’ (chiamati) o '4' (Coniuge/Parte dell’unione civile superstite rinunciatario), ed il tipo passività è diverso da 1 (Spese mediche e chirurgiche), 2 (Spese funerarie), 11 (Legato o altro onere che grava su una quota ereditaria o sul legato stesso) e 12 (Altre passivita'), nella sezione Devoluzione devono essere riportati i dati identificativi (Rigo n. e Mod. N.) dei soggetti indicati nel Quadro EA, in ordine progressivo. Nella sezione Ripartizione, lo stesso beneficiario non può essere presente su più righi
            - Rigo `[1..1]` : `cm:DatoN1_Type`
            - Modulo `[1..1]` : `cm:DatoNP_Type` {'maxLength': '3'}
          - **Quota** `[1..1]` : `suc:Quota_Type` — In presenza di devoluzione per legge (e in assenza di devoluzione per testamento e se 'legge estera' del frontespizio = 0), se nel Quadro EA i tipi soggetto sono tutti ‘1’ (erede) o tutti ‘3’ (chiamati) o '4' (Coniuge/Parte dell’unione civile superstite rinunciatario) ed il tipo passività è diverso da 1, 2, 11 e 12, il campo quota deve essere compilato in base al grado di parentela, come riportato nell'allegato 5 al modello;
            - **QuotaElementi** `[1..1]` : `suc:QuotaElementi_Type` — La somma delle quote di devoluzione/ripartizione deve essere uguale all'intero (1/1).
              - QuotaNumeratore `[1..1]` : `cm:DatoNP_Type`
              - QuotaDenominatore `[1..1]` : `cm:DatoNP_Type`
            - QuotaValore `[0..1]` : `cm:DatoVP_Type` — Obbligatorio per i fabbricati se categoria catastale è diversa da D10. Obbligatorio per i terreni se natura è diversa da R. Il valore della singola quota non può essere maggiore del campo 'Valore' del bene oggetto della devoluzione/ripartizione (per il quadro EO non può essere maggiore della somma dei campi 'Valore' e 'Valore esente'). La somma dei valori delle quote deve essere uguale al campo 'Valore' del bene oggetto della devoluzione/ripartizione (per il quadro EO deve essere uguale alla somma dei campi 'Valore' e 'Valore esente'); è accettabile uno scostamento massimo pari all’1% del valore del bene oggetto della devoluzione/ripartizione (per il quadro EO della somma dei campi 'Valore' e 'Valore esente'), e comunque, in valore assoluto, non superiore a 100 €
        - Continuazione `[0..1]` : `cm:DatoCB_Type` — se è barrata la casella, nel rigo successivo devono essere indicati gli ulteriori soggetti nella sezione ripartizione senza compilare la parte relativa ai dati identificativi del bene

## QuadroEE

- **QuadroEE** `[0..1]` — Non deve essere presente se 'Dichiarazione sostitutiva è uguale a '3'
  - TotaleValoreImmobili `[0..1]` : `cm:DatoNP_Type` — Obbligatorio in presenza di almeno uno dei quadri EB, EC, EL, EM con almeno un rigo in cui non è stata barrata la casella ‘Bene aziendale’ e con campo valore diverso da zero Deve essere uguale alla somma del valore degli immobili inseriti nei quadri ‘EB’, ‘EL’, ‘EC’ ed ‘EM’ al netto di quello degli immobili per i quali è stata barrata la casella ‘Bene aziendale’ e quello di immobili per i quali nella sezione devoluzione risulta il campo 'Agevolazioni' = 'A'.
  - TotaleValoreAziende `[0..1]` : `cm:DatoNP_Type` — Obbligatorio in presenza del quadro EN. Deve essere uguale alla somma del valore delle aziende inserite nel quadro EN.
  - TotaleValoreTitoli `[0..1]` : `cm:DatoNP_Type` — Obbligatorio in presenza di almeno un rigo del quadro EO Deve essere uguale alla somma del valore e del valore esente dei beni inseriti nel quadro EO.
  - TotaleValoreAereiNavi `[0..1]` : `cm:DatoNP_Type` — Obbligatorio in presenza di almeno uno dei quadri EP, EQ Deve essere uguale alla somma del valore dei beni inseriti nei quadri EP ed EQ al netto di quello dei beni per i quali nella sezione devoluzione risulta il campo 'Agevolazioni' = 'A'.
  - TotaleValoreAltriBeni `[0..1]` : `cm:DatoNP_Type` — Obbligatorio in presenza del quadro ER con almeno un rigo con campo valore presente. Deve essere uguale alla somma del valore dei beni inseriti nel quadro ER al netto di quello dei beni per i quali nella sezione devoluzione risulta il campo 'Agevolazioni' = 'A'.
  - TotaleAttivo `[0..1]` : `cm:DatoNP_Type` — Deve essere uguale alla somma da EE1 a EE5.
  - TotalePassivo `[0..1]` : `cm:DatoNP_Type` — Obbligatorio in presenza del quadro ED. Deve essere uguale alla somma del valore delle passività riportate nel quadro ED.
  - TotaleValoreAsseEreditarioNetto `[0..1]` : `cm:DatoNU_Type` — Deve essere uguale alla differenza tra TotaleAttivo e TotalePassivo

## QuadroER

- **QuadroER** `[0..1]` — Non deve essere presente se 'Dichiarazione sostitutiva è uguale a '3'
  - **Modulo** `[0..n]`
    - **Rendite** `[1..4]`
      - TipoCespite `[0..1]` : `suc:TipoCespite_Type` — obbligatorio se non è presente il campo continuazione del rigo precedente. Il valore GD può essere presente solo in presenza di successione testamentaria.
      - Descrizione `[0..1]` : `cm:DatoAN_Type` {'maxLength': '250'} — obbligatorio se non è presente il campo continuazione del rigo precedente
      - **Possesso** `[0..1]` : `suc:Possesso_Type` — obbligatorio se non è presente il campo continuazione del rigo precedente e se tipo cespite diverso da GD
        - PossessoNumeratore `[1..1]` : `cm:DatoVP_Type`
        - PossessoDenominatore `[1..1]` : `cm:DatoNP_Type` {'maxLength': '6'}
      - CodiceDiritto_P `[0..1]` : `suc:CodiciDirittoNonImmobili` — obbligatorio se non è presente il campo continuazione del rigo precedente e se tipo cespite diverso da GD. Per i quadri EN, EO, ER sono ammessi solo i codici 1, 2
      - **BeniEsteri** `[0..1]` : `suc:BeniEsteri_Type`
        - BeneSitoEstero `[1..1]` : `cm:DatoCB_Type`
        - ImpostaVersataEstero `[0..1]` : `cm:DatoNP_Type` — Se presente deve essere presente il campo EG4
      - Valore `[0..1]` : `cm:DatoNP_Type` {'maxLength': '13'} — obbligatorio se non è presente il campo continuazione del rigo precedente e se tipo cespite diverso da CR
      - ValorePrecSucc `[0..1]` : `cm:DatoNP_Type` {'maxLength': '13'} — Non può essere presente in assenza di riduzioni art. 25 c. 1 nella sezione devoluzione. Campo obbligatorio in presenza di riduzioni art. 25 c. 1 nella sezione devoluzione. Non può essere superiore al campo valore.
      - **DevoluzioneER** `[0..1]` : `suc:DevoluzioneNonImmobili_Type` — Se il numero dei soggetti a cui sono devoluti i singoli beni supera il numero dei campi disponibili, barrare la casella continuazione e riportare l’indicazione degli ulteriori soggetti nella sezione devoluzione del rigo che segue senza compilare la parte relativa ai dati identificativi del bene. In presenza del Quadro EA la sezione deve essere compilata.
        - **Devoluzione** `[0..3]` — la sezione non puo' essere presente in assenza di quadro EA
          - _(estensione di `suc:DevoluzioneSingolaNonImmobili_Type`)_
          - **IdentificazioneSoggetto** `[1..1]` : `suc:IdentificazioneRigo_Type` — Non può essere indicato un soggetto (rigo-modulo) non presente nel quadro EA. Non può essere indicato un soggetto (rigo-modulo) rinunciatario. In presenza di devoluzione per legge (e in assenza di devoluzione per testamento e se 'legge estera' del frontespizio = 0) non può essere indicato un soggetto (rigo-modulo) con grado di parentela = 01 (Coniuge/Parte dell’unione civile) se nel quadro EH è barrata la casella di separazione per colpa o la casella di scioglimento dell'unione civile. In presenza di devoluzione per legge (e in assenza di devoluzione per testamento e se 'legge estera' del frontespizio = 0), se nel Quadro EA i tipi soggetto sono tutti ‘1’ (erede) o tutti ‘3’ (chiamati) o '4' (Coniuge/Parte dell’unione civile superstite rinunciatario), nella sezione Devoluzione devono essere riportati i dati identificativi (Rigo n. e Mod. N.) dei soggetti indicati nel Quadro EA, in ordine progressivo; Nel caso di un soggetto che eredita diversi diritti sullo stesso bene (ad es. 1/3 nuda proprietà e 2/3 di usufrutto), ripetere l’indicazione del soggetto su tanti righi quanti sono i diritti a lui devoluti. Nella sezione Devoluzione, lo stesso beneficiario può essere presente su più righi solo se i codici diritto sono diversi;
            - Rigo `[1..1]` : `cm:DatoN1_Type`
            - Modulo `[1..1]` : `cm:DatoNP_Type` {'maxLength': '3'}
          - **Quota** `[1..1]` : `suc:Quota_Type` — In presenza di devoluzione per legge (e in assenza di devoluzione per testamento e se 'legge estera' del frontespizio = 0), se nel Quadro EA i tipi soggetto sono tutti ‘1’ (erede) o tutti ‘3’ (chiamati) o '4' (Coniuge/Parte dell’unione civile superstite rinunciatario), il campo quota deve essere compilato in base al grado di parentela, come riportato nell'allegato 5 al modello. Se il codice diritto presente nella sezione devoluzione coincide con il codice diritto del defunto, il campo valore quota è uguale al prodotto del valore del bene (per il quadro EO della somma dei campi 'Valore' e 'Valore esente') per la quota devoluzione.
            - **QuotaElementi** `[1..1]` : `suc:QuotaElementi_Type` — La somma delle quote di devoluzione/ripartizione deve essere uguale all'intero (1/1).
              - QuotaNumeratore `[1..1]` : `cm:DatoNP_Type`
              - QuotaDenominatore `[1..1]` : `cm:DatoNP_Type`
            - QuotaValore `[0..1]` : `cm:DatoVP_Type` — Obbligatorio per i fabbricati se categoria catastale è diversa da D10. Obbligatorio per i terreni se natura è diversa da R. Il valore della singola quota non può essere maggiore del campo 'Valore' del bene oggetto della devoluzione/ripartizione (per il quadro EO non può essere maggiore della somma dei campi 'Valore' e 'Valore esente'). La somma dei valori delle quote deve essere uguale al campo 'Valore' del bene oggetto della devoluzione/ripartizione (per il quadro EO deve essere uguale alla somma dei campi 'Valore' e 'Valore esente'); è accettabile uno scostamento massimo pari all’1% del valore del bene oggetto della devoluzione/ripartizione (per il quadro EO della somma dei campi 'Valore' e 'Valore esente'), e comunque, in valore assoluto, non superiore a 100 €
          - CodiceDiritto_Rip `[0..1]` : `suc:CodiciDirittoNonImmobiliDevoluzione` — obbligatorio se il quadro è diverso da ER o se il quadro è ER e tipo cespite diverso da GD In presenza di devoluzione per legge (e in assenza di devoluzione per testamento e se 'legge estera' del frontespizio = 0), se nel Quadro EA i tipi soggetto sono tutti ‘1’ (erede) o tutti ‘3’ (chiamati) o '4' (Coniuge/Parte dell’unione civile superstite rinunciatario), i codici diritto presenti nella sezione devoluzione devono coincidere con il codice diritto del defunto. Per i quadri EN, EO, EP, EQ, ER sono ammessi solo i codici 1, 2, 7, 8 In presenza di devoluzione per testamento o se 'legge estera' del frontespizio = 1, nei quadri EN, EO, EP, EQ e ER, deve esserci coerenza tra il codice diritto del defunto e quelli indicati nella sezione devoluzione secondo la seguente tabella: - se il de cuius trasferisce la proprietà (1), nella sezione devoluzione possono essere indicati: proprietà (1) e/o nuda proprietà (2) + usufrutto (8); il diritto di uso (7) può essere presente in aggiunta a tutti i diritti sopra riportati o in qualsiasi loro combinazione. - se il de cuius trasferisce la nuda proprietà (2), nella sezione devoluzione può essere indicato solo lo stesso diritto
          - Agevolazioni `[0..1]` : `suc:CodiciAgevolazioni_Type` — In presenza di bene aziendale il campo non deve essere presente oppure deve avere valore = D o Q o G. I codici agevolazione P, Z, X e Y possono essere selezionati solo nella sezione devoluzione dei quadri EC, EM. L’agevolazione “P” può essere presente per uno stesso soggetto solo 1 volta. L’agevolazione “Z” può essere presente soltanto se esiste una agevolazione "P" per quel soggetto. L’agevolazione “X” o "Y" può essere presente per uno stesso soggetto una sola volta per ciascuna delle categorie: C/2, C/6, C/7. L’agevolazione “X” può essere presente soltanto se esiste una agevolazione "P" per quel soggetto. L’agevolazione “Y” non può essere presente se esiste una agevolazione "P" per quel soggetto. Il codice agevolazione H può essere selezionato solo nella sezione devoluzione dei quadri EC, EM e solo a favore di persone fisiche. Il codice agevolazione F può essere selezionato solo nella sezione devoluzione dei quadri EC, EM. Il codice agevolazione G può essere selezionato solo nella sezione devoluzione dei quadri EB, EC, EL, EM, EN. Il codice agevolazione N può essere selezionato solo nella sezione devoluzione dei quadri EB, EL. I codici agevolazione C, D, E, M, N, F, R, G non possono essere selezionati nella sezione devoluzione dei Quadri EP, EQ e ER. Per il quadro EN sono ammessi solo i codici agevolazione D, G, Q. Per il quadro EO sono ammessi solo i codici agevolazione D, Q. Per il quadro ER sono ammessi solo i codici agevolazione A (solo per tipo cespite AB, BI) e L. Per ogni bene è possibile indicare soltanto una delle seguenti tipologie di agevolazione: ‘A’, ‘C’, ’D’, ‘E’, 'L', ‘M’, ‘N’, ‘P’, 'X' e ‘Y’ ed in tal caso non possono essere presenti altre agevolazioni. Le agevolazioni ‘F’, ‘G’, ‘Q’ e ‘R’ possono invece essere presenti in contemporanea L' agevolazione N non può essere richiesta da soggetti con grado di parentela diverso da: '01' (Coniuge/Parte dell’unione civile), ‘02’ (Figlio/a), ‘03’ (Genitore), ‘04’ Nipote (figlio/a di figlio/a)), ‘5A’ (Nonno/a paterno/a), ‘5B’ (Nonno/a materno/a), ‘06’ (Pronipote (figlio/a di figlio/a di figlio/a)), ‘7A’ (Bisavo paterno), ‘7B’ (Bisavo materno), ‘08’ (Figlio/a del Pronipote), ‘9A’ (Trisavo paterno), ‘9B’ (Trisavo materno). L' agevolazione D non può essere richiesta da soggetti con grado di parentela diverso da: '01' (Coniuge/Parte dell’unione civile), ‘02’ (Figlio/a), ‘04’ Nipote (figlio/a di figlio/a)), ‘06’ (Pronipote (figlio/a di figlio/a di figlio/a)), ‘08’ (Figlio/a del Pronipote). L' agevolazione R non può essere richiesta da soggetti con grado di parentela diverso da: '01' (Coniuge/Parte dell’unione civile), ‘02’ (Figlio/a), ‘03’ (Genitore), ‘04’ Nipote (figlio/a di figlio/a)), ‘5A’ (Nonno/a paterno/a), ‘5B’ (Nonno/a materno/a), ‘06’ (Pronipote (figlio/a di figlio/a di figlio/a)), ‘7A’ (Bisavo paterno), ‘7B’ (Bisavo materno), ‘08’ (Figlio/a del Pronipote), ‘9A’ (Trisavo paterno), ‘9B’ (Trisavo materno), ‘10’ (Fratello/sorella germano), ‘11’ (Fratello/sorella unilaterale). L' agevolazione F non può essere richiesta da soggetti con grado di parentela diverso da: '01' (Coniuge/Parte dell’unione civile), ‘02’ (Figlio/a), ‘03’ (Genitore), ‘04’ Nipote (figlio/a di figlio/a)), ‘5A’ (Nonno/a paterno/a), ‘5B’ (Nonno/a materno/a), ‘06’ (Pronipote (figlio/a di figlio/a di figlio/a)), ‘7A’ (Bisavo paterno), ‘7B’ (Bisavo materno). L' agevolazione Q non può essere richiesta da soggetti con grado di parentela diverso da: '01' (Coniuge/Parte dell’unione civile), ‘02’ (Figlio/a), ‘03’ (Genitore), ‘04’ Nipote (figlio/a di figlio/a)), )), ‘5A’ (Nonno/a paterno/a), ‘5B’ (Nonno/a materno/a), ‘06’ (Pronipote (figlio/a di figlio/a di figlio/a ‘7A’ (Bisavo paterno), ‘7B’ (Bisavo materno), ‘10’ (Fratello/sorella germano), ‘11’ (Fratello/sorella unilaterale), ‘15’ (Nipote (figlio/a di fratello/sorella), ‘16’ (Zio/a (Fratello/sorella di genitore)). L' agevolazione ‘G’ non può essere richiesta da soggetti con grado di parentela diverso da 02, 03, 04, 5A, 5B, 06, 7A, 7B nè da soggetti con almeno 40 anni al momento dell’apertura della successione (data decesso) nè per terreni/fabbricati che non siano beni aziendali. Se codice carica del frontespizio = 5 (curatore dell’eredità giacente) o 6 (amministratore dell’eredità) non sono ammesse agevolazioni diverse da A,C,D,E,M,N,L Non può essere presente in presenza di devoluzione a soggetti di tipo 5 (trust).
          - Riduzioni `[0..1]` : `suc:CodiciRiduzioni25comma1_Type` — Obbligatorio e deve assumere lo stesso valore in tutti i righi della devoluzione se è presente il campo Valore precedenti successioni. Non può essere presente in presenza di devoluzione a soggetti di tipo 5 (trust).
        - Continuazione `[0..1]` : `cm:DatoCB_Type` — se è barrata la casella, nel rigo successivo devono essere indicati gli ulteriori soggetti nella sezione devoluzione senza compilare la parte relativa ai dati identificativi del bene

## QuadroEF

- **QuadroEF** `[0..1]` — Quadro obbligatorio: - In presenza del campo Copia conforme (sezione casi particolari del quadro dati generali) - In presenza del quadro EA e di almeno un rigo nei quadri EB, EC, EL, EM; - per le successioni aperte (data di decesso) a partire dal 01/01/2025. Non devono essere considerati i righi in cui 'provincia' = 'EE' né quelli con devoluzione a soggetti con grado parentela = 36 né quelli con devoluzione a soggetti con grado parentela = 37, 38, 39 con dichiarazione sostitutiva = 2 né quelli con agevolazione C, D, E o H con dichiarazione sostitutiva = 2. In assenza contemporanea del campo Copia conforme e dei quadri EA, EB, EC, EL, EM non va compilato per le successioni aperte (data di decesso) prima del 01/01/2025 se il presentatore ha codice carica diverso da 9. Il quadro può essere presente per le successioni aperte (data di decesso) prima del 01/01/2025 se il presentatore ha codice carica = 9. Non deve essere presente se 'Dichiarazione sostitutiva è uguale a '3'
  - **SezioneI_ImpostaIpotecaria** `[0..1]` — Obbligatorio in presenza del quadro EA e di almeno uno dei quadri relativi agli immobili con almeno un rigo con il campo 'Agevolazioni' = spazio o ‘A’ o B o L o R o F o G o M o N o P o Y o 'Q' o in cui è presente il campo diritto di abitazione con valore = 1 o 5 (quadri EB, EC, EL, EM) o in cui è presente almeno un soggetto di tipo 5 (trust) Non devono essere considerati i righi in cui 'provincia' = 'EE' o il campo 'Grado di parentela' uguale a '36', '37', '38' o '39' .
    - **ImpostaProporzionale** `[0..1]` — Obbligatorio in presenza di almeno uno dei quadri EB, EC, EL, EM con almeno un rigo con il campo 'Agevolazioni' = spazio o ‘A’ o ‘L', o 'R', o 'F' o N o 'Q'. Non devono essere considerati i righi in cui 'provincia' = 'EE' o il campo 'Grado di parentela' uguale a '36', '37', '38' o '39' . Non devono essere considerati i righi della sezione devoluzione dei quadri EC, EM in cui è valorizzato almeno un campo 'Agevolazioni' = 'P' o 'X' o 'Y' o 'Z' o in cui è presente il campo diritto di abitazione con valore = 1 o 2 o 3 o 5 o 6 o 7 (l’agevolazione prima casa si estende a tutti i beneficiari indicati nella sezione devoluzione in relazione a quel bene, anche se non hanno indicato P o X o Y o Z) . Non devono essere considerati i righi della sezione devoluzione dei quadri EB, EC, EL, EM in cui è valorizzato almeno un campo 'Agevolazioni' = 'M' (l’agevolazione si estende a tutti i beneficiari indicati nella sezione devoluzione in relazione a quel bene, anche se non hanno indicato M). Non devono essere considerati i righi della sezione devoluzione dei quadri EB, EC, EL, EM in cui è presente almeno un soggetto di tipo 5 (trust) (l’agevolazione si estende a tutti i beneficiari indicati nella sezione devoluzione in relazione a quel bene).
      - ImpostaProporzionale_Imponibile `[1..1]` : `cm:DatoNP_Type` — Deve essere uguale alla somma dei campi 'Valore quota' dei righi della sezione devoluzione dei quadri EB, EC, EL, EM con il campo 'Agevolazioni' = spazio o ‘A’ o ‘L', o 'R', o 'F' o N o 'Q'.
      - ImpostaProporzionale_Imposta `[0..1]` : `cm:DatoNP_Type` — Deve essere uguale al 2% del campo precedente. Il totale dell'imposta deve essere arrotondato all'unità di euro, per difetto se la frazione è inferiore a 50 centesimi e per eccesso se non inferiore. In presenza di soli terreni non edificabili su cui non è stata richiesta alcuna agevolazione ed in assenza di fabbricati, nel caso di valore inferiore a 168 euro deve essere impostata a 168 (se la data di decesso è superiore o uguale al 01/01/2014 si deve far riferimento a 200 invece di 168). In presenza di soli terreni non edificabili su cui non è stata richiesta alcuna agevolazione ed in assenza di fabbricati, se il totale dei valori fiscali (somma dei redditi dominicali rapportati alla quota del de cuius moltiplicato per 112.5) è inferiore alla somma delle imposte ipotecarie e catastali proporzionali, deve essere uguale a 2/3 del totale dei valori fiscali.
    - **AgevolazioneG** `[0..1]` — Obbligatorio in presenza di almeno uno dei quadri EB, EC,EL, EM con almeno un rigo con il campo 'Agevolazioni' = G. Non devono essere considerati i righi in cui 'provincia' = 'EE' o il campo 'Grado di parentela' uguale a '36', '37', '38' o '39'.
      - AgevolazioneG_Valore `[1..1]` : `cm:DatoNP_Type` — Deve essere uguale alla somma dei campi 'Valore quota' dei righi della sezione devoluzione con il campo 'Agevolazioni' = 'G' dei quadri EB, EC, EL, EM.
      - AgevolazioneG_Imposta `[0..1]` : `cm:DatoNP_Type` — Deve essere uguale a 168 (se la data di decesso è superiore o uguale al 01/01/2014 deve essere uguale a 200 invece di 168). Per gli immobili relativamente ai quali sono presenti anche quote assoggettate ad imposta ipotecaria proporzionale, se l'imposta proporzionale (per quei beni) è maggiore o uguale all’imposta fissa (168 o 200) l’imposta con agevolazione G viene azzerata in quanto l’imposta fissa viene assorbita dalla quota parte di proporzionale. Il campo va arrotondato all'unità di euro , per difetto se la frazione è inferiore a 50 centesimi e per eccesso se non inferiore.
    - **AgevolazioneM** `[0..1]` — Obbligatorio in presenza di almeno uno dei quadri EB, EC,EL, EM con almeno un rigo con il campo 'Agevolazioni' = M. Non devono essere considerati i righi in cui 'provincia' = 'EE' o il campo 'Grado di parentela' uguale a '36', '37', '38' o '39'.
      - AgevolazioneM_Valore `[1..1]` : `cm:DatoNP_Type` — Deve essere uguale alla somma dei campi 'Valore quota' dei righi della sezione devoluzione in cui è valorizzato almeno un campo 'Agevolazioni' = 'M' dei quadri EB, EC, EL, EM (quindi è il totale quote di tutti i beneficiari presenti in quella sezione devoluzione dove uno dei beneficiari ha indicato l’agevolazione). L’agevolazione si estende a tutti i beneficiari indicati nella sezione devoluzione in relazione a quel bene (anche se non hanno indicato M): per gli altri soggetti presenti nella sezione devoluzione non deve essere calcolata l’imposta proporzionale in quanto se anche non hanno indicato il codice M, l’agevolazione si estende anche a loro, per cui sconteranno anche loro una imposta fissa per la propria quota.
      - AgevolazioneM_Imposta `[0..1]` : `cm:DatoNP_Type` — Deve essere uguale a 168 (se la data di decesso è superiore o uguale al 01/01/2014 deve essere uguale a 200 invece di 168).
    - **TrustDisab** `[0..1]` — Obbligatorio in presenza di testamento, presentatore con codice carica 9 e almeno uno dei quadri EB, EC, EL, EM con almeno un rigo di devoluzione a soggetti di tipo 5 (trust). Non devono essere considerati i righi in cui 'provincia' = 'EE' o il campo 'Grado di parentela' uguale a '36', '37', '38' o '39'.
      - TrustDisab_Valore `[1..1]` : `cm:DatoNP_Type` — Deve essere uguale alla somma dei campi 'Valore quota' dei righi della sezione devoluzione dei quadri EB, EC, EL, EM in cui è presente almeno un soggetto di tipo 5 (trust) (quindi è il totale quote di tutti i beneficiari presenti in quella sezione devoluzione) se la data di apertura della successione non è antecedente al 1°gennaio 2017.
      - TrustDisab_Imposta `[0..1]` : `cm:DatoNP_Type` — Deve essere uguale a 200
    - **PrimaCasa** `[0..1]` — Obbligatorio in presenza di almeno uno dei quadri EC, EM con almeno un rigo con il campo 'Agevolazioni' = P o Y o Z (in assenza di P) o in cui è presente il campo diritto di abitazione con valore = 1 o 5 o 2 (in assenza di 1) o 6 (in assenza di 5). Non devono essere considerati i righi in cui 'provincia' = 'EE' o il campo 'Grado di parentela' uguale a '36', '37', '38' o '39' .
      - PrimaCasa_Numero `[1..1]` : `cm:DatoNP_Type` — Deve essere uguale al numero di immobili con il campo 'Agevolazioni' = 'P' o 'Y' o Z (in assenza di P) o in cui è presente il campo diritto di abitazione con valore = 1 o 5 o 2 (in assenza di 1) o 6 (in assenza di 5) dei quadri EC, EM (l’imposta fissa per l’agevolazione prima casa si calcola solo una volta indipendentemente dal numero di pertinenze accettabili e di immobili contigui). Non devono essere considerati i righi in cui 'provincia' = 'EE' o il campo 'Grado di parentela' uguale a '36', '37', '38' o '39' .
      - AgevolazionePX_Valore `[1..1]` : `cm:DatoNP_Type` — Deve essere uguale alla somma dei campi 'Valore quota' dei righi della sezione devoluzione in cui è valorizzato almeno un campo 'Agevolazioni' = 'P' o 'X' o 'Y' o 'Z' o in cui è presente il campo diritto di abitazione con valore = 1 o 2 o 3 o 5 o 6 o 7 dei quadri EC, EM (quindi è il totale quote di tutti i beneficiari presenti in quella sezione devoluzione dove uno dei beneficiari ha indicato l’agevolazione). L’agevolazione si estende a tutti i beneficiari indicati nella sezione devoluzione in relazione a quel bene (anche se non hanno indicato P o X o Y o Z): per gli altri soggetti presenti nella sezione devoluzione non deve essere calcolata l’imposta proporzionale in quanto se anche non hanno indicato il codice P o X o Y o Z, l’agevolazione si estende anche a loro, per cui sconteranno anche loro una imposta fissa per la propria quota.
      - PrimaCasa_Imposta `[1..1]` : `cm:DatoNP_Type` — deve essere uguale al prodotto dell’imposta ipotecaria fissa (euro 168,00) per il numero degli immobili indicati (se la data di decesso è superiore o uguale al 01/01/2014 si deve far riferimento a 200 invece di 168).
    - ImpostaIpotecariaDovuta `[0..1]` : `cm:DatoNP_Type` — Obbligatorio in presenza di almeno uno dei righi precedenti. Deve essere uguale alla somma dei righi EF1, EF2, EF3, EF3-bis e EF4 di colonna 3. Nel caso di valore inferiore a 168 euro ed in presenza del campo EF1 deve essere impostata a 168 (se la data di decesso è superiore o uguale al 01/01/2014 si deve far riferimento a 200 invece di 168). In presenza di soli terreni non edificabili su cui non è stata richiesta alcuna agevolazione ed in assenza di fabbricati tale adeguamento non va effettuato.
    - ImpostaIpotecariaVersata `[0..1]` : `cm:DatoNP_Type` — Puo' essere valorizzato solo se il campo 'Dichiarazione sostitutiva' del frontespizio = '1' o '2'. Se Il campo 'Prima dichiarazione del frontespizio = '1' non va valorizzato.
    - CreditoImposta `[0..1]` : `cm:DatoNP_Type`
    - ImpostaIpotecariaDaVersare `[0..1]` : `cm:DatoNP_Type` — Deve essere uguale a EF5 – EF6 – EF7, arrotondato all'unità di euro , per difetto se la frazione è inferiore a 50 centesimi e per eccesso se non inferiore. Se la differenza è negativa, deve essere uguale a 0. Nel caso di valore inferiore a 168 euro ed in assenza dei campi EF2 e EF3 e se il campo 'Dichiarazione sostitutiva' del frontespizio = '1' deve essere impostata a 168 (se la data di decesso è superiore o uguale al 01/01/2014 si deve far riferimento a 200 invece di 168).
  - **SezioneII_ImpostaCatastale** `[0..1]` — Obbligatorio in presenza del quadro EA e di almeno uno dei quadri relativi agli immobili con almeno un rigo con: - il campo 'Agevolazioni' = spazio o ‘A’ o B o L o R o F o N o 'Q' (quadri EB, EC, EL, EM) - oppure con il campo il campo Agevolazioni = P o Y o Z (in assenza di P) o in cui è presente il campo diritto di abitazione con valore = 1 o 5 o 2 (in assenza di 1) o 6 (in assenza di 5) (quadri EC, EM) - oppure in cui è presente almeno un soggetto di tipo 5 (trust). Non devono essere considerati i righi in cui 'provincia' = 'EE' o il campo 'Grado di parentela' uguale a '36', '37', '38' o '39'. Non devono essere considerati i righi del quadro EL in cui 'provincia' = ''TN' o 'BZ' o Codice comune = 'G831A' o 'E800' o 'L468' o 'G406'.
    - **ImpostaProporzionale** `[0..1]` — Obbligatorio in presenza di almeno uno dei quadri EB, EC, EL, EM con almeno un rigo con: - il campo 'Agevolazioni' = spazio o ‘A’ o ‘L', o 'R', o 'F' o 'N' o 'Q'. Non devono essere considerati i righi in cui 'provincia' = 'EE' o il campo 'Grado di parentela' uguale a '36', '37', '38' o '39' . Non devono essere considerati i righi del quadro EL in cui 'provincia' = ''TN' o 'BZ' o Codice comune = 'G831A' o 'E800' o 'L468' o 'G406'. Non devono essere considerati i righi della sezione devoluzione dei quadri EC, EM in cui è valorizzato almeno un campo 'Agevolazioni' = 'P' o 'X' o 'Y' o 'Z' o in cui è presente il campo diritto di abitazione con valore = 1 o 2 o 3 o 5 o 6 o 7 (l’agevolazione prima casa si estende a tutti i beneficiari indicati nella sezione devoluzione in relazione a quel bene, anche se non hanno indicato P o X o Y o Z). Non devono essere considerati i righi della sezione devoluzione dei quadri EB, EC, EL, EM in cui è valorizzato almeno un campo 'Agevolazioni' = 'M' (l’agevolazione si estende a tutti i beneficiari indicati nella sezione devoluzione in relazione a quel bene, anche se non hanno indicato M). Non devono essere considerati i righi della sezione devoluzione dei quadri EB, EC, EL, EM in cui è presente almeno un soggetto di tipo 5 (trust) (l’agevolazione si estende a tutti i beneficiari indicati nella sezione devoluzione in relazione a quel bene).
      - ImpostaProporzionale_Imponibile `[1..1]` : `cm:DatoNP_Type` — Deve essere uguale alla somma dei campi 'Valore quota' dei righi della sezione devoluzione dei quadri EB, EC, EL, EM: - con il campo 'Agevolazioni' = (spazio o ‘A’) ; - con il campo ‘Agevolazioni’ = ‘L', o 'R', o 'F' o 'N' o 'Q'.
      - ImpostaProporzionale_Imposta `[0..1]` : `cm:DatoNP_Type` — Deve essere uguale al campo precedente moltiplicato per l’aliquota prevista (al momento 1%), arrotondato all'unità di euro , per difetto se la frazione è inferiore a 50 centesimi e per eccesso se non inferiore. In presenza di soli terreni non edificabili su cui non è stata richiesta alcuna agevolazione ed in assenza di fabbricati, nel caso di valore inferiore a 168 euro deve essere impostata a 168 (se la data di decesso è superiore o uguale al 01/01/2014 si deve far riferimento a 200 invece di 168). In presenza di soli terreni non edificabili su cui non è stata richiesta alcuna agevolazione ed in assenza di fabbricati, se il totale dei valori fiscali (somma dei redditi dominicali rapportati alla quota del de cuius moltiplicato per 112.5) è inferiore alla somma delle imposte ipotecarie e catastali proporzionali, deve essere uguale a 1/3 del totale dei valori fiscali.
    - ImpostaCatastaleFissa `[0..1]` : `cm:DatoNP_Type` — Obbligatorio in presenza di almeno uno dei quadri EC, EM con almeno un rigo con il campo 'Agevolazioni' = P o Y o Z (in assenza di P) o in cui è presente il campo diritto di abitazione con valore = 1 o 5 o 2 (in assenza di 1) o 6 (in assenza di 5). Non devono essere considerati i righi in cui 'provincia' = 'EE' o il campo 'Grado di parentela' uguale a '36', '37', '38' o '39'. Deve essere uguale al valore della colonna 3 del rigo EF4.
    - **ImpostaCatastaleTrustDisab** `[0..1]` — Obbligatorio in presenza di testamento, presentatore con codice carica 9 e almeno uno dei quadri EB, EC, EL, EM con almeno un rigo di devoluzione a soggetti di tipo 5 (trust). Non devono essere considerati i righi in cui 'provincia' = 'EE' o il campo 'Grado di parentela' uguale a '36', '37', '38' o '39'.
      - ImpostaCatastaleTrustDisab_Valore `[1..1]` : `cm:DatoNP_Type` — Deve essere uguale al valore della colonna 2 del rigo EF3-bis.
      - ImpostaCatastaleTrustDisab_Imposta `[0..1]` : `cm:DatoNP_Type` — Deve essere uguale al valore della colonna 3 del rigo EF3-bis.
    - ImpostaCatastaleDovuta `[0..1]` : `cm:DatoNP_Type` — Deve essere uguale alla somma dei righi EF9, EF10 e EF10-bis di colonna 3. Nel caso di valore inferiore a 168 euro ed in presenza del campo EF9 deve essere impostata a 168 (se la data di decesso è superiore o uguale al 01/01/2014 si deve far riferimento a 200 invece di 168). In presenza di soli terreni non edificabili su cui non è stata richiesta alcuna agevolazione ed in assenza di fabbricati tale adeguamento non va effettuato.
    - ImpostaCatastaleVersata `[0..1]` : `cm:DatoNP_Type` — Puo' essere valorizzato solo se il campo 'Dichiarazione sostitutiva' del frontespizio = '1' o '2'. Se il campo 'Prima dichiarazione del frontespizio = '1' non va valorizzato.
    - CreditoImposta `[0..1]` : `cm:DatoNP_Type` — Può essere valorizzato solo se EF5 - EF6 - EF7 = 0. Non può essere maggiore della differenza tra EF11 e EF12
    - ImpostaCatastaleDaVersare `[0..1]` : `cm:DatoNP_Type` — Deve essere uguale alla differenza dei righi EF11 – EF12 – EF13, arrotondato all'unità di euro , per difetto se la frazione è inferiore a 50 centesimi e per eccesso se non inferiore. Se la differenza è negativa, deve essere uguale a 0. Nel caso di valore inferiore a 168 euro e se il campo 'Dichiarazione sostitutiva' del frontespizio = '1' deve essere impostata a 168 (se la data di decesso è superiore o uguale al 01/01/2014 si deve far riferimento a 200 invece di 168).
  - **SezioneIII_TassaIpotecaria** `[0..1]` — Obbligatorio in presenza di almeno uno dei quadri EB, EC con almeno un rigo con devoluzione a soggetti con grado parentela diverso da 36 e codice diritto diverso da 10 e agevolazione diversa da H.
    - Circoscrizioni_Numero `[1..1]` : `cm:DatoNP_Type` — Deve essere uguale al numero di circoscrizioni immobiliari, individuate in base al codice del comune, dei righi della sezione devoluzione dei quadri EB, EC con il campo 'Grado di parentela' diverso da '36' e codice diritto diverso da 10. In presenza di codice ‘1’ nella casella ‘Dichiarazione sostitutiva’ dei Dati Generali, deve essere minore o uguale (con un minimo di 1), al numero di circoscrizioni immobiliari, individuate in base al codice del comune, dei righi della sezione devoluzione dei quadri EB, EC con il campo 'Grado di parentela' diverso da '36' e codice diritto diverso da 10. In presenza di codice ‘2’ nella casella ‘Dichiarazione sostitutiva’ dei Dati Generali, deve essere uguale a 0. Non devono essere considerati i righi in cui 'provincia' = 'EE' e i beni in cui è presente l'agevolazione H. L’elenco delle conservatorie è presente sul sito internet dell’Agenzia delle Entrate
    - Circoscrizioni_Imposta `[1..1]` : `cm:DatoNP_Type` — deve essere uguale al prodotto di euro 120,00 per il numero delle circoscrizioni indicate. Nel caso in cui sia stata espressa la volonta' di non dar seguito alle volture catastali mediante la barratura della casella presente nel frontespizio nella sezione casi particolari, deve essere uguale al prodotto di euro 65,00 per il numero delle circoscrizioni indicate
  - **SezioneIV_ImpostaBollo** `[0..1]` — Obbligatorio in presenza di almeno uno dei quadri EB, EC con almeno un rigo con devoluzione a soggetti con grado parentela diverso da 36 e 37 e agevolazioni diverse da ‘C’, ‘M’ o ‘G’ o ‘E’ o 'H' e codice diritto diverso da 10 oppure in presenza del campo Copia conforme (sezione casi particolari del quadro dati generali)
    - ImpostaBollo_CopiaConforme `[0..1]` : `cm:DatoNP_Type` — deve essere uguale a 32,00 (in presenza del campo Copia conforme) . In presenza di testamento, presentatore con codice carica 9 e casella "persona con disabilità" barrata su tutti i righi del quadro EA se la data di apertura della successione non è antecedente al 1°gennaio 2017 deve essere uguale a zero. In presenza di testamento, presentatore con codice carica 9 e almeno uno dei quadri EB, EC, EL, EM con almeno un rigo di devoluzione a soggetti di tipo 5 (trust) con 'Grado di parentela' uguale a '36', '37', deve essere uguale a zero. In presenza di almeno uno dei quadri EB, EC, EL, EM con almeno un rigo di devoluzione a soggetti con 'Grado di parentela' uguale a '36' deve essere uguale a zero.
    - Circoscrizioni_Numero `[0..1]` : `cm:DatoNP_Type` — Deve essere uguale al numero di circoscrizioni immobiliari, individuate in base al codice del comune, dei righi della sezione devoluzione dei quadri EB, EC con il codice diritto diverso da 10 e il campo 'Grado di parentela' diverso da 36 e 37 e agevolazioni diverse da ‘C’, ‘M’ o ‘G’ o ‘E’. In presenza di codice ‘1’ nella casella ‘Dichiarazione sostitutiva’ dei Dati Generali, deve essere minore o uguale (con un minimo di 1), al numero di circoscrizioni immobiliari, individuate in base al codice del comune, dei righi della sezione devoluzione quadri EB, EC con il codice diritto diverso da 10 e il campo 'Grado di parentela' diverso da 36 e 37 e agevolazioni diverse da ‘C’, ‘M’ o ‘G’ o ‘E’. In presenza di codice ‘2’ nella casella ‘Dichiarazione sostitutiva’ dei Dati Generali, deve essere uguale a 0. Non devono essere considerati i righi in cui 'provincia' = 'EE' e i beni in cui è presente l'agevolazione H. L’elenco delle conservatorie è presente sul sito internet dell’Agenzia delle Entrate
    - Circoscrizioni_Imposta `[1..1]` : `cm:DatoNP_Type` — deve essere uguale al prodotto di euro 85,00 per il numero delle circoscrizioni indicate (anche nel caso in cui sia stata espressa la volonta' di non dar seguito alle volture catastali mediante la barratura della casella presente nel frontespizio nella sezione casi particolari) + 32,00 (in presenza del campo Copia conforme)
  - **SezioneV_TributiSpeciali** `[0..1]` — Obbligatorio in presenza del campo Copia conforme (sezione casi particolari del quadro dati generali)
    - **CopiaConforme** `[0..1]` — Obbligatorio in presenza di copia conforme Non può essere presente in assenza di copia conforme
      - CopiaConforme_Importo `[1..1]` : `cm:DatoVP_Type` — Deve essere uguale a 16 euro
  - **SezioneVBis_ImpostaSuccessione** `[0..1]` — La sezione è obbligatoria per le successioni aperte (data di decesso) a partire dal 01/01/2025. La sezione non può essere presente per le successioni aperte (data di decesso) prima del 01/01/2025 se il presentatore ha codice carica diverso da 9. La sezione può essere presente per le successioni aperte (data di decesso) prima del 01/01/2025 se il presentatore ha codice carica = 9 e può contenere solo il campo PagamentoAnticipatoTrust.
    - _scelta `[0..1]` fra:_
      - ImpostaNonDovuta `[1..1]` : `cm:DatoCB_Type` — Campo obbligatorio se il presentatore ha codice carica 9 e casella "persona con disabilità" barrata su tutti i righi del quadro EA.
      - **ImpostaCalcolata** `[1..1]` — Non può essere presente se il presentatore ha codice carica 9 e casella "persona con disabilità" barrata su tutti i righi del quadro EA.
        - Imposta `[1..1]` : `cm:DatoNP_Type`
        - ImpostaVersata `[0..1]` : `cm:DatoNP_Type` — Può essere valorizzato solo se il campo 'Dichiarazione sostitutiva' del frontespizio = '1' o '2'. Se Il campo 'Prima dichiarazione del frontespizio = '1' non va valorizzato. Non può essere presente se il presentatore ha codice carica = 9 ed in assenza del campo EF18ter–Pagamento anticipato Trust. Se presente deve essere minore o uguale del campo EF18bis-imposta.
        - CreditoImposta `[0..1]` : `cm:DatoNP_Type` — Non può essere presente se il presentatore ha codice carica = 9 ed in assenza del campo EF18ter–Pagamento anticipato Trust. Può essere valorizzato solo se EF11 – EF12 – EF13 = 0. Non può essere maggiore della differenza tra EF18bis-imposta e EF18bis-Imposta già versata.
        - ImpostaDaVersare `[0..1]` : `cm:DatoNP_Type` — Deve essere uguale a EF18bis-imposta - EF18bis-Imposta già versata - EF18bis- Credito d’imposta. Se il risultato è minore o uguale a 10 euro deve essere uguale a zero.
        - TempisticaPagamento `[0..1]` : `suc:TempisticaPagamento_Type` — Non può essere presente se il campo EF18bis-imposta da versare è uguale a zero. Campo obbligatorio se il presentatore ha codice carica diverso da 9. Campo obbligatorio se il presentatore ha codice carica = 9 e pagamento anticipato trust valorizzato. Non può essere presente se il presentatore ha codice carica = 9 e pagamento anticipato trust non valorizzato.
        - PagamentoRateale `[0..1]` : `cm:DatoNP_Type` — Non può essere presente se il presentatore ha codice carica = 9 e pagamento anticipato trust non valorizzato. Non può essere presente se la differenza tra il campo EF18bis-imposta da versare ed il campo acconto è inferiore a 1000 euro. Indicare il numero di rate trimestrali (compreso tra 1 e 12). Se la differenza tra il campo EF18bis-imposta da versare ed il campo acconto è pari o inferiore a 20.000 euro, il numero di rate deve essere compreso tra 1 e 8.
        - Acconto `[0..1]` : `cm:DatoNP_Type` — Campo obbligatorio in presenza del campo EF18ter-Pagamento rateale. Non può essere presente in assenza del campo EF18ter-Pagamento rateale. Non può essere inferiore al 20% del campo EF18bis-imposta da versare. Non può essere maggiore del campo EF18bis-imposta da versare.
    - PagamentoAnticipatoTrust `[0..1]` : `cm:DatoCB_Type` — Può essere presente solo se il presentatore ha codice carica = 9 e almeno un rigo del quadro EA con beneficiario finale presente oppure se il presentatore ha codice carica = 9 e almeno un rigo del quadro EA con grado di parentela = 35 senza beneficiario finale. Non può essere presente in caso contrario.
  - TotaleDaVersare `[0..1]` : `cm:DatoVP_Type` — Deve essere uguale alla somma dei righi EF8, EF14, EF15 col. 2, EF16 col. 3 e EF18 col. 2. Se il presentatore ha codice carica 9 ed in presenza del campo EF18ter–Pagamento anticipato Trust ed in presenza di Tempistica pagamento = 2 ed in assenza del campo EF18ter–Pagamento rateale bisogna aggiungere il campo EF18bis-imposta da versare. Se il presentatore ha codice carica 9 ed in presenza del campo EF18ter–Pagamento anticipato Trust ed in presenza del campo EF18ter–Pagamento rateale ed in presenza di Tempistica pagamento = 2 bisogna aggiungere il campo EF18ter-acconto. Se il presentatore ha codice carica 9 ed in presenza del campo EF18ter–Pagamento anticipato Trust ed in presenza di Tempistica pagamento = 1 non bisogna aggiungere né il campo EF18bis-imposta da versare né il campo EF18ter-acconto. Se il presentatore ha codice carica diverso da 9 ed in presenza del campo EF18bis-imposta da versare ed in presenza di Tempistica pagamento = 2 ed in assenza del campo EF18ter–Pagamento rateale bisogna aggiungere il campo EF18bis-imposta da versare. Se il presentatore ha codice carica diverso da 9 ed in presenza del campo EF18bis-imposta da versare ed in presenza del campo EF18ter–Pagamento rateale ed in presenza di Tempistica pagamento = 2 bisogna aggiungere il campo EF18ter-acconto. Se il presentatore ha codice carica diverso da 9 ed in presenza del campo EF18bis-imposta da versare ed in presenza di Tempistica pagamento = 1 non bisogna aggiungere né il campo EF18bis-imposta da versare né il campo EF18ter-acconto.
  - **SezioneVI_SanzioniInteressi** `[0..1]`
    - **ImpostaIpotecaria** `[0..1]` — Può essere presente solo se è presente il campo ImpostaIpotecariaDaVersare
      - ImpostaIpotecaria_Sanzioni `[0..1]` : `cm:DatoVP_Type`
      - ImpostaIpotecaria_Interessi `[0..1]` : `cm:DatoVP_Type`
    - **ImpostaCatastale** `[0..1]` — Può essere presente solo se è presente il campo ImpostaCatastaleDaVersare
      - ImpostaCatastale_Sanzioni `[0..1]` : `cm:DatoVP_Type`
      - ImpostaCatastale_Interessi `[0..1]` : `cm:DatoVP_Type`
    - **TassaIpotecaria** `[0..1]` — Può essere presente solo se è presente il campo Circoscrizioni_Imposta della Sezione III
      - TassaIpotecaria_Sanzioni `[0..1]` : `cm:DatoVP_Type`
      - TassaIpotecaria_Interessi `[0..1]` : `cm:DatoVP_Type`
    - **ImpostaBollo** `[0..1]` — Può essere presente solo se è presente il campo Circoscrizioni_Imposta della Sezione IV
      - ImpostaBollo_Sanzioni `[0..1]` : `cm:DatoVP_Type`
      - ImpostaBollo_Interessi `[0..1]` : `cm:DatoVP_Type`
    - **ImpostaSuccessione** `[0..1]` — Può essere presente solo se è presente il campo Imposta da versare della Sezione VBis ed in presenza di Tempistica pagamento = 2
      - ImpostaSuccessione_Sanzioni `[0..1]` : `cm:DatoVP_Type`
      - ImpostaSuccessione_Interessi `[0..1]` : `cm:DatoVP_Type`
    - **TotaleDaVersare** `[0..1]`
      - TotaleDaVersare_Sanzioni `[0..1]` : `cm:DatoVP_Type` — Deve essere uguale alla somma dei righi di col. 1 EF20, EF21, EF22, EF23, EF23bis.
      - TotaleDaVersare_Interessi `[0..1]` : `cm:DatoVP_Type` — Deve essere uguale alla somma dei righi di col. 2 EF20, EF21, EF22, EF23, EF23bis.

## QuadroEG

- **QuadroEG** `[0..1]` — Obbligatorio se 'Dichiarazione sostitutiva è uguale a '3' Obbligatorio in presenza del quadro EA
  - **DichSost** `[0..1]` — Obbligatorio se codice carica = 5 o 6 o 7.
    - DichSostNum `[1..1]` : `cm:DatoNP_Type`
    - **DichSostAll** `[1..n]` : `reg:FileAttachment_Type`
      - FileType `[1..1]` : `reg:FileType_Type`
      - FileName `[1..1]` : `cm:DatoAN_Type` {'maxLength': '100'}
      - FileDescription `[0..1]` : `cm:DatoAN_Type`
      - ImageData `[1..1]` : `xs:base64Binary`
  - **Testamento** `[0..1]` — Obbligatorio se 'Devoluzione per testamento' del frontespizio = '1'. Il campo non può essere presente se 'Devoluzione per testamento' del frontespizio = '0'.
    - TestamentoNum `[1..1]` : `cm:DatoNP_Type`
    - **TestamentoAll** `[1..n]` : `reg:FileAttachment_Type`
      - FileType `[1..1]` : `reg:FileType_Type`
      - FileName `[1..1]` : `cm:DatoAN_Type` {'maxLength': '100'}
      - FileDescription `[0..1]` : `cm:DatoAN_Type`
      - ImageData `[1..1]` : `xs:base64Binary`
  - **Inventario** `[0..1]` — Obbligatorio in presenza del primo campo del rigo EH10 Non può essere presente in assenza del primo campo del rigo EH11
    - InventarioNum `[1..1]` : `cm:DatoNP_Type`
    - **InventarioAll** `[1..n]` : `reg:FileAttachment_Type`
      - FileType `[1..1]` : `reg:FileType_Type`
      - FileName `[1..1]` : `cm:DatoAN_Type` {'maxLength': '100'}
      - FileDescription `[0..1]` : `cm:DatoAN_Type`
      - ImageData `[1..1]` : `xs:base64Binary`
  - **CertificazioneImpostaVersataEstero** `[0..1]` — Obbligatorio in presenza di imposta versata all'estero in almeno un quadro EB, EC, EO, EP, EQ, ER.
    - CertificazioneImpostaVersataEsteroNum `[1..1]` : `cm:DatoNP_Type`
    - **CertificazioneImpostaVersataEsteroAll** `[1..n]` : `reg:FileAttachment_Type`
      - FileType `[1..1]` : `reg:FileType_Type`
      - FileName `[1..1]` : `cm:DatoAN_Type` {'maxLength': '100'}
      - FileDescription `[0..1]` : `cm:DatoAN_Type`
      - ImageData `[1..1]` : `xs:base64Binary`
  - **DocumentiPassivita** `[0..1]` — Obbligatorio in presenza del quadro ED. Obbligatorio in presenza del terzo campo del rigo EH11 Non può essere presente in assenza del terzo campo del rigo EH11
    - DocumentiPassivitaNum `[1..1]` : `cm:DatoNP_Type`
    - **DocumentiPassivitaAll** `[1..n]` : `reg:FileAttachment_Type`
      - FileType `[1..1]` : `reg:FileType_Type`
      - FileName `[1..1]` : `cm:DatoAN_Type` {'maxLength': '100'}
      - FileDescription `[0..1]` : `cm:DatoAN_Type`
      - ImageData `[1..1]` : `xs:base64Binary`
  - **AlberoGenealogico** `[0..1]` — Obbligatorio in presenza del quadro EA
    - AlberoGenealogicoNum `[1..1]` : `cm:DatoNP_Type` — deve assumere valore = 1
    - **AlberoGenealogicoAll** `[1..n]` : `reg:FileAttachment_Type`
      - FileType `[1..1]` : `reg:FileType_Type`
      - FileName `[1..1]` : `cm:DatoAN_Type` {'maxLength': '100'}
      - FileDescription `[0..1]` : `cm:DatoAN_Type`
      - ImageData `[1..1]` : `xs:base64Binary`
  - **DocumentiIdentita** `[0..1]` — Obbligatorio in presenza del rigo EG1 o EG10 o EG11. Campo obbligatorio in presenza del rigo EG9 ad eccezione dei casi di presenza di Flag trasferimento prima (F2) nel quadro EH ed assenza di agevolazioni = P o X o Y o Z o di campo diritto di abitazione con valore = 1 o 2 o 3 o 5 o 6 o 7 in almeno uno dei quadri EC, EM per soggetti diversi dal dichiarante.
    - DocumentiIdentitaNum `[1..1]` : `cm:DatoNP_Type`
    - **DocumentiIdentitaAll** `[1..n]` : `reg:FileAttachment_Type`
      - FileType `[1..1]` : `reg:FileType_Type`
      - FileName `[1..1]` : `cm:DatoAN_Type` {'maxLength': '100'}
      - FileDescription `[0..1]` : `cm:DatoAN_Type`
      - ImageData `[1..1]` : `xs:base64Binary`
  - **Altro** `[0..1]` — Obbligatorio in presenza del secondo campo del rigo EH11 Obbligatorio in presenza del campo eventi eccezionali del frontespizio o di agevolazione H nella sezione devoluzione dei quadri EC, EM. Obbligatorio in presenza di testamento, presentatore con codice carica 9 e almeno uno dei quadri EB, EC, EL, EM con almeno un rigo di devoluzione a soggetti di tipo 5 (trust).
    - AltroNum `[1..1]` : `cm:DatoNP_Type`
    - **AltroAll** `[1..n]` : `reg:FileAttachment_Type`
      - FileType `[1..1]` : `reg:FileType_Type`
      - FileName `[1..1]` : `cm:DatoAN_Type` {'maxLength': '100'}
      - FileDescription `[0..1]` : `cm:DatoAN_Type`
      - ImageData `[1..1]` : `xs:base64Binary`
  - **PrimaCasa** `[0..1]` — Obbligatorio in presenza di agevolazioni = P o X o Y o Z o di campo diritto di abitazione con valore = 1 o 2 o 3 o 5 o 6 o 7 in almeno uno dei quadri EC, EM per soggetti diversi dal dichiarante. Obbligatorio in presenza di Flag trasferimento prima (F2) nel quadro EH. Obbligatorio in presenza di agevolazione Z ed in assenza di agevolazione P per il dichiarante Obbligatorio in presenza di agevolazione Y per il dichiarante Per dichiarante si intende: • il codice fiscale presente nella sezione “Riservato a chi presenta il modello” del frontespizio (primo campo) se tale soggetto è presente nel quadro EA • il codice fiscale del soggetto rappresentato eventualmente presente nella sezione “Riservato a chi presenta il modello” del frontespizio (ultimo campo) se il codice fiscale presente nella sezione “Riservato a chi presenta il modello” del frontespizio (primo campo) non è presente nel quadro EA oppure se presente è rinunciatario
    - PrimaCasaNum `[1..1]` : `cm:DatoNP_Type`
    - **PrimaCasaAll** `[1..n]` : `reg:FileAttachment_Type`
      - FileType `[1..1]` : `reg:FileType_Type`
      - FileName `[1..1]` : `cm:DatoAN_Type` {'maxLength': '100'}
      - FileDescription `[0..1]` : `cm:DatoAN_Type`
      - ImageData `[1..1]` : `xs:base64Binary`
  - **AgevolazioniImposteIpocatastali** `[0..1]` — Obbligatorio in presenza di agevolazioni = C o D o E in almeno uno dei quadri EB, EC, EL, EM, EN, EO, EP, EQ, ER per soggetti diversi dal dichiarante Per dichiarante si intende: • il codice fiscale presente nella sezione “Riservato a chi presenta il modello” del frontespizio (primo campo) se tale soggetto è presente nel quadro EA • il codice fiscale del soggetto rappresentato eventualmente presente nella sezione “Riservato a chi presenta il modello” del frontespizio (ultimo campo) se il codice fiscale presente nella sezione “Riservato a chi presenta il modello” del frontespizio (primo campo) non è presente nel quadro EA oppure se presente è rinunciatario
    - AgevolazioniImposteIpocatastaliNum `[1..1]` : `cm:DatoNP_Type`
    - **AgevolazioniImposteIpocatastaliAll** `[1..n]` : `reg:FileAttachment_Type`
      - FileType `[1..1]` : `reg:FileType_Type`
      - FileName `[1..1]` : `cm:DatoAN_Type` {'maxLength': '100'}
      - FileDescription `[0..1]` : `cm:DatoAN_Type`
      - ImageData `[1..1]` : `xs:base64Binary`
  - **RiduzioniImposteSuccessione** `[0..1]` — Obbligatorio in presenza di riduzioni = L o A o Q o 1 o 2 o 3 o 4 o 5 in almeno uno dei quadri EB, EC, EL, EM, EN, EO, EP, EQ, ER per soggetti diversi dal dichiarante Obbligatorio in presenza di agevolazioni = L o A in almeno uno dei quadri EB, EC, EL, EM, EN, EO, EP, EQ, ER per il dichiarante ed in assenza dei relativi campi del quadro EH Per dichiarante si intende: • il codice fiscale presente nella sezione “Riservato a chi presenta il modello” del frontespizio (primo campo) se tale soggetto è presente nel quadro EA • il codice fiscale del soggetto rappresentato eventualmente presente nella sezione “Riservato a chi presenta il modello” del frontespizio (ultimo campo) se il codice fiscale presente nella sezione “Riservato a chi presenta il modello” del frontespizio (primo campo) non è presente nel quadro EA oppure se presente è rinunciatario
    - RiduzioniImposteSuccessioneNum `[1..1]` : `cm:DatoNP_Type`
    - **RiduzioniImposteSuccessioneAll** `[1..n]` : `reg:FileAttachment_Type`
      - FileType `[1..1]` : `reg:FileType_Type`
      - FileName `[1..1]` : `cm:DatoAN_Type` {'maxLength': '100'}
      - FileDescription `[0..1]` : `cm:DatoAN_Type`
      - ImageData `[1..1]` : `xs:base64Binary`

## QuadroEH

- **QuadroEH** `[0..1]` — Non deve essere presente se 'Dichiarazione sostitutiva è uguale a '3' o se codice carica = 5 o 6 o 7. Obbligatorio se 'Dichiarazione sostitutiva è diversa da '3' e se codice carica è diverso da 5 o 6 o 7.
  - **PrimoModulo** `[1..1]`
    - **SezioneI_DichSost** `[1..1]`
      - **Presentatore** `[1..1]` — I dati devono essere uguali a quelli riportati sul frontespizio
        - _(estensione di `reg:Dati_Anagrafici_Type`)_
        - Cognome `[1..1]` : `reg:DatoAN2_Type` {'maxLength': '80'}
        - Nome `[1..1]` : `reg:DatoAN2_Type` {'maxLength': '80'}
        - Sesso `[1..1]` : `sc:Sesso_Type`
        - DataNascita `[1..1]` : `cm:DatoDT_Type`
        - ComuneNascita `[1..1]` : `cm:DatoAN_Type` {'maxLength': '50'}
        - ProvinciaNascita `[1..1]` : `cm:PN_Type`
        - CodiceFiscale `[1..1]` : `cm:DatoCF_Type`
        - CodiceCarica `[1..1]` : `reg:CodiciCarica_Type`
        - CodiceFiscaleRappresentato `[0..1]` : `cm:DatoCF_Type`
      - **DatiDefunto** `[1..1]`
        - **DatiAnagrafici** `[1..1]` — I dati devono essere uguali a quelli riportati sul frontespizio
          - _(estensione di `reg:Dati_Anagrafici_Type`)_
          - Cognome `[1..1]` : `reg:DatoAN2_Type` {'maxLength': '80'}
          - Nome `[1..1]` : `reg:DatoAN2_Type` {'maxLength': '80'}
          - Sesso `[1..1]` : `sc:Sesso_Type`
          - DataNascita `[1..1]` : `cm:DatoDT_Type`
          - ComuneNascita `[1..1]` : `cm:DatoAN_Type` {'maxLength': '50'}
          - ProvinciaNascita `[1..1]` : `cm:PN_Type`
        - _scelta `[1..1]` fra:_
          - **Decesso** `[1..1]`
            - FlagDeceduto `[1..1]` : `cm:DatoCB_Type`
            - DataDecesso `[1..1]` : `cm:DatoDT_Type` — deve essere uguale a quella riportata sul frontespizio
            - Comune `[1..1]` : `cm:DatoAN_Type` {'maxLength': '50'}
            - Provincia `[1..1]` : `cm:PN_Type`
          - **MortePresunta** `[1..1]` — Obbligatorio se codice carica del frontespizio = 8 (persona immessa nel possesso temporaneo dei beni dell’assente).
            - FlagAssenza `[1..1]` : `cm:DatoCB_Type`
            - Tribunale `[1..1]` : `cm:DatoAN_Type` {'maxLength': '50'}
            - DataDeposito `[1..1]` : `cm:DatoDT_Type` — deve essere successiva a quella del decesso presente nel frontespizio
            - Sentenza `[1..1]` : `cm:DatoAN_Type` {'maxLength': '50'}
      - **Dichiarante** `[0..1]` — Può essere presente solo in presenza di quadro EA
        - _scelta `[1..1]` fra:_
          - PresenzaDichiarante `[1..1]` : `cm:DatoCB_Type` — La casella deve essere barrata se il codice carica del frontespizio è uguale a 1 o 2 (erede, chiamato all’eredità, legatario). Non deve essere barrata se il codice carica del frontespizio è diverso da 1, 2 o 3 o 4 o 6 o 7 o 8.
          - FlagAssenzaDichiarante `[1..1]` : `cm:DatoCB_Type` — La casella non deve essere barrata se il codice carica del frontespizio è uguale a 1 o 2 (erede, chiamato all’eredità, legatario). Deve essere barrata se il codice carica del frontespizio è diverso da 1, 2 o 3 o 4 o 6 o 7 o 8.
      - **Eredi** `[0..3]` : `suc:Soggetto2_Type` — I dati relativi agli eredi devono essere uguali a quelli presenti nel Quadro EA relativamente ai soggetti con tipo soggetto = 1 o 2 o 3 o 4 (erede, legatario, chiamato, coniuge superstite rinunciatario)
        - CodiceFiscale `[1..1]` : `cm:DatoCF_Type`
        - GradoParentela `[1..1]` : `suc:GradoParentela_Type`
        - _scelta `[1..1]` fra:_
          - **DatiAnagrafici** `[1..1]` : `reg:Dati_Anagrafici_Type`
            - Cognome `[1..1]` : `reg:DatoAN2_Type` {'maxLength': '80'}
            - Nome `[1..1]` : `reg:DatoAN2_Type` {'maxLength': '80'}
            - Sesso `[1..1]` : `sc:Sesso_Type`
            - DataNascita `[1..1]` : `cm:DatoDT_Type`
            - ComuneNascita `[1..1]` : `cm:DatoAN_Type` {'maxLength': '50'}
            - ProvinciaNascita `[1..1]` : `cm:PN_Type`
          - Denominazione `[1..1]` : `reg:DatoAN2_Type` {'maxLength': '150'}
      - **Testamento** `[1..1]`
        - _scelta `[1..1]` fra:_
          - FlagAssenzaTestamento `[1..1]` : `cm:DatoCB_Type` — la casella non deve essere barrata se la casella Devoluzione Per Testamento del frontespizio è barrata. Deve essere barrata se la casella Devoluzione Per Testamento del frontespizio non è barrata
          - **PresenzaTestamento** `[1..1]`
            - FlagTestamento `[1..1]` : `cm:DatoCB_Type` — la casella non deve essere barrata se la casella Devoluzione Per Testamento del frontespizio non è barrata. Deve essere barrata se la casella Devoluzione Per Testamento del frontespizio è barrata
            - **RegistrazioneTestamento** `[0..2]` : `reg:EstremiRegistrazione_Type` — Deve essere presente se non è barrata la casella Testamento estero del frontespizio. I dati relativi al primo rigo (EH4) devono essere uguali a quelli presenti nel frontespizio. Non possono essere presenti righe duplicate
              - UfficioDiRegistrazione `[1..1]` : `reg:UfficioDiRegistrazione_Type`
              - Serie `[1..1]` : `reg:Serie_Type` {'maxLength': '2', 'minLength': '1'}
              - NumeroRegistrazione `[1..1]` : `cm:DatoNU_Type` {'maxLength': '6'}
              - SottonumeroRegistrazione `[0..1]` : `cm:DatoNU_Type` {'maxLength': '3'}
              - DataRegistrazione `[1..1]` : `cm:DatoDT_Type`
      - **ReintegroDiritti** `[0..1]`
        - FlagReintegro `[1..1]` : `cm:DatoCB_Type`
        - **RegistrazioneReintegroDiritti** `[1..1]` : `reg:EstremiRegistrazione_Type` — Non possono essere presenti righe duplicate
          - UfficioDiRegistrazione `[1..1]` : `reg:UfficioDiRegistrazione_Type`
          - Serie `[1..1]` : `reg:Serie_Type` {'maxLength': '2', 'minLength': '1'}
          - NumeroRegistrazione `[1..1]` : `cm:DatoNU_Type` {'maxLength': '6'}
          - SottonumeroRegistrazione `[0..1]` : `cm:DatoNU_Type` {'maxLength': '3'}
          - DataRegistrazione `[1..1]` : `cm:DatoDT_Type`
      - **Interdetti** `[1..1]`
        - _scelta `[1..1]` fra:_
          - FlagAssenzaInterdetti `[1..1]` : `cm:DatoCB_Type` — la casella deve essere barrata se in nessun rigo del quadro EA è presente il campo Persone con disabilità uguale a 1. Non deve essere barrata se in almeno un rigo del quadro EA è presente il campo Persone con disabilità uguale a 1
          - **PresenzaInterdetti** `[1..1]`
            - FlagInterdetti `[1..1]` : `cm:DatoCB_Type` — la casella deve essere barrata se in almeno un rigo del quadro EA è presente il campo Persone con disabilità uguale a 1. Non deve essere barrata se in nessun rigo del quadro EA è presente il campo Persone con disabilità uguale a 1
            - **IdentificazioneSoggetto** `[1..1]` : `suc:IdentificazioneRigo_Type` — Non può essere indicato un soggetto (rigo-modulo) non presente nel quadro EA o che non abbia il campo Persone con disabilità uguale a 1 Non possono essere presenti righe duplicate
              - Rigo `[1..1]` : `cm:DatoN1_Type`
              - Modulo `[1..1]` : `cm:DatoNP_Type` {'maxLength': '3'}
            - Certificatore `[1..1]` : `cm:DatoAN_Type` {'maxLength': '35'}
      - **Rinuncia** `[1..1]`
        - _scelta `[1..1]` fra:_
          - FlagAssenzaRinuncia `[1..1]` : `cm:DatoCB_Type` — Obbligatorio in assenza del campo rinuncia su tutti i righi del quadro EA
          - **PresenzaRinuncia** `[1..1]` — Obbligatorio in presenza di un tipo soggetto = 4 (Coniuge/Parte dell’unione civile superstite rinunciatario) nel quadro EA. Obbligatorio in presenza del campo rinuncia su almeno un rigo del quadro EA
            - FlagRinuncia `[1..1]` : `cm:DatoCB_Type`
            - **IdentificazioneSoggetto** `[1..1]` : `suc:IdentificazioneRigo_Type` — Non può essere indicato un soggetto (rigo-modulo) non presente nel quadro EA e che non abbia impostato il campo rinuncia. Non possono essere presenti righe duplicate Non può essere indicato il dichiarante
              - Rigo `[1..1]` : `cm:DatoN1_Type`
              - Modulo `[1..1]` : `cm:DatoNP_Type` {'maxLength': '3'}
            - **RegistrazioneRinuncia** `[1..1]` : `reg:EstremiRegistrazione_Type`
              - UfficioDiRegistrazione `[1..1]` : `reg:UfficioDiRegistrazione_Type`
              - Serie `[1..1]` : `reg:Serie_Type` {'maxLength': '2', 'minLength': '1'}
              - NumeroRegistrazione `[1..1]` : `cm:DatoNU_Type` {'maxLength': '6'}
              - SottonumeroRegistrazione `[0..1]` : `cm:DatoNU_Type` {'maxLength': '3'}
              - DataRegistrazione `[1..1]` : `cm:DatoDT_Type`
      - **Separazione** `[0..1]`
        - _scelta `[1..1]` fra:_
          - FlagAssenzaSeparazione `[1..1]` : `cm:DatoCB_Type`
          - FlagSeparazione `[1..1]` : `cm:DatoCB_Type` — la casella non deve essere barrata se lo stato civile del defunto presente nel frontespizio è diverso da 5 (separato/a).. In presenza del campo e di devoluzione per legge (e in assenza di devoluzione per testamento e se 'legge estera' del frontespizio = 0) non può essere indicato nella sezione devoluzione dei vari quadri un soggetto con grado di parentela = 01 (Coniuge/Parte dell’unione civile)
      - FlagNoScioglimentoUnioneCivile `[0..1]` : `cm:DatoCB_Type` — Obbligatorio se lo stato civile del frontespizio = '7' (Parte dell’unione civile) Non può essere presente in caso contrario
      - **Aziende** `[0..1]` — Non deve essere presente in assenza del quadro EN.
        - FlagAzienda `[1..1]` : `cm:DatoCB_Type` — la casella non deve essere barrata in assenza del quadro EN
        - DataDeposito `[1..1]` : `cm:DatoDT_Type`
        - CameraCommercio `[1..1]` : `cm:DatoAN_Type` {'maxLength': '35'}
      - FlagProspetto `[0..1]` : `cm:DatoCB_Type` — Campo obbligatorio in presenza del rigo EG3 La casella non deve essere barrata in assenza del rigo EG3
      - FlagInventari `[0..1]` : `cm:DatoCB_Type` — La casella non deve essere barrata in assenza del rigo EG8
      - FlagPassivita `[0..1]` : `cm:DatoCB_Type` — Campo obbligatorio in presenza del rigo EG5 La casella non deve essere barrata in assenza del rigo EG5
      - **Navi** `[0..1]` — Non deve essere presente in assenza del quadro EQ. Deve essere presente in presenza del quadro EQ. I dati relativi alle navi devono essere uguali a quelli presenti nel Quadro EQ
        - FlagNavi `[1..1]` : `cm:DatoCB_Type` — la casella non deve essere barrata in assenza del quadro EQ. Deve essere barrata in presenza del quadro EQ
        - SiglaUfficioIscrizione `[1..1]` : `cm:DatoAN_Type` {'maxLength': '6'}
        - AnnoIscrizione `[1..1]` : `cm:DatoDA_Type`
        - NumeroIscrizione `[1..1]` : `cm:DatoNP_Type` {'maxLength': '10'}
      - **Aeromobili** `[0..1]` — Non deve essere presente in assenza del quadro EP. Deve essere presente in presenza del quadro EP. I dati relativi agli Aeromobili devono essere uguali a quelli presenti nel Quadro EP
        - FlagAeromobili `[1..1]` : `cm:DatoCB_Type` — la casella non deve essere barrata in assenza del quadro EP. Deve essere barrata in presenza del quadro EP
        - Nazionalita `[1..1]` : `cm:DatoAN_Type` {'maxLength': '20'}
        - AnnoImmatricolazione `[1..1]` : `cm:DatoDA_Type`
        - NumeroImmatricolazione `[1..1]` : `cm:DatoNP_Type` {'maxLength': '10'}
      - FirmaDichiarante `[1..1]` : `cm:DatoCB_Type`
    - **SezioneII_AgevPrimaCasa** `[0..1]` — La presente sezione può essere compilata solo in presenza di agevolazioni = P o X o Y o Z o di diritto di abitazione con valore = 1 o 2 o 3 o 5 o 6 o 7 in almeno uno dei quadri EC, EM per il dichiarante Per dichiarante si intende: • il codice fiscale presente nella sezione “Riservato a chi presenta il modello” del frontespizio (primo campo) se tale soggetto è presente nel quadro EA • il codice fiscale del soggetto rappresentato eventualmente presente nella sezione “Riservato a chi presenta il modello” del frontespizio (ultimo campo) se il codice fiscale presente nella sezione “Riservato a chi presenta il modello” del frontespizio (primo campo) non è presente nel quadro EA oppure se presente è rinunciatario
      - **ImmobilePrincipale** `[0..1]` — I dati devono corrispondere a quelli presenti nel quadro EC o EM con codice agevolazione P in corrispondenza del dichiarante o con il campo diritto di abitazione con valore = 1 o 5 se il dichiarante ha Grado di parentela = ‘01’ (Coniuge/Parte dell’unione civile).
        - **Luogo** `[1..1]`
          - Provincia `[1..1]` : `cm:PE_Type`
          - Comune `[1..1]` : `cm:DatoAN_Type` {'maxLength': '50'}
          - CodiceComune `[1..1]` : `cm:DatoAN_Type` {'maxLength': '5'}
          - Indirizzo `[0..1]` : `cm:DatoAN_Type` {'maxLength': '80'}
        - SezioneUrbana `[0..1]` : `cm:DatoAN_Type` {'maxLength': '3'}
        - **DatiCatastali** `[1..1]` : `reg:DatiCatastali_Type`
          - Foglio `[1..1]` : `cm:DatoAN_Type` {'maxLength': '4'}
          - Particella `[1..1]` : `reg:Particella_Type` {'maxLength': '5'} — Riportare il numero di particella, indicato nel documento catastale. Nel caso di immobile graffato riportare solo la prima particella.
          - Subalterno `[0..1]` : `cm:DatoAN_Type` {'maxLength': '4'}
      - **ImmobileContiguo** `[0..1]` — I dati devono corrispondere a quelli presenti nel quadro EC o EM con codice agevolazione Z in corrispondenza del dichiarante o con il campo diritto di abitazione con valore = 2 o 6 se il dichiarante ha Grado di parentela = ‘01’ (Coniuge/Parte dell’unione civile).
        - **Luogo** `[1..1]`
          - Provincia `[1..1]` : `cm:PE_Type`
          - Comune `[1..1]` : `cm:DatoAN_Type` {'maxLength': '50'}
          - CodiceComune `[1..1]` : `cm:DatoAN_Type` {'maxLength': '5'}
          - Indirizzo `[0..1]` : `cm:DatoAN_Type` {'maxLength': '80'}
        - SezioneUrbana `[0..1]` : `cm:DatoAN_Type` {'maxLength': '3'}
        - **DatiCatastali** `[1..1]` : `reg:DatiCatastali_Type`
          - Foglio `[1..1]` : `cm:DatoAN_Type` {'maxLength': '4'}
          - Particella `[1..1]` : `reg:Particella_Type` {'maxLength': '5'} — Riportare il numero di particella, indicato nel documento catastale. Nel caso di immobile graffato riportare solo la prima particella.
          - Subalterno `[0..1]` : `cm:DatoAN_Type` {'maxLength': '4'}
      - **Pertinenza** `[0..3]` — I dati relativi alle pertinenze devono corrispondere a quelli presenti nel Quadro EC o EM con codice agevolazione X o Y in corrispondenza del dichiarante o con il campo diritto di abitazione con valore = 3 o 7 se il dichiarante ha Grado di parentela = ‘01’ (Coniuge/Parte dell’unione civile). La seconda pertinenza può essere presente solo in presenza della pertinenza n. 1. La terza pertinenza può essere presente solo in presenza della pertinenza n. 2.
        - **Luogo** `[1..1]`
          - Provincia `[1..1]` : `cm:PE_Type`
          - Comune `[1..1]` : `cm:DatoAN_Type` {'maxLength': '50'}
          - CodiceComune `[1..1]` : `cm:DatoAN_Type` {'maxLength': '5'}
          - Indirizzo `[0..1]` : `cm:DatoAN_Type` {'maxLength': '80'}
        - SezioneUrbana `[0..1]` : `cm:DatoAN_Type` {'maxLength': '3'}
        - **DatiCatastali** `[1..1]` : `reg:DatiCatastali_Type`
          - Foglio `[1..1]` : `cm:DatoAN_Type` {'maxLength': '4'}
          - Particella `[1..1]` : `reg:Particella_Type` {'maxLength': '5'} — Riportare il numero di particella, indicato nel documento catastale. Nel caso di immobile graffato riportare solo la prima particella.
          - Subalterno `[0..1]` : `cm:DatoAN_Type` {'maxLength': '4'}
      - **Opzioni** `[1..1]`
        - _scelta `[1..1]` fra:_
          - FlagComuneResidenza `[0..1]` : `cm:DatoCB_Type`
          - FlagComuneAttivita `[0..1]` : `cm:DatoCB_Type`
          - FlagCambioResidenza `[0..1]` : `cm:DatoCB_Type`
          - FlagTrasferitoEstero `[0..1]` : `cm:DatoCB_Type`
          - FlagForzeArmate `[0..1]` : `cm:DatoCB_Type`
      - FlagTrasferimentoPrima `[0..1]` : `cm:DatoCB_Type` — Campo obbligatorio in presenza del campo FlagTrasferitoEstero per le successioni aperte a partire dal 14/06/2023. Non deve essere presente in presenza del campo FlagTrasferitoEstero per le successioni che si sono aperte prima del 14/06/2023. Non deve essere presente in assenza del campo FlagTrasferitoEstero.
      - FlagSedeLavoro `[0..1]` : `cm:DatoCB_Type` — Non deve essere presente in presenza del campo FlagTrasferitoEstero per le successioni aperte a partire dal 14/06/2023. Campo obbligatorio in presenza del campo FlagTrasferitoEstero per le successioni che si sono aperte prima del 14/06/2023. Non deve essere presente in assenza del campo FlagTrasferitoEstero.
      - FlagResidenteEstero2 `[0..1]` : `cm:DatoCB_Type` — Campo obbligatorio in presenza del campo FlagTrasferitoEstero per le successioni che si sono aperte prima del 14/06/2023. Non deve essere presente in assenza del campo FlagTrasferitoEstero.
      - FlagNessunaAltraCasaComune `[0..1]` : `cm:DatoCB_Type` — Obbligatorio ad eccezione del caso di presenza di agevolazione Z ed in assenza di agevolazione P per il dichiarante oppure in presenza di agevolazione Y per il dichiarante.
      - **AltraCasa** `[0..1]` — Obbligatorio ad eccezione del caso di presenza di agevolazione Z ed in assenza di agevolazione P per il dichiarante.
        - _scelta `[1..1]` fra:_
          - FlagNessunaAltraCasa `[0..1]` : `cm:DatoCB_Type`
          - FlagVenditaAltraCasa `[0..1]` : `cm:DatoCB_Type`
      - FlagContigui `[0..1]` : `cm:DatoCB_Type` — obbligatorio in presenza di almeno uno dei quadri EC, EM con almeno un rigo con il campo 'Agevolazioni' = Z.
      - FirmaDichiarante `[1..1]` : `cm:DatoCB_Type`
    - **SezioneIII_CreditoImposta** `[0..1]` — Non deve essere presente in assenza del campo EF7
      - TipologiaImposta `[1..1]` : `suc:TipoImposta_Type`
      - Imposta `[1..1]` : `cm:DatoNP_Type`
      - **RegistrazioneAcquisto** `[1..1]` : `reg:EstremiRegistrazione_Type`
        - UfficioDiRegistrazione `[1..1]` : `reg:UfficioDiRegistrazione_Type`
        - Serie `[1..1]` : `reg:Serie_Type` {'maxLength': '2', 'minLength': '1'}
        - NumeroRegistrazione `[1..1]` : `cm:DatoNU_Type` {'maxLength': '6'}
        - SottonumeroRegistrazione `[0..1]` : `cm:DatoNU_Type` {'maxLength': '3'}
        - DataRegistrazione `[1..1]` : `cm:DatoDT_Type`
      - **RegistrazioneVendita** `[0..1]` : `reg:EstremiRegistrazione_Type` — la data di vendita non può essere anteriore a quella di acquisto
        - UfficioDiRegistrazione `[1..1]` : `reg:UfficioDiRegistrazione_Type`
        - Serie `[1..1]` : `reg:Serie_Type` {'maxLength': '2', 'minLength': '1'}
        - NumeroRegistrazione `[1..1]` : `cm:DatoNU_Type` {'maxLength': '6'}
        - SottonumeroRegistrazione `[0..1]` : `cm:DatoNU_Type` {'maxLength': '3'}
        - DataRegistrazione `[1..1]` : `cm:DatoDT_Type`
      - FirmaDichiarante `[1..1]` : `cm:DatoCB_Type`
    - **SezioneIV_AltreAgevRiduz** `[0..1]` — Per dichiarante si intende: • il codice fiscale presente nella sezione “Riservato a chi presenta il modello” del frontespizio (primo campo) se tale soggetto è presente nel quadro EA • il codice fiscale del soggetto rappresentato eventualmente presente nella sezione “Riservato a chi presenta il modello” del frontespizio (ultimo campo) se il codice fiscale presente nella sezione “Riservato a chi presenta il modello” del frontespizio (primo campo) non è presente nel quadro EA oppure se presente è rinunciatario
      - **EsenzioneImpostaSuccessione** `[0..1]` — La presente sezione può essere compilata solo in presenza di agevolazioni = L o A in almeno uno dei quadri EB, EC, EL, EM, EP, EQ, ER per il dichiarante
        - **AgevolazTipoA** `[0..1]` — Deve essere presente almeno una delle agevolazioni (A o L)
          - FlagA `[1..1]` : `cm:DatoCB_Type`
          - NumProtocollo `[1..1]` : `cm:DatoAN_Type`
          - Data `[1..1]` : `cm:DatoDT_Type`
        - **AgevolazTipoL** `[0..1]` — Deve essere presente almeno una delle agevolazioni (A o L)
          - FlagL `[1..1]` : `cm:DatoCB_Type`
          - NumProtocollo `[1..1]` : `cm:DatoAN_Type`
          - Data `[1..1]` : `cm:DatoDT_Type`
        - FirmaDichiarante `[1..1]` : `cm:DatoCB_Type`
      - **Agevolazioni** `[0..1]` — La presente sezione può essere compilata solo in presenza di agevolazioni = C o D o E o Q in almeno uno dei quadri EB, EC, EL, EM, EN, EO, EP, EQ, ER per il dichiarante
        - FlagC `[0..1]` : `cm:DatoCB_Type`
        - FlagD `[0..1]` : `cm:DatoCB_Type`
        - FlagE `[0..1]` : `cm:DatoCB_Type`
        - FlagQ `[0..1]` : `cm:DatoCB_Type`
        - FirmaDichiarante `[1..1]` : `cm:DatoCB_Type`
      - **Riduzioni** `[0..1]` — La presente sezione può essere compilata solo in presenza di riduzioni = 1 o 2 o 3 o 4 o 5 in almeno uno dei quadri EB, EC, EL, EM, EN, EO, EP, EQ, ER per il dichiarante
        - UfficioTerritoriale `[0..1]` : `reg:UfficioDiRegistrazione_Type` — obbligatorio in presenza degli estremi della dichiarazione precedente Non deve essere presente in caso contrario
        - **EstremiDichiarazionePrecedente** `[0..1]`
          - Anno `[1..1]` : `cm:DatoDA_Type`
          - Volume `[1..1]` : `cm:DatoNP_Type` {'maxLength': '5'}
          - Numero `[1..1]` : `cm:DatoNP_Type` {'maxLength': '6'}
        - **EstremiDonazionePrecedente** `[0..1]`
          - UfficioDiRegistrazione `[1..1]` : `reg:UfficioDiRegistrazione_Type`
          - Serie `[1..1]` : `reg:Serie_Type` {'maxLength': '2', 'minLength': '1'}
          - NumeroRegistrazione `[1..1]` : `cm:DatoNU_Type` {'maxLength': '6'}
          - SottonumeroRegistrazione `[0..1]` : `cm:DatoNU_Type` {'maxLength': '3'}
        - FirmaDichiarante `[1..1]` : `cm:DatoCB_Type`
  - **Modulo** `[0..n]`
    - **SezioneI_DichSost** `[0..1]`
      - **Eredi** `[0..3]` : `suc:Soggetto2_Type` — Può essere presente solo se nel modulo precedente sono presenti tre righi relativi agli eredi (EH1, EH2, EH3). I dati relativi agli eredi devono essere uguali a quelli presenti nel Quadro EA
        - CodiceFiscale `[1..1]` : `cm:DatoCF_Type`
        - GradoParentela `[1..1]` : `suc:GradoParentela_Type`
        - _scelta `[1..1]` fra:_
          - **DatiAnagrafici** `[1..1]` : `reg:Dati_Anagrafici_Type`
            - Cognome `[1..1]` : `reg:DatoAN2_Type` {'maxLength': '80'}
            - Nome `[1..1]` : `reg:DatoAN2_Type` {'maxLength': '80'}
            - Sesso `[1..1]` : `sc:Sesso_Type`
            - DataNascita `[1..1]` : `cm:DatoDT_Type`
            - ComuneNascita `[1..1]` : `cm:DatoAN_Type` {'maxLength': '50'}
            - ProvinciaNascita `[1..1]` : `cm:PN_Type`
          - Denominazione `[1..1]` : `reg:DatoAN2_Type` {'maxLength': '150'}
      - **RegistrazioneTestamento** `[0..2]` : `reg:EstremiRegistrazione_Type` — Può essere presente solo se nel modulo precedente sono presenti due righi relativi ai testamenti (EH4, EH5). Non possono essere presenti righe duplicate
        - UfficioDiRegistrazione `[1..1]` : `reg:UfficioDiRegistrazione_Type`
        - Serie `[1..1]` : `reg:Serie_Type` {'maxLength': '2', 'minLength': '1'}
        - NumeroRegistrazione `[1..1]` : `cm:DatoNU_Type` {'maxLength': '6'}
        - SottonumeroRegistrazione `[0..1]` : `cm:DatoNU_Type` {'maxLength': '3'}
        - DataRegistrazione `[1..1]` : `cm:DatoDT_Type`
      - **ReintegroDiritti** `[0..1]` : `reg:EstremiRegistrazione_Type` — Può essere presente solo se nel modulo precedente è presente il rigo relativo al reintegro dei diritti (EH6). Non possono essere presenti righe duplicate
        - UfficioDiRegistrazione `[1..1]` : `reg:UfficioDiRegistrazione_Type`
        - Serie `[1..1]` : `reg:Serie_Type` {'maxLength': '2', 'minLength': '1'}
        - NumeroRegistrazione `[1..1]` : `cm:DatoNU_Type` {'maxLength': '6'}
        - SottonumeroRegistrazione `[0..1]` : `cm:DatoNU_Type` {'maxLength': '3'}
        - DataRegistrazione `[1..1]` : `cm:DatoDT_Type`
      - **PresenzaInterdetti** `[0..1]` — Può essere presente solo se nel modulo precedente è presente il rigo relativo ad incapaci/interdetti (EH7)
        - **IdentificazioneSoggetto** `[1..1]` : `suc:IdentificazioneRigo_Type` — Non può essere indicato un soggetto (rigo-modulo) non presente nel quadro EA o che non abbia il campo Persone con disabilità uguale a 1 Non possono essere presenti righe duplicate
          - Rigo `[1..1]` : `cm:DatoN1_Type`
          - Modulo `[1..1]` : `cm:DatoNP_Type` {'maxLength': '3'}
        - Certificatore `[1..1]` : `cm:DatoAN_Type` {'maxLength': '35'}
      - **PresenzaRinuncia** `[0..1]` — Può essere presente solo se nel modulo precedente è presente il rigo relativo alla rinuncia (EH8)
        - **IdentificazioneSoggetto** `[1..1]` : `suc:IdentificazioneRigo_Type` — Non può essere indicato un soggetto (rigo-modulo) non presente nel quadro EA Non possono essere presenti righe duplicate
          - Rigo `[1..1]` : `cm:DatoN1_Type`
          - Modulo `[1..1]` : `cm:DatoNP_Type` {'maxLength': '3'}
        - **RegistrazioneRinuncia** `[1..1]` : `reg:EstremiRegistrazione_Type`
          - UfficioDiRegistrazione `[1..1]` : `reg:UfficioDiRegistrazione_Type`
          - Serie `[1..1]` : `reg:Serie_Type` {'maxLength': '2', 'minLength': '1'}
          - NumeroRegistrazione `[1..1]` : `cm:DatoNU_Type` {'maxLength': '6'}
          - SottonumeroRegistrazione `[0..1]` : `cm:DatoNU_Type` {'maxLength': '3'}
          - DataRegistrazione `[1..1]` : `cm:DatoDT_Type`
      - **Aziende** `[0..1]` — Può essere presente solo se nel modulo precedente è presente il rigo relativo alle aziende (EH9)
        - DataDeposito `[1..1]` : `cm:DatoDT_Type`
        - CameraCommercio `[1..1]` : `cm:DatoAN_Type` {'maxLength': '35'}
      - **Navi** `[0..1]` — Può essere presente solo se nel modulo precedente è presente il rigo relativo alle navi (EH11). I dati relativi alle navi devono essere uguali a quelli presenti nel Quadro EQ
        - SiglaUfficioIscrizione `[1..1]` : `cm:DatoAN_Type` {'maxLength': '6'}
        - AnnoIscrizione `[1..1]` : `cm:DatoDA_Type`
        - NumeroIscrizione `[1..1]` : `cm:DatoNP_Type` {'maxLength': '10'}
      - **Aeromobili** `[0..1]` — Può essere presente solo se nel modulo precedente è presente il rigo relativo alle aereomobili (EH12). I dati relativi alle navi devono essere uguali a quelli presenti nel Quadro EP
        - Nazionalita `[1..1]` : `cm:DatoAN_Type` {'maxLength': '20'}
        - AnnoImmatricolazione `[1..1]` : `cm:DatoDA_Type`
        - NumeroImmatricolazione `[1..1]` : `cm:DatoNP_Type` {'maxLength': '10'}
    - **SezioneII_AgevPrimaCasa** `[0..1]` — La presente sezione può essere compilata solo in presenza di agevolazioni = Z o di diritto di abitazione con valore = 2 o 6 in almeno uno dei quadri EC, EM per il dichiarante Per dichiarante si intende: • il codice fiscale presente nella sezione “Riservato a chi presenta il modello” del frontespizio (primo campo) se tale soggetto è presente nel quadro EA • il codice fiscale del soggetto rappresentato eventualmente presente nella sezione “Riservato a chi presenta il modello” del frontespizio (ultimo campo) se il codice fiscale presente nella sezione “Riservato a chi presenta il modello” del frontespizio (primo campo) non è presente nel quadro EA Per i moduli successivi al primo può essere presente solo se nel modulo precedente è presente un rigo relativo agli immobili contigui
      - **ImmobileContiguo** `[0..1]` — I dati devono corrispondere a quelli presenti nel quadro EC o EM con codice agevolazione Z in corrispondenza del dichiarante o con il campo diritto di abitazione con valore = 2 o 6 se il dichiarante ha Grado di parentela = ‘01’ (Coniuge/Parte dell’unione civile).
        - **Luogo** `[1..1]`
          - Provincia `[1..1]` : `cm:PE_Type`
          - Comune `[1..1]` : `cm:DatoAN_Type` {'maxLength': '50'}
          - CodiceComune `[1..1]` : `cm:DatoAN_Type` {'maxLength': '4'}
          - Indirizzo `[0..1]` : `cm:DatoAN_Type` {'maxLength': '80'}
        - SezioneUrbana `[0..1]` : `cm:DatoAN_Type` {'maxLength': '3'}
        - **DatiCatastali** `[1..1]` : `reg:DatiCatastali_Type`
          - Foglio `[1..1]` : `cm:DatoAN_Type` {'maxLength': '4'}
          - Particella `[1..1]` : `reg:Particella_Type` {'maxLength': '5'} — Riportare il numero di particella, indicato nel documento catastale. Nel caso di immobile graffato riportare solo la prima particella.
          - Subalterno `[0..1]` : `cm:DatoAN_Type` {'maxLength': '4'}
    - **SezioneIII_CreditoImposta** `[0..1]` — Non deve essere presente in assenza del campo EF7 in presenza di tipologia di imposta = 1 o 2 devono essere presenti almeno 2 righi di acquisti con tipologia di imposta = 1 o 2
      - TipologiaImposta `[0..1]` : `suc:TipoImposta_Type` — campo obbligatorio
      - Imposta `[0..1]` : `cm:DatoNP_Type` — campo obbligatorio
      - **RegistrazioneAcquisto** `[1..1]` : `reg:EstremiRegistrazione_Type`
        - UfficioDiRegistrazione `[1..1]` : `reg:UfficioDiRegistrazione_Type`
        - Serie `[1..1]` : `reg:Serie_Type` {'maxLength': '2', 'minLength': '1'}
        - NumeroRegistrazione `[1..1]` : `cm:DatoNU_Type` {'maxLength': '6'}
        - SottonumeroRegistrazione `[0..1]` : `cm:DatoNU_Type` {'maxLength': '3'}
        - DataRegistrazione `[1..1]` : `cm:DatoDT_Type`
      - **RegistrazioneVendita** `[0..1]` : `reg:EstremiRegistrazione_Type` — la data di vendita non può essere anteriore a quella di acquisto
        - UfficioDiRegistrazione `[1..1]` : `reg:UfficioDiRegistrazione_Type`
        - Serie `[1..1]` : `reg:Serie_Type` {'maxLength': '2', 'minLength': '1'}
        - NumeroRegistrazione `[1..1]` : `cm:DatoNU_Type` {'maxLength': '6'}
        - SottonumeroRegistrazione `[0..1]` : `cm:DatoNU_Type` {'maxLength': '3'}
        - DataRegistrazione `[1..1]` : `cm:DatoDT_Type`

## Altri quadri (non nel perimetro: solo struttura di primo livello)

- **QuadroEI_new** `[0..1]` — obbligatorio in presenza di Discordanza dati intestatario o Passaggi senza atti legali in almeno un quadro EB o EC con provincia diversa da EE. Non deve essere presente in caso contrario. Non deve essere presente se 'Dichiarazione sostitutiva è uguale a '3'
- **QuadroEL** `[0..1]` — Non deve essere presente se 'Dichiarazione sostitutiva è uguale a '3'
- **QuadroEM** `[0..1]` — Non deve essere presente se 'Dichiarazione sostitutiva è uguale a '3'
- **QuadroEN** `[0..1]` — Obbligatorio in presenza di casella bene aziendale in almeno un quadro EB, EC,EL, EM. Non deve essere presente se 'Dichiarazione sostitutiva è uguale a '3'
- **QuadroEO** `[0..1]` — Non deve essere presente se 'Dichiarazione sostitutiva è uguale a '3'
- **QuadroEP** `[0..1]` — Non deve essere presente se 'Dichiarazione sostitutiva è uguale a '3'
- **QuadroEQ** `[0..1]` — Non deve essere presente se 'Dichiarazione sostitutiva è uguale a '3'

## Enumerazioni dei codici

### CodiciCarica_Type (9 valori)

| codice | descrizione (documentazione XSD) |
|---|---|
| `1` | erede, chiamato all'eredità |
| `2` | legatario |
| `3` | rappresentante legale o tutore di legatario |
| `4` | rappresentante legale, tutore, erede dell'erede |
| `5` | curatore dell'eredita' giacente |
| `6` | amministratore dell'eredita' |
| `7` | esecutore testamentario |
| `8` | persona immessa nel possesso temporaneo dei beni dell'assente |
| `9` | trustee (soggetto che amministra i beni e i diritti conferiti in trust) o suo rappresentante |

### StatoCivile_Type (7 valori)

| codice | descrizione (documentazione XSD) |
|---|---|
| `1` | celibe/nubile |
| `2` | coniugato/a in regime di comunione dei beni |
| `3` | coniugato/a in regime di separazione dei beni |
| `4` | vedovo/a |
| `5` | separato/a |
| `6` | divorziato/a - Scioglimento dell’unione civile |
| `7` | Parte dell’unione civile |

### Sesso_Type (2 valori)

| codice | descrizione (documentazione XSD) |
|---|---|
| `M` | Maschio |
| `F` | Femmina |

### TipoSoggetto_Type (6 valori)

| codice | descrizione (documentazione XSD) |
|---|---|
| `1` | Erede |
| `2` | Legatario |
| `3` | Chiamato all'eredita' |
| `4` | Coniuge/Parte dell’unione civile superstite rinunciatario |
| `5` | Trust |
| `6` | Altro |

### GradoParentela_Type (43 valori)

| codice | descrizione (documentazione XSD) |
|---|---|
| `01` | Coniuge/Parte dell’unione civile |
| `02` | Figlio/a |
| `03` | Genitore |
| `04` | Nipote in linea retta |
| `5A` | Nonno/a paterno/a |
| `5B` | Nonno/a materno/a |
| `06` | Pronipote in linea retta |
| `7A` | Bisavo paterno |
| `7B` | Bisavo materno |
| `08` | Figlio/a di pronipote in linea retta |
| `9A` | Trisavo paterno |
| `9B` | Trisavo materno |
| `10` | Fratello/sorella germano |
| `11` | Fratello/sorella unilaterale |
| `12` | Genitore del Coniuge/Parte dell’unione civile |
| `13` | Cognato/a |
| `14` | Nonno/a del Coniuge/Parte dell’unione civile |
| `15` | Nipote (figlio/a di fratello/sorella) |
| `15A` | Coniuge di nipote (figlio/a di fratello/sorella) |
| `16` | Zio/a |
| `17` | Nipote del Coniuge/Parte dell’unione civile (figlio/a di figlio) |
| `18` | Zio/a del Coniuge/Parte dell’unione civile |
| `19` | Bisavo del Coniuge/Parte dell’unione civile |
| `20` | Figlio/a di nipote (figlio/a di figlio/a di fratello/sorella) |
| `21` | Cugino/a |
| `22` | Prozio/a |
| `23` | Figlio/a di nipote del Coniuge/Parte dell’unione civile (Figlio/a di Figlio/a di Figlio/a) |
| `24` | Figlio/a del Coniuge/Parte dell’unione civile |
| `25` | Figlio/a del cognato |
| `26` | Nuora/Genero |
| `27` | Nipote di nipote (in linea collaterale) |
| `28` | Figlio/a di cugino/a |
| `29` | 2° cugino/a |
| `30` | Fratello/sorella di bisavo |
| `31` | Altro cugino/a |
| `32` | Figlio di 2° cugino/a |
| `33` | Nipote di trisavo |
| `34` | Nipote di cugino/a |
| `35` | Estraneo/a |
| `36` | Stato; |
| `37` | Regioni, province, comuni, enti pubblici, ONLUS e terzo settore; |
| `38` | Enti pubblici, fondazioni ed associazioni riconosciute, art.3,c.1 TUS, movimenti e partiti politici, art.3, c.4bis TUS, enti religiosi, circ. min. 22/01/2008 n. 3/E; |
| `39` | Enti pubblici, fondazioni e associazioni riconosciute, art. 3,c. 2 TUS |

### GradoParentela2_Type (3 valori)

| codice | descrizione (documentazione XSD) |
|---|---|
| `02` | Figlio/a |
| `10` | Fratello/sorella germano |
| `11` | Fratello/sorella unilaterale |

### CodiciDirittoImmobili_Type (10 valori)

| codice | descrizione (documentazione XSD) |
|---|---|
| `10` | Oneri reali |
| `1` | Proprieta' |
| `1S` | Proprieta' superficiaria |
| `1T` | Proprieta' per l'area |
| `2` | Nuda proprieta' |
| `2S` | Nuda proprieta' superficiaria |
| `2T` | Nuda proprieta' per l'area |
| `4` | Diritto del concedente |
| `5` | Diritto dell'enfiteuta |
| `6` | Superficie |

### CodiciDiritto_Type (17 valori)

| codice | descrizione (documentazione XSD) |
|---|---|
| `3` | Abitazione |
| `3S` | Abitazione su proprieta' superficiaria |
| `7` | Uso |
| `7S` | Uso su proprieta' superficiaria |
| `8` | Usufrutto |
| `8S` | Usufrutto su proprieta' superficiaria |
| `8T` | Usufrutto su proprieta' per l'area |
| `10` | Oneri reali |
| `1` | Proprieta' |
| `1S` | Proprieta' superficiaria |
| `1T` | Proprieta' per l'area |
| `2` | Nuda proprieta' |
| `2S` | Nuda proprieta' superficiaria |
| `2T` | Nuda proprieta' per l'area |
| `4` | Diritto del concedente |
| `5` | Diritto dell'enfiteuta |
| `6` | Superficie |

### CodiciDirittoNonImmobili (2 valori)

| codice | descrizione (documentazione XSD) |
|---|---|
| `1` | Proprieta' |
| `2` | Nuda proprieta' |

### CodiciDirittoNonImmobiliDevoluzione (4 valori)

| codice | descrizione (documentazione XSD) |
|---|---|
| `1` | Proprieta' |
| `2` | Nuda proprieta' |
| `7` | Uso |
| `8` | Usufrutto |

### CodiciNatura_Type (7 valori)

| codice | descrizione (documentazione XSD) |
|---|---|
| `F` | Bene futuro |
| `EU` | Ente urbano |
| `C` | Fabbricato in corso di costruzione |
| `R` | Fabbricato rurale |
| `LE` | Lotto edificabile |
| `PF` | Porzione di bene futuro |
| `T` | Terreno |

### TerrenoEdificabile_Type (3 valori)

| codice | descrizione (documentazione XSD) |
|---|---|
| `1` | Terreno edificabile |
| `2` | Terreno parzialmente edificabile |
| `3` | Terreno non edificabile |

### CodiciCategoriaCatastale_Type (52 valori)

| codice | descrizione (documentazione XSD) |
|---|---|
| `A1` | Abitazioni di tipo signorile |
| `A2` | Abitazione di tipo civile |
| `A3` | Abitazione di tipo economico |
| `A4` | Abitazione di tipo popolare |
| `A5` | Abitazione di tipo ultrapopolare |
| `A6` | Abitazione di tipo rurale |
| `A7` | Abitazione in villini |
| `A8` | Abitazione in ville |
| `A9` | Castelli, palazzi di eminenti pregi artistici o storici |
| `A10` | Uffici e studi privati |
| `A11` | Abitazioni e alloggi tipici dei luoghi |
| `B1` | Collegi e convitti, educandati, ricoveri orfanotrofi, ospizi, conventi,seminari, caserme |
| `B2` | Case di cura ed ospedali (senza fine di lucro) |
| `B3` | Prigioni e riformatori |
| `B4` | Uffici pubblici |
| `B5` | Scuole e laboratori scientifici |
| `B6` | Biblioteche, pinacoteche, musei, gallerie, accademie, circoli ricreativi e culturali senza fine di lucro, che non hanno sede in edifici della categoria A9 |
| `B7` | Cappelle ed oratori non destinati all'esercizio pubblico del culto |
| `B8` | Magazzini sotterranei per deposito derrate |
| `C1` | Negozi e botteghe |
| `C2` | Magazzini e locali di deposito; cantine e soffitte se non unite all'unita' immobiliare abitativa |
| `C3` | Laboratori per arti e mestieri |
| `C4` | Fabbricati e locali per esercizi sportivi |
| `C5` | Stabilimenti balneari e di acque curative |
| `C6` | Stalle, scuderie, rimesse, autorimesse |
| `C7` | Tettoie, posti auto su aree private, posti auto coperti |
| `D1` | Opifici |
| `D2` | Alberghi e pensioni |
| `D3` | Teatri, cinematografi, sale per concerti e spettacoli; arene, parchi giochi, zoo-safari |
| `D4` | Case di cura e ospedali |
| `D5` | Istituti di credito, cambio, assicurazione |
| `D6` | Fabbricati, locali, aree attrezzate per esercizi sportivi |
| `D7` | Fabbricati costruiti o adattati per le speciali esigenze di un'attivita' industriale e non suscettibile di destinazione diversa senza radicali trasformazioni |
| `D8` | Fabbricati costruiti o adattati per le speciali esigenze di un'attivita' commerciale e non suscettibile di destinazione diversa senza radicali trasformazioni |
| `D9` | Edifici galleggianti o assicurati a punti fissi del suolo; ponti privati soggetti a pedaggio; aree attrezzate per l'appoggio di palloni aerostatici e dirigibili |
| `D10` | Fabbricati per funzioni produttive connesse alle attivita' agricole |
| `E1` | Stazioni per servizi di trasporto terrestri, marittimi ed aerei; stazioni per metropolitane, stazioni per ferrovie; impianti di risalita in genere |
| `E2` | Ponti comunali e provinciali soggetti a pedaggio |
| `E3` | Costruzioni e fabbricati per speciali esigenze pubbliche |
| `E4` | Recinti chiusi per mercati, fiere, posteggio bestiame e simili |
| `E5` | Fabbricati costituenti fortificazioni e loro dipendenze |
| `E6` | Fari, semafori, torri per rendere pubblico l'uso dell'orologio comunale |
| `E7` | Fabbricati per l'esercizio pubblico dei culti |
| `E8` | Fabbricati e costruzioni nei cimiteri esclusi i colombari, i sepolcri e le tombe di famiglia |
| `E9` | Edifici a destinazione particolare non comprese nelle categorie precedenti del gruppo E |
| `F1` | Area urbana |
| `F2` | Unita' collabenti |
| `F3` | Unita' in corso di costruzione |
| `F4` | Unita' in corso di definizione |
| `F5` | Lastrico solare |
| `F6` | Fabbricato in attesa di dichiarazione |
| `F7` | Infrastrutture di reti pubbliche di comunicazione |

### TipoCespite_Type (5 valori)

| codice | descrizione (documentazione XSD) |
|---|---|
| `BI` | beni inventariati; |
| `CR` | crediti, rimborsi fiscali, compresi gli interessi legali maturati fino alla data di apertura della successione, censi, rendite, pensioni (comprese nell’attivo ereditario) e somme depositate in conto corrente; |
| `DN` | denaro, gioielli e mobilia non inventariati; |
| `AB` | altri beni |
| `GD` | cosa genericamente determinata - art. 653 c.c. |

### CodiciPassivita_Type (12 valori)

| codice | descrizione (documentazione XSD) |
|---|---|
| `1` | Spese mediche e chirurgiche sostenute dagli eredi per conto del defunto negli ultimi sei mesi; |
| `2` | Spese funerarie, nei limiti deducibili previsti dall'articolo 24, comma 2; |
| `3` | Mutui, contratti per l'acquisto di immobili; |
| `4` | Debiti verso aziende o istituti di credito (saldi passivi su conti correnti); |
| `5` | Debiti inerenti l'esercizio di imprese; |
| `6` | Debiti cambiari; |
| `7` | Debiti verso lo Stato, enti pubblici territoriali ed enti pubblici che gestiscono forme obbligatorie di previdenza e di assistenza sociale; |
| `8` | Rapporto di lavoro subordinato ( TFR, trattamenti previdenziali integrativi); |
| `9` | Debiti tributari; |
| `10` | Assegni di mantenimento al Coniuge/Parte dell’unione civile divorziato; |
| `11` | Legato o altro onere che grava su una quota ereditaria o sul legato stesso. |
| `12` | Altre passivita'. |

### CodiciAgevolazioni_Type (16 valori)

| codice | descrizione (documentazione XSD) |
|---|---|
| `A` | beni culturali (vincolo anteriore a apertura successione), art. 13, comma 1; |
| `C` | terreni agricoli "compendio unico" in zone montane art. 5bis L. 97/94; |
| `D` | Aziende esenti o rami di esse, quote sociali e azioni facenti parte dell'attivo ereditario (immobili) art. 3, D.Lgs 346/90, artt. 1 e 10 D.Lgs 347/90; |
| `E` | Terreni agricoli "compendio unico" generale art. 5bis D.Lgs. 228/2001; |
| `G` | terreni/Aziende Agricole devolute a giovani imprenditori agricoli professionali art.14 L.441/98; |
| `H` | immobili demoliti o dichiarati inagibili a seguito di eventi sismici; |
| `M` | fondi rustici in territori montani e/o immobili in comunita' montane inseriti in piani di sviluppo art. 9, commi 2 e 3 DPR 601/73; |
| `N` | boschi in terreni montani art. 9, comma 5 DPR 601/73; |
| `P` | Abitazione "prima casa" art. 69 L.342/2000 art.1 tariffa D.Lgs 347/90; |
| `Z` | Abitazione "prima casa" art. 69 L.342/2000 art.1 tariffa D.Lgs 347/90 (immobile contiguo); |
| `X` | pertinenza "prima casa" art. 69 L.342/2000 art.1 tariffa D.Lgs 347/90 (insieme all'immobile principale); |
| `Y` | pertinenza "prima casa" art. 69 L.342/2000 art.1 tariffa D.Lgs 347/90 (senza l'immobile principale); |
| `F` | immobili di impresa artigiana familiare art. 25, comma 4 |
| `L` | beni culturali (vincolo posteriore a apertura successione) art. 25, comma 2 |
| `Q` | Aziende, quote societa' di persone, beni strumentali in comuni montani < 5.000 abitanti, art. 25, comma 4 bis,D.Lgs 346/90 |
| `R` | fondi rustici art. 25, comma 3 |

### CodiciRiduzioni25comma1_Type (5 valori)

| codice | descrizione (documentazione XSD) |
|---|---|
| `1` | beni/diritti oggetto di precedenti successioni/donazioni (entro un anno) |
| `2` | beni/diritti oggetto di precedenti successioni/donazioni (entro due anni) |
| `3` | beni/diritti oggetto di precedenti successioni/donazioni (entro tre anni) |
| `4` | beni/diritti oggetto di precedenti successioni/donazioni (entro quattro anni) |
| `5` | beni/diritti oggetto di precedenti successioni/donazioni (entro cinque anni) |

### DirittoAbitazione_Type (8 valori)

| codice | descrizione (documentazione XSD) |
|---|---|
| `1` | il Coniuge/Parte dell’unione civile superstite richiede l’agevolazione “prima casa” relativamente all'immobile principale (cod. P) |
| `2` | il Coniuge/Parte dell’unione civile superstite richiede l’agevolazione “prima casa” relativamente all'immobile contiguo (cod. Z) a quello principale |
| `3` | il Coniuge/Parte dell’unione civile superstite richiede l’agevolazione “prima casa” relativamente alla pertinenza (cod. X) dell'immobile principale |
| `4` | il Coniuge/Parte dell’unione civile superstite non richiede l’agevolazione “prima casa” |
| `5` | il Coniuge/Parte dell’unione civile superstite rinunciatario richiede l’agevolazione “prima casa” relativamente all'immobile principale (cod. P) |
| `6` | il Coniuge/Parte dell’unione civile superstite rinunciatario richiede l’agevolazione “prima casa” relativamente all'immobile contiguo (cod. Z) a quello principale |
| `7` | il Coniuge/Parte dell’unione civile superstite rinunciatario richiede l’agevolazione “prima casa” relativamente alla pertinenza (cod. X) dell'immobile principale |
| `8` | il Coniuge/Parte dell’unione civile superstite rinunciatario non richiede l’agevolazione “prima casa” |

### DichiarazioneSostitutiva_Type (3 valori)

| codice | descrizione (documentazione XSD) |
|---|---|
| `1` | Dichiarazione sostitutiva con nuova trascrizione e voltura sostitutiva |
| `2` | Dichiarazione sostitutiva senza nuova trascrizione |
| `3` | Dichiarazione integrativa con sola presentazione di documentazione |

### ImpegnoPresentazione_Type (2 valori)

| codice | descrizione (documentazione XSD) |
|---|---|
| `1` | la dichiarazione e' stata predisposta dal contribuente |
| `2` | la dichiarazione e' stata predisposta da chi effettua l'invio |

### TempisticaPagamento_Type (2 valori)

| codice | descrizione (documentazione XSD) |
|---|---|
| `1` | pagamento non contestuale alla presentazione della dichiarazione |
| `2` | pagamento contestuale alla presentazione della dichiarazione |

