# EF per successioni aperte dal 2006-10-03 al 2024-12-31

**Fonti**: Fascicolo I pp. PDF 9, 39 («l'imposta di successione deve essere autoliquidata solo per le successioni aperte a partire dal
01/01/2025, mentre per quelle aperte prima l'imposta continua ad essere liquidata dagli uffici»; misura fissa 200 euro dal 1° gennaio 2014,
168 euro per le successioni aperte tra il 3 ottobre 2006 e il 31 dicembre 2013), p. 46 (la sezione V-bis vale dal 2025), p. 49 (Sezione VI,
sanzioni e interessi: «puo' essere utilizzata»); XSD `fornituraSUC13_v1.xsd`, annotazioni di `QuadroEF` (obbligatorio con EA e almeno un
rigo EB/EC/EL/EM, e dal 2025 sempre), di `SezioneVBis_ImpostaSuccessione` («non puo' essere presente per le successioni aperte prima del
01/01/2025» salvo `PagamentoAnticipatoTrust` per carica 9), delle imposte fisse («168 ... 200 se la data di decesso e' >= 01/01/2014») e di
`DataDecesso` (maggiore del 2 ottobre 2006).

**Cosa genera il programma** (`quadri_efgh.quadro_ef`, funzione `imposta_fissa`):
- sezioni I (ipotecaria), II (catastale), III (tassa ipotecaria, 120 euro per circoscrizione), IV (bollo, 85 euro per circoscrizione) e totale EF19 /
  `ImportoDaVersare` del frontespizio, **senza** la sezione V-bis (nessuna chiamata a `calcolo.py` ne' a `_sezione_vbis`);
- misura fissa per data del decesso: 200 euro dal 2014-01-01, 168 dal 2006-10-03 al 2013-12-31, ovunque l'imposta fissa interviene: rigo EF4
  (prima casa, numero immobili x fissa), `ImpostaCatastaleFissa`, minimo nel dovuto (EF5/EF11) e soli terreni non edificabili (valori fiscali),
  minimo del codice 1 delle sostitutive (non inferiore alla fissa dell'epoca);
- interazione verificata con prima casa, minimo fisso, soli terreni, piu' comuni (conservatorie) e sostitutive 1 e 2;
- il quadro EF resta obbligatorio, e quindi bloccante se non generabile, con EA e immobili anche prima del 2025.

**Avvisi** (non bloccano):
- `EF_TARDIVA_SANZIONI_NON_CALCOLATE`: dichiarazione presentata oltre i dodici mesi dal decesso con imposte ipocatastali da versare. La
  Sezione VI (ravvedimento: sanzioni e interessi) e' facoltativa e non si calcola perche' il tasso legale per anno non e' nelle fonti.
  Per i decessi precedenti il 2025 la presentazione e' quasi sempre tardiva: valutare sanzioni e interessi a parte.
- `DATO_NON_APPLICABILE_PRIMA_DEL_2025`: tempistica di pagamento, rateazione e acconto riguardano l'imposta di successione autoliquidata
  (sezione V-bis) e non vengono esportati per queste successioni.

**Non coperto / bloccato**
- Successioni aperte fino al 2 ottobre 2006: la data e' respinta dalla validazione (annotazione XSD di `DataDecesso`).
- Trust con carica 9 e `PagamentoAnticipatoTrust` (il pagamento anticipato dell'imposta e' esprimibile anche prima del 2025): non trattato.
- Sezione VI (sanzioni e interessi), crediti d'imposta, copia conforme: restano fuori, come per le successioni dal 2025.
- Le citazioni di pagina del Fascicolo nella mappa di esportazione (`FO.fonte_fasc1`) riportano ancora «decorrenza dal 2025-01-01»: per queste
  successioni valgono i riferimenti ai righi EF1-EF16, non la decorrenza.

**Evidenza (2026-11-05, locale, dati sintetici)**: `tests/test_ef_storico.py`. Controllo ufficiale SUC13 2.3.1 positivo (solo l'avviso 3345 sull'attestazione) su: caso A10 con
decesso 2024, 2016 e 2013; minimo fisso 2013 e 2024; soli terreni 2022 e 2013; prima casa 2013 e 2024; sostitutive 1 e 2 con decesso 2013 e 2020;
due comuni con decesso 2018. Respinti: `168` per un decesso 2024 e `200` per un decesso 2013 (diagnostico 3076: la misura fissa dipende davvero
dalla data) e un totale alterato (diagnostico 1012).
