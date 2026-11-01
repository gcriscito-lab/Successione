# Skill di sviluppo: configurazione e stato

Aggiornato: 2026-11-01. Le skill sono **strumenti di sviluppo**: non sono dipendenze del programma, non sostituiscono
le fonti ministeriali, non garantiscono l'accesso a Entratel e non autorizzano a dichiarare superato un controllo
ufficiale mai eseguito. Distinguere sempre: prova simulata / controllo locale / verifica ufficiale.

## Ambiente effettivo e metodo scelto
Sessione **cloud** di Claude Code su repository (non un thread di progetto). Dalla documentazione ufficiale
(code.claude.com/docs/en/skills, sezioni "Where skills live" e "Skills in Cowork and cloud sessions", letta il 2026-11-01):
- `~/.claude/skills/` locale **non** è letta nelle sessioni cloud;
- le skill di **progetto** in `.claude/skills/<nome>/SKILL.md` committate nel repository **sono caricate** nelle sessioni cloud
  diverse dai thread di progetto (in questi ultimi non sono disponibili: occorre abilitarle nell'account claude.ai);
- una cartella `.claude/skills/` creata *durante* la sessione richiede `/reload-skills` (o una nuova sessione).

Metodo: installazione limitata al progetto, committata, con licenza e commit sorgente accanto a ogni skill.
Ripristino ripetibile: `python scripts/installa_skills.py` (commit fissati nello script; `--verifica` controlla i file).

## Stato per skill
| Skill | Fonte e commit | Licenza | Installazione | Stato in questa sessione | Passaggio manuale |
|---|---|---|---|---|---|
| mcp-builder | anthropics/skills `ca45fc496a34…` | Apache-2.0 | `.claude/skills/mcp-builder/` | **installata, non caricata** (`Unknown skill`: cartella creata a sessione avviata). Contenuto letto e applicato a mano | `/reload-skills` oppure nuova sessione |
| webapp-testing | anthropics/skills `ca45fc496a34…` | Apache-2.0 | `.claude/skills/webapp-testing/` | **installata, non caricata**; la prova GUI con Playwright è stata fatta con lo stesso metodo | idem |
| dispatching-parallel-agents | obra/superpowers 7.0.1 `2ce8aa15d05b…` | MIT | `.claude/skills/dispatching-parallel-agents/` | **installata, non caricata**; criteri applicati nella delega ai tre subagenti | idem |
| systematic-debugging | obra/superpowers 7.0.1 `2ce8aa15d05b…` | MIT | `.claude/skills/systematic-debugging/` (SKILL + 3 riferimenti; esclusi file di test/creazione) | **installata, non caricata** | idem |
| verification-before-completion | obra/superpowers 7.0.1 `2ce8aa15d05b…` | MIT | `.claude/skills/verification-before-completion/` | **installata, non caricata** | idem |
| pdf | skill ufficiale Anthropic sincronizzata dall'account claude.ai | **proprietaria** (© Anthropic, tutti i diritti riservati) | **non copiata** nel repository pubblico | **caricata e usata** (invocata con `Skill`; guida a pypdf/qpdf/pdftotext/reportlab) | nessuno |

Non installata la suite Superpowers completa né altri componenti (hook, comandi, agenti).

## Cosa le skill non coprono
- `pdf` descrive lettura/generazione/manipolazione PDF; **non tratta PDF/A**. La conformità si dimostra solo con un
  validatore indipendente (veraPDF): vedi `docs/PDFA.md` e `docs/DECISIONI.md`.
- Nessuna skill sostituisce XSD, istruzioni e specifiche in `fonti/`.

## Verifica del caricamento
`Skill(skill="mcp-builder")` → esito registrato qui sopra. Dopo `/reload-skills` ripetere per ciascuna skill e aggiornare la
colonna "Stato" (da "installata, non caricata" a "caricata"); segnare "utilizzata" solo dopo l'uso effettivo con la skill
caricata.
