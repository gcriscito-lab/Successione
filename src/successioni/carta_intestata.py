"""Carta intestata comune a tutte le stampe dello studio (prospetto per il cliente, preventivo e parcella, brogliaccio,
copertina del fascicolo): stessa testata con i dati dello studio, stessi caratteri e colori, piede con il riferimento della
pratica e «pag. N di M» su ogni pagina.

I dati dello studio vengono da ``impostazioni.intestazione_studio`` (nome, indirizzo, CAP e comune, telefono, email, PEC,
codice fiscale o partita IVA). Finche' quella funzione non c'e', o se i campi sono vuoti, la testata mostra solo il nome dello
studio (``impostazioni.nome_studio``): una stampa senza dati dello studio resta valida.

Solo impaginazione: nessun dato della pratica viene calcolato o modificato qui.
"""
from __future__ import annotations

from datetime import date
from html import escape
from pathlib import Path

CHIAVI_STUDIO = ("nome", "indirizzo", "cap_comune", "telefono", "email", "pec", "cf_piva")


def dati_studio(cartella_dati: Path | str | None = None) -> dict:
    """Le 7 voci dello studio come testi (anche vuoti). Non solleva mai: una configurazione illeggibile da' una testata vuota."""
    from . import impostazioni
    vuoto = {k: "" for k in CHIAVI_STUDIO}
    f = getattr(impostazioni, "intestazione_studio", None)
    try:
        d = f(cartella_dati) if f else {}
    except Exception:
        d = {}
    out = {**vuoto, **{k: str(v or "").strip() for k, v in (d or {}).items() if k in CHIAVI_STUDIO}}
    if not out["nome"]:
        try:
            out["nome"] = (impostazioni.nome_studio(cartella_dati) or "").strip()
        except Exception:
            out["nome"] = ""
    return out


def righe_studio(studio: dict) -> list[str]:
    """Righe di testo della testata, nell'ordine di stampa (le voci vuote si saltano). La prima e' il nome."""
    s = {k: str((studio or {}).get(k) or "").strip() for k in CHIAVI_STUDIO}
    contatti = " – ".join(x for x in (f"Tel. {s['telefono']}" if s["telefono"] else "", s["email"],
                                     f"PEC {s['pec']}" if s["pec"] else "") if x)
    return [x for x in (s["nome"], s["indirizzo"], s["cap_comune"], contatti,
                        f"C.F./P.IVA {s['cf_piva']}" if s["cf_piva"] else "") if x]


CSS = """
@font-face{font-family:"Atkinson Hyperlegible Next";font-weight:200 800;src:url("/static/atkinson-next-latin.woff2") format("woff2")}
@font-face{font-family:"Atkinson Hyperlegible Mono";font-weight:200 800;src:url("/static/atkinson-mono-latin.woff2") format("woff2")}
:root{--inchiostro:#1F2A2A;--t2:#55615F;--verde:#2F6B57;--casella:#DDEBE3;--sep:rgba(31,42,42,.16);--ocra:#8A560C;--rosso:#B3261E;
 --fondo:#F6F7F4}
*{box-sizing:border-box}
body{margin:0;background:var(--fondo);color:var(--inchiostro);font:15px/1.5 "Atkinson Hyperlegible Next","Segoe UI",system-ui,sans-serif}
.foglio{max-width:860px;margin:24px auto;background:#fff;padding:40px 48px;box-shadow:0 0 0 1px var(--sep)}
.foglio.orizzontale{max-width:1240px;padding:32px 36px}
.barra{max-width:860px;margin:16px auto 0;display:flex;gap:10px;justify-content:flex-end}
.barra.larga{max-width:1240px}
.barra button{font:inherit;font-weight:700;padding:8px 16px;border-radius:4px;border:0;background:var(--verde);color:#fff;cursor:pointer}
header.testata{display:flex;justify-content:space-between;gap:24px;align-items:flex-start;padding-bottom:14px;border-bottom:2px solid var(--verde)}
.studio{font-size:12.5px;color:var(--t2);line-height:1.45}
.studio b{display:block;font-size:15px;color:var(--verde)}
.rif{color:var(--t2);font-size:12.5px;text-align:right;line-height:1.45}
.rif b{color:var(--inchiostro)}
h1{font-size:26px;line-height:1.2;margin:18px 0 4px} .sotto{color:var(--t2);margin:0}
h2{font-size:17px;margin:28px 0 10px;color:var(--verde)}
table{width:100%;border-collapse:collapse;font-size:14px}
th{text-align:left;font-weight:700;font-size:13px;color:var(--t2);border-bottom:1px solid var(--inchiostro);padding:6px 8px;vertical-align:bottom}
td{padding:7px 8px;border-bottom:1px solid var(--sep);vertical-align:top}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.mono{font-family:"Atkinson Hyperlegible Mono",Consolas,monospace;font-size:12.5px;letter-spacing:.02em}
.dett,.mut{color:var(--t2);font-size:13px}
tr.tot td{font-weight:700;border-top:1px solid var(--inchiostro);border-bottom:0}
.gruppo td{background:var(--fondo);font-weight:700;font-size:13px}
footer.piede{margin-top:32px;padding-top:12px;border-top:1px solid var(--sep);font-size:12px;color:var(--t2)}
@media (max-width:640px){.foglio{padding:24px 18px;margin:0}}
@media print{
 body{background:#fff}.barra{display:none}
 .foglio,.foglio.orizzontale{box-shadow:none;margin:0;max-width:none;padding:0}
 thead{display:table-header-group} h2{break-after:avoid} tr{break-inside:avoid}
}
"""


def _pagina_css(orizzontale: bool, piede_sx: str) -> str:
    """Formato del foglio e piede di ogni pagina stampata (box di margine di @page: Chrome ed Edge, che aprono il programma)."""
    # testo dentro una stringa CSS in <style>: barra, virgolette, a capo e «<» (nessun «</style>» possibile) in escape CSS
    testo = (piede_sx.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", " ")
             .replace("<", "\\3c ").replace(">", "\\3e "))
    return ("@page{size:A4" + (" landscape" if orizzontale else "") + ";margin:14mm 14mm 16mm"
            + ";@bottom-left{content:\"" + testo + "\";font:9px system-ui,sans-serif;color:#55615F}"
            + ";@bottom-right{content:\"pag. \" counter(page) \" di \" counter(pages);font:9px system-ui,sans-serif;color:#55615F}}")


def testata(studio: dict, riferimento: list[str]) -> str:
    """Testata della prima pagina: dati dello studio a sinistra, riferimento del documento a destra (la prima riga in grassetto)."""
    righe = righe_studio(studio)
    sx = (f"<b>{escape(righe[0])}</b>" + "".join(f"{escape(r)}<br>" for r in righe[1:])) if righe else "&nbsp;"
    dx = "<br>".join((f"<b>{escape(r)}</b>" if i == 0 else escape(r)) for i, r in enumerate(x for x in riferimento if x))
    return f'<header class="testata"><div class="studio">{sx}</div><div class="rif">{dx}</div></header>'


def pagina(*, titolo_finestra: str, studio: dict, riferimento: list[str], corpo: str, piede: str = "",
           orizzontale: bool = False, css_extra: str = "", lang: str = "it") -> str:
    """Documento HTML completo su carta intestata, con il pulsante «Stampa o salva in PDF» (nascosto in stampa)."""
    nome = (studio or {}).get("nome") or ""
    piede_pagina = " – ".join(x for x in (nome, titolo_finestra) if x)
    cls = "foglio orizzontale" if orizzontale else "foglio"
    barra = f'<div class="barra{" larga" if orizzontale else ""}"><button type="button" onclick="window.print()">Stampa o salva in PDF</button></div>'
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{escape(titolo_finestra)}</title><style>{CSS}{_pagina_css(orizzontale, piede_pagina)}{css_extra}</style></head><body>"
            f'{barra}<main class="{cls}">{testata(studio, riferimento)}{corpo}'
            + (f'<footer class="piede">{piede}</footer>' if piede else "") + "</main></body></html>")


def data_it(d: date | None = None) -> str:
    return (d or date.today()).strftime("%d/%m/%Y")


def accenti(testo: str) -> str:
    """«Proprieta'» -> «Proprietà»: vocale finale con l'apostrofo (forma delle tabelle ufficiali dei codici) -> vocale accentata.
    Solo in fine di parola; un apostrofo di elisione («dell'erede») resta."""
    import re
    mappa = {"a": "à", "e": "è", "i": "ì", "o": "ò", "u": "ù", "A": "À", "E": "È", "I": "Ì", "O": "Ò", "U": "Ù"}
    return re.sub(r"([aeiouAEIOU])'(?=$|[\s,.;:)\]])", lambda m: mappa[m.group(1)], testo or "")
