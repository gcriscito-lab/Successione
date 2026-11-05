# Frontespizio: caselle, dichiarazione integrativa (codice 3) e codici carica

Codice: `src/successioni/telematico/frontespizio.py` (con ganci in `esporta.py`, `quadri_efgh.py`, `sostitutiva.py`). Test: `tests/test_frontespizio.py`.
Tutti i casi positivi sono stati accettati dal controllo ufficiale SUC13 2.3.1 eseguito in locale il 2026-11-05 su dati sintetici (non e' una
verifica con l'Agenzia).

**Fonti**: XSD `fornituraSUC13_v1.xsd` (`FrontespizioSUC_Type`, `QuadroEG`, `QuadroEH`), Fascicolo I pp. PDF 11-15 (tipo di dichiarazione, eventi
eccezionali, data opzione, beneficiari, residenza estera, presentatore, casi particolari), p. 45 (rigo EF15), p. 49-50 (EG).

## Caselle (dati in `opzioni.telematico.dichiarazione`)
| Chiave | Elemento XSD | Regola | Esito col controllo |
|---|---|---|---|
| `legge_estera` (bool) | `Devoluzione/LeggeEstera` | con la legge estera le quote non sono quelle dell'Allegato 5: nessuna verifica delle quote di legge | positivo |
| `eventi_eccezionali` (bool, codice 1) | `TipoDichiarazione/EventiEccezionali` | inagibilita' dell'immobile prima casa gia' agevolato; **richiede il rigo EG8 «Altro»** (certificazione) | senza «Altro»: 3323; con: positivo |
| `data_opzione` (data) | `TipoDichiarazione/DataOpzione` | opzione art. 24-bis TUIR: non inferiore al 2017-01-01 e anteriore al decesso | positivo |
| `beneficio_inventario` (bool) | `Beneficiari/AccettazioneConBeneficioInventario` | casella; la documentazione si allega nel quadro EG (non obbligatoria per il controllo) | positivo |
| `residenza_estera_defunto` (1 o 2) | `DatiDefunto/UlterioriDati/ResidenzaEstera` | 1 = mai residente in Italia o ignota; 2 = in parte in Italia e in parte all'estero | positivo |
| `casi_particolari` (bool) | `CasiParticolari/CasiParticolari` | «non dar corso alle volture»: la **tassa ipotecaria EF15 e' di 65 euro per circoscrizione** invece di 120 (Fascicolo I p. 45) | con 120: 3076; con 65: positivo |
| `presentatore.data_decorrenza` | `Presentatore/DecorrenzaTerminePresentazione` | non inferiore alla data del decesso | positivo |

## Dichiarazione integrativa: codice 3 (solo frontespizio ed EG)
`tipo_dichiarazione = sostitutiva` e `codice_sostitutiva = 3` con gli estremi della prima dichiarazione (anno >= 2014, volume 88888/88889, numero).
Le annotazioni XSD vietano gli altri quadri: l'esportazione produce **solo `Frontespizio` e `QuadroEG`**, con la sola `CasellaEG`. Il resto della pratica
(soggetti EA, beni, passivita', devoluzioni) non viene esportato e un avviso `INTEGRATIVA_SOLO_FRONTESPIZIO_EG` lo dice. Il presentatore resta nel
frontespizio anche se e' un erede (non compare nel quadro EA). Il quadro EG con la documentazione e' obbligatorio; le imposte gia' versate non si indicano
(nessuna liquidazione). Il controllo ufficiale accetta il file senza diagnostici.

## Codici carica del presentatore
| Codice | Supportato | Regole (annotazioni XSD di `CodiceCarica`, `CodiceFiscaleRappresentato`, `QuadroEH/Dichiarante`) |
|---|---|---|
| 1 erede/chiamato | si (gia') | nel quadro EA con tipo 1 o 3 |
| 2 legatario | si | nel quadro EA con tipo 2; devoluzione per testamento obbligatoria in assenza di legge estera |
| 3 rappresentante di legatario | si | `presentatore.rappresentato_cf` obbligatorio (diverso da defunto e presentatore); EH: `FlagAssenzaDichiarante`, e il rappresentato anche nel presentatore EH (controllo 3214/3008) |
| 4 rappresentante legale/tutore | si | come il 3 |
| 7 esecutore testamentario | si | solo con devoluzione per testamento; **nessun quadro EH**; EG1 «DichSost» (dichiarazione sostitutiva sullo stato di famiglia) ed EG7 obbligatori (controllo 3328) |
| 5 curatore, 6 amministratore | no | richiedono soggetto EA tipo «Altro» (6), casi particolari, agevolazioni ristrette |
| 8 possesso temporaneo (assente) | no | richiede la sezione `MortePresunta` del quadro EH |
| 9 trustee | no | richiede soggetti Trust (5), sezioni Trust e pagamento anticipato |

Il presentatore puo' essere **residente all'estero** (`presentatore.residente_estero {codice_stato, stato, stato_federato, localita, indirizzo}`, stesse
regole e tabella degli Stati dei soggetti EA).

## Non coperto
- Codici carica 5, 6, 8, 9 (motivi sopra) e quindi la **morte presunta** (`MortePresunta`, solo con carica 8).
- Casi particolari automatici per soli immobili con diritto 10 o tutti gli eredi chiamati: la casella si imposta a mano; l'obbligo non e' verificato.
- Documentazione obbligatoria del beneficio d'inventario nel quadro EG (non richiesta dal controllo).
- Presentatori con carica 3, 4, 7 e agevolazioni/riduzioni richieste dal dichiarante (EH sezioni II e IV): non provati.
