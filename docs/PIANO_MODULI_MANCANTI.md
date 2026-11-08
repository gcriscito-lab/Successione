# Piano dei moduli mancanti (ramo `sviluppo-moduli`)

> **Superato (07/11/2026).** Piano di lavoro del 05/11/2026: molti dei moduli elencati sono stati poi realizzati
> e uniti (verificare caso per caso). Lo stato attuale e' in `docs/STATO_LAVORI.md` e `docs/MATRICE_COPERTURA.md`.

Creato il 2026-11-05. Il ramo stabile per la pratica reale di sabato e' il tag `stabile-pratica-reale-20261105` (ramo
`claude/successioni-dichiarazioni-app-fhcwbe`): **non si tocca fino a dopo la pratica**. Qui si sviluppa tutto il resto.

## Regole di lavoro
- Ogni regola viene dalle fonti (`fonti/`: XSD con annotazioni, Fascicolo I e II, Specifiche, Allegato): mai dalla memoria. Se la fonte non basta, il caso resta
  **bloccato con un motivo esplicito** e va nel registro dei dubbi.
- Accettazione di ogni pacchetto: test dai valori delle fonti + **controllo ufficiale SUC13 2.3.1 locale positivo** su almeno 3 casi sintetici e, dove si puo', un
  negativo (alterazione respinta). Dove il controllo e le fonti discordano, vince il controllo e lo si documenta (come per il minimo fisso).
- Un pacchetto = un ramo di lavoro, una scheda in `docs/regole/<tema>.md`, test dedicati; la matrice di copertura si aggiorna in integrazione.

## Pacchetti
| # | Pacchetto | Contenuto (dalla matrice) | Stato |
|---|---|---|---|
| 1 | Successioni 2014-2024 | quadro EF senza sezione V-bis, imposta fissa per periodo | **integrato** (2006-2024) |
| 2 | Agevolazioni | A, N, G, M, H, C, D, E (righe EF2, AgevolazioneM, esclusioni da EE) | **integrato** (G solo in EN; requisiti soggettivi a carico del professionista) |
| 3 | Soggetti | rinunciatari (tipo 4), trust (5), enti/Stato (gradi 36-39), residenza estera, soggetto su piu' righi | **integrato** (restano trust, altro, Stato) |
| 4 | Beni esteri | provincia EE, imposta versata all'estero e detrazione, certificazione in EG | **integrato** |
| 5 | Immobili particolari | graffati, rendita proposta, immobili aziendali, diritto di abitazione, discordanza (EI), piu' di tre estremi EI | **integrato** (diritto di abitazione bloccato) |
| 6 | Frontespizio | integrativa codice 3, cariche 2-9, legge estera, eventi eccezionali, beneficio d'inventario, residenza estera del defunto | **integrato** (restano cariche 5, 6, 8, 9) |
| 7 | EG ed EH | inventario, sezioni III-IV di EH, separazione, unione civile, disabili/interdetti, morte presunta | **integrato** (restano EH III, morte presunta) |
| 8 | ED e passivita' | piu' di tre destinatari, titoli esenti con passivita' collegate | **integrato** (titoli esenti bloccati) |
| 9 | Pagamenti | crediti d'imposta, rimborsi nelle sostitutive; sanzioni/interessi solo con fonte dei tassi | **integrato** (crediti, rimborsi, sanzioni/interessi dichiarati dal professionista; tasso legale non calcolato) |
| 10 | Quote di legge | nonni e altri ascendenti, rinunce nella devoluzione | **integrato** (nonni, bisavi, trisavi; altri parenti bloccati) |
| 11 | Personalizzazione dell'app | tema, accento, densita', intestazione dello studio, quadri predefiniti, avvio | **integrato** |

Fuori da questo piano (servono credenziali o campioni): collegamenti Entratel/catasto/ricevute, lettore di visure PDF.
| 12 | Cariche e soggetti residui | cariche 5, 6, 8; tipo «Altro» | **integrato** (restano carica 9, trust, Stato) |
| 13 | Strumenti nelle impostazioni | diagnosi, Desktop Telematico/Multifile, versione del controllo | **integrato** |

Suite completa del ramo `sviluppo-moduli` al 2026-11-06: 1614 test passati, 1 saltato.
