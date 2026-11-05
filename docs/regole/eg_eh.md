# Quadri EG ed EH: separazione, unione civile, disabili e interdetti, reintegro, inventario, EG10 (pacchetto 7)

Codice: `src/successioni/telematico/quadri_efgh.py` (`quadro_eh`, `_eh_separazione_unione`, `_eh_interdetti`, `_eh_reintegri`,
`_eh_moduli_ulteriori`, `quadro_eg`). Test: `tests/test_eg_eh.py`.

**Fonti**: XSD `fornituraSUC13_v1.xsd`, annotazioni di `QuadroEH/PrimoModulo/SezioneI_DichSost` (`Separazione`, `FlagNoScioglimentoUnioneCivile`,
`Interdetti`, `ReintegroDiritti`, `FlagProspetto`) e di `QuadroEG` (`Inventario`, `AgevolazioniImposteIpocatastali`); Fascicolo I pp. PDF 18 (coniuge
separato) e 51-52 (Sezione I, lettere d, e, g, h, l).

## Implementato (accettato dal controllo SUC13 2.3.1 eseguito in locale il 2026-11-05, dati sintetici)
| Funzione | Dati | Regola |
|---|---|---|
| **Separazione** (stato civile 5) | `dichiarazione.separazione_con_colpa` (true/false) | `false` -> `FlagAssenzaSeparazione`; `true` -> `FlagSeparazione`. Con colpa e devoluzione per legge il coniuge (grado 01) non puo' essere beneficiario (annotazione XSD): errore `REGOLA_SEPARAZIONE`. Dato obbligatorio con stato civile 5; non ammesso con altri stati civili. |
| **Unione civile** (stato civile 7) | `dichiarazione.no_scioglimento_unione_civile` (true) | `FlagNoScioglimentoUnioneCivile`: obbligatorio con stato civile 7, non ammesso altrimenti. |
| **Disabili e interdetti** | `persone[id].portatore_handicap` + `certificatore_disabilita` (estremi del verbale L. 104/1992 art. 4 o della sentenza, max 35 caratteri) | un rigo EH7 per soggetto con rigo e modulo del quadro EA; il primo nel primo modulo, gli altri uno per modulo (`Modulo/SezioneI_DichSost/PresenzaInterdetti`). Il certificatore e' obbligatorio. |
| **Reintegro dei diritti di legittima** | `dichiarazione.reintegro_1` .. `reintegro_3` (ufficio, serie, numero, sottonumero, data) | `ReintegroDiritti`: il primo nel primo modulo, i successivi nei moduli seguenti; estremi duplicati respinti. |
| **Inventario/prospetto (EG3)** | documento con `tipo_eg = Inventario` | `FlagProspetto` in EH; richiede l'attestazione delle copie conformi (`dichiara_copie_conformi`, lettera l) come per le passivita'. |
| **EG10** | documento con `tipo_eg = AgevolazioniImposteIpocatastali` | riga ora ammessa (era respinta come «non supportata»): serve alle agevolazioni C, D, E richieste da un beneficiario diverso dal dichiarante. |

I campi si inseriscono dall'interfaccia: sezione «Separazione, unione civile e reintegro dei diritti» nei dati generali; certificatore nel pannello della persona.

## Evidenza del controllo ufficiale (locale)
- **Positivi** (solo l'avviso 3345): separato senza colpa con coniuge, separato con colpa senza coniuge, unione civile, un disabile, due disabili (il secondo
  nel secondo modulo), un reintegro, tre reintegri, inventario con attestazione, EG10 con agevolazione C.
- **Negativi** (alterazioni dell'XML respinte): `FlagSeparazione` con stato civile 4 (**3130**), `FlagNoScioglimentoUnioneCivile` con stato civile 2 (**3271**),
  «assenza di interdetti» con una persona con disabilita' nel quadro EA (**2097**).
- Il controllo NON segnala una persona con disabilita' priva del rigo in EH quando e' tolta la casella dal quadro EA (la coerenza inversa e' verificata dal
  nostro export).

## Resta bloccato o non fatto, con motivo
- **Morte presunta** (`MortePresunta`, obbligatoria con codice carica 8): la carica 8 e le cariche 2-9 sono nel pacchetto del frontespizio; con carica diversa da 1
  il quadro EH non si genera (invariato).
- **Sezione III (credito d'imposta)**: «non deve essere presente in assenza del campo EF7»; i crediti d'imposta sono nel pacchetto dei pagamenti.
- **FlagInventari**: «non deve essere barrata in assenza del rigo EG8» (Altro) senza un criterio chiaro nelle fonti su quando va barrata: non generato.
- **Ulteriori testamenti in EH** oltre i due righi e `Presentatore/CodiceFiscaleRappresentato` (carica diversa da 1): invariati.
- La Sezione IV (riduzioni art. 25, agevolazioni A/C/D/E/L/Q) e la Sezione II (prima casa) sono gia' coperte dai pacchetti dedicati: non duplicate.
