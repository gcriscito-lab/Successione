"""Preventivo e parcella della pratica (versione 0.4). Documento di studio, NON una fattura.

I dati stanno nella sezione interna ``note.preventivo`` (non entra nel file telematico):
``{"voci": [{"descrizione", "importo"}], "cassa_pct", "iva_pct", "ritenuta_pct", "numero", "data", "intestatario", "nota",
"includi_imposte"}``.

Nessuna regola fiscale e' scritta nel programma: le percentuali le indica il professionista (vuote = 0). Il programma fa solo
queste somme, mostrate nel documento: contributo = compensi x cassa %; IVA = (compensi + contributo) x IVA %; ritenuta =
compensi x ritenuta %; totale = compensi + contributo + IVA - ritenuta. Le imposte della dichiarazione, se scelte, sono lette
dall'ultimo file generato (``prospetto_cliente.leggi``) e sommate a parte come somme da versare per conto del cliente.
"""
from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from html import escape

from .errori import DatiNonValidi

CENT = Decimal("0.01")
TIPI = {"preventivo": "Preventivo", "parcella": "Parcella"}


def _dec(v, campo: str) -> Decimal:
    if v in (None, ""):
        return Decimal(0)
    try:
        d = Decimal(str(v).strip().replace(",", ".")) if not isinstance(v, (int, float)) else Decimal(str(v))
    except InvalidOperation:
        raise DatiNonValidi(f"{campo}: numero non valido ({v!r})") from None
    if d < 0 or not d.is_finite():
        raise DatiNonValidi(f"{campo}: serve un numero non negativo")
    return d


def _euro(d: Decimal) -> str:
    s = f"{d.quantize(CENT, ROUND_HALF_UP):,.2f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".") + " €"


def _pct(d: Decimal) -> str:
    return f"{d.normalize():f}".replace(".", ",") + "%"


def calcola(prev: dict) -> dict:
    """Somme del documento; importi arrotondati al centesimo riga per riga."""
    prev = prev or {}
    voci = []
    for i, v in enumerate(prev.get("voci") or [], 1):
        if not isinstance(v, dict):
            raise DatiNonValidi(f"voce {i}: attesa una descrizione e un importo")
        desc = str(v.get("descrizione") or "").strip()
        imp = _dec(v.get("importo"), f"voce {i}").quantize(CENT, ROUND_HALF_UP)
        if desc or imp:
            voci.append({"descrizione": desc or f"Voce {i}", "importo": imp})
    pc = {k: _dec(prev.get(k), k) for k in ("cassa_pct", "iva_pct", "ritenuta_pct")}
    for k, d in pc.items():
        if d > 100:
            raise DatiNonValidi(f"{k}: percentuale oltre 100")
    compensi = sum((v["importo"] for v in voci), Decimal(0))
    cassa = (compensi * pc["cassa_pct"] / 100).quantize(CENT, ROUND_HALF_UP)
    iva = ((compensi + cassa) * pc["iva_pct"] / 100).quantize(CENT, ROUND_HALF_UP)
    ritenuta = (compensi * pc["ritenuta_pct"] / 100).quantize(CENT, ROUND_HALF_UP)
    return {"voci": voci, "percentuali": pc, "compensi": compensi, "cassa": cassa, "iva": iva, "ritenuta": ritenuta,
            "totale": compensi + cassa + iva - ritenuta}


def imposte_dal_file(sv, pid: str) -> dict | None:
    """Imposte lette dall'ultimo file generato, con la revisione; None se non c'e' un file."""
    from .errori import ErroreServizio
    from .prospetto_cliente import leggi
    try:
        xml, j = sv.file_export(pid)
    except ErroreServizio:
        return None
    letto = leggi(xml)
    ex = sv.stato_elaborati(pid)["export"]
    return {"righe": letto["imposte"], "totale": letto.get("importo_da_versare") if letto.get("importo_da_versare") is not None
            else letto.get("totale_ef"), "revisione": j["input"]["revisione"], "obsoleto": ex.get("stato") == "obsoleto",
            # una bozza tecnica o un file incompleto puo' avere imposte parziali o mancanti
            "incompleto": j["input"].get("scopo") == "bozza_tecnica" or not j["risultato"].get("completo")}


def html(sv, pid: str, tipo: str, studio: str = "") -> str:
    if tipo not in TIPI:
        raise DatiNonValidi("tipo di documento: preventivo o parcella")
    p = sv.leggi(pid)
    prev = (p["dati"].get("note") or {}).get("preventivo") or {}
    c = calcola(prev)
    imp = imposte_dal_file(sv, pid) if prev.get("includi_imposte") else None
    e = escape
    nome = TIPI[tipo]
    numero = str(prev.get("numero") or "").strip()
    data = str(prev.get("data") or date.today().isoformat())
    try:
        data_it = date.fromisoformat(data).strftime("%d/%m/%Y")
    except ValueError:
        data_it = data
    righe = "".join(f"<tr><td>{e(v['descrizione'])}</td><td class='n'>{_euro(v['importo'])}</td></tr>" for v in c["voci"]) \
        or "<tr><td colspan='2' class='mut'>Nessuna voce: aggiungile in «Preventivo e parcella».</td></tr>"
    pc = c["percentuali"]
    somme = [("Totale compensi", c["compensi"], True)]
    if pc["cassa_pct"]:
        somme.append((f"Contributo cassa {_pct(pc['cassa_pct'])} sui compensi", c["cassa"], False))
    if pc["iva_pct"]:
        somme.append((f"IVA {_pct(pc['iva_pct'])} su compensi e contributo", c["iva"], False))
    if pc["ritenuta_pct"]:
        somme.append((f"Ritenuta d'acconto {_pct(pc['ritenuta_pct'])} sui compensi (si sottrae)", -c["ritenuta"], False))
    somme.append(("Totale " + ("previsto" if tipo == "preventivo" else "da corrispondere"), c["totale"], True))
    tab_somme = "".join(f"<tr class='{'tot' if forte else ''}'><td>{e(t)}</td><td class='n'>{_euro(v) if v >= 0 else '− ' + _euro(-v)}</td></tr>"
                        for t, v, forte in somme)
    blocco_imp = ""
    if prev.get("includi_imposte"):
        if imp is None:
            blocco_imp = "<p class='mut'>Imposte della dichiarazione: genera prima il file della pratica.</p>"
        else:
            r_imp = "".join(f"<tr><td>{e(str(t))}</td><td class='n'>{e(v) if isinstance(v, str) else _euro(Decimal(v))}</td></tr>"
                            for t, v in imp["righe"])
            tot = f"<tr class='tot'><td>Totale imposte da versare con la dichiarazione</td><td class='n'>{_euro(Decimal(imp['totale']))}</td></tr>" \
                if imp["totale"] is not None else ""
            avviso = (" <b>Il file non e' aggiornato alle ultime modifiche.</b>" if imp["obsoleto"] else "") + (
                " <b>Il file e' una bozza o e' incompleto: le imposte possono essere parziali.</b>" if imp.get("incompleto") else "")
            blocco_imp = (f"<h2>Imposte della dichiarazione (per conto del cliente)</h2><table>{r_imp}{tot}</table>"
                          f"<p class='mut'>Dal file generato (revisione {imp['revisione']}); sommate a parte, non fanno parte dei compensi.{avviso}</p>")
    intest = e(str(prev.get("intestatario") or "").strip())
    nota = e(str(prev.get("nota") or "").strip())
    return f"""<!doctype html><html lang="it"><head><meta charset="utf-8"><title>{nome} - {e(p['titolo'])}</title>
<style>body{{font:14px/1.45 system-ui,sans-serif;color:#1d1d1f;background:#fff;max-width:760px;margin:24px auto;padding:0 16px}}
h1{{font-size:22px;margin:0}}h2{{font-size:15px;margin:22px 0 6px}}table{{width:100%;border-collapse:collapse}}
td{{padding:5px 6px;border-bottom:1px solid #ddd}}td.n{{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}}
tr.tot td{{font-weight:600;border-top:2px solid #999}}.mut{{color:#555;font-size:12.5px}}.testa{{display:flex;justify-content:space-between;gap:16px}}
@media print{{body{{margin:0}}}}</style></head><body>
<div class="testa"><div><h1>{nome}{(' n. ' + e(numero)) if numero else ''}</h1><div>{e(studio)}</div></div><div>Data: {e(data_it)}</div></div>
<p>Pratica: <b>{e(p['titolo'])}</b>{('<br>Intestato a: ' + intest) if intest else ''}</p>
<h2>Compensi</h2><table>{righe}</table><table>{tab_somme}</table>
{blocco_imp}
{('<p>' + nota + '</p>') if nota else ''}
<p class="mut">Documento di studio{', non una fattura' if tipo == 'parcella' else ''}. Percentuali indicate dal professionista;
il programma esegue solo le somme mostrate.</p></body></html>"""
