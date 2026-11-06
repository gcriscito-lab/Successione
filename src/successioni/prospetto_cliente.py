"""Prospetto per il cliente: riepilogo leggibile della dichiarazione per gli eredi.

Legge SOLO i byte del file XML generato (gli stessi del file telematico): nessuna regola fiscale nuova. Le somme per
erede sono addizioni dei campi 'QuotaValore' dichiarati (attivo: devoluzioni dei quadri dei beni; passivo: ripartizioni
del quadro ED). L'imposta di successione per erede viene dal calcolo del programma (``telematico.calcolo``), lo stesso che
compila il rigo EF18bis, ed e' mostrata solo se il calcolo e' completato. Non sostituisce la dichiarazione.
"""
from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from html import escape

from lxml import etree

from . import codici as C

NS = "urn:www.agenziaentrate.gov.it:specificheTecniche:sco:suc:v1"
QUADRI_BENI = {"EB": "Terreni", "EC": "Fabbricati", "EL": "Terreni (sistema tavolare)", "EM": "Fabbricati (sistema tavolare)",
               "EN": "Aziende", "EO": "Azioni, obbligazioni, titoli e fondi", "EP": "Aeromobili", "EQ": "Navi e imbarcazioni",
               "ER": "Altri beni e crediti"}


def _ln(e) -> str:
    return etree.QName(e).localname


def _figlio(e, *nomi):
    """Primo discendente con il percorso di nomi locali indicato (ignora il namespace)."""
    cur = [e]
    for n in nomi:
        cur = [c for x in cur for c in x if isinstance(c.tag, str) and _ln(c) == n]
        if not cur:
            return None
    return cur[0]


def _t(e, *nomi) -> str:
    x = _figlio(e, *nomi) if nomi else e
    return (x.text or "").strip() if x is not None else ""


def _num(s: str) -> Decimal | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return Decimal(s.replace(".", "").replace(",", ".")) if "," in s else Decimal(s)
    except Exception:
        return None


def euro(v: Decimal | int | None, *, decimali: bool = True) -> str:
    if v is None:
        return "—"
    q = Decimal(v).quantize(Decimal("0.01") if decimali else Decimal("1"), rounding=ROUND_HALF_UP)
    intero, _, dec = f"{abs(q):.2f}".partition(".") if decimali else (f"{abs(q):.0f}", "", "")
    gruppi = []
    while len(intero) > 3:
        gruppi.insert(0, intero[-3:]); intero = intero[:-3]
    gruppi.insert(0, intero)
    s = ".".join(gruppi) + ("," + dec if decimali else "")
    return ("−" if q < 0 else "") + s + " €"


def _data(s: str) -> str:
    s = (s or "").strip()
    return f"{s[:2]}/{s[2:4]}/{s[4:]}" if len(s) == 8 and s.isdigit() else s


def _etichette(tipo: str) -> dict[str, str]:
    try:
        return {v["valore"]: v["etichetta"] for v in C.voci(tipo)}
    except Exception:
        return {}


def _quota(q) -> str:
    if q is None:
        return ""
    n, d = _t(q, "QuotaElementi", "QuotaNumeratore"), _t(q, "QuotaElementi", "QuotaDenominatore")
    return f"{n}/{d}" if n and d else ""


def _possesso(b) -> str:
    n, d = _t(b, "Possesso", "PossessoNumeratore"), _t(b, "Possesso", "PossessoDenominatore")
    if not (n and d):
        return ""
    nn = _num(n)
    n = str(int(nn)) if nn is not None and nn == nn.to_integral_value() else n
    return f"{n}/{d}"


def _descrizione_bene(q: str, b) -> str:
    for nome in ("Descrizione", "Denominazione", "DescrizioneTitolo", "MarcaModello"):
        t = _t(b, nome)
        if t:
            return t.capitalize() if t.isupper() else t
    parti = []
    luogo = _figlio(b, "Luogo")
    if luogo is not None:
        it = _figlio(luogo, "Italia")
        comune = _t(it, "ComuneAmministrativo") if it is not None else ""
        ind = _t(it, "Indirizzo") if it is not None else ""
        if ind:
            parti.append(ind.title())
        if comune:
            parti.append(comune.title() + (f" ({_t(luogo, 'Provincia')})" if _t(luogo, "Provincia") else ""))
    cat = None
    for e in b.iter():
        if isinstance(e.tag, str) and _ln(e) == "DatiCatastali":
            cat = e
            break
    if cat is not None:
        est = [f"foglio {_t(cat, 'Foglio')}" if _t(cat, "Foglio") else "", f"particella {_t(cat, 'Particella')}" if _t(cat, "Particella") else "",
               f"sub. {_t(cat, 'Subalterno')}" if _t(cat, "Subalterno") else ""]
        parti.append(", ".join(x for x in est if x))
    categoria = next((e.text.strip() for e in b.iter() if isinstance(e.tag, str) and _ln(e) == "CategoriaCatastale" and e.text), "")
    if categoria:
        parti.append("cat. " + (categoria[0] + "/" + categoria[1:] if len(categoria) > 1 and categoria[1:].isdigit() else categoria))
    return ", ".join(p for p in parti if p) or QUADRI_BENI.get(q, q)


def _valore_bene(b) -> Decimal | None:
    for perc in (("Valore",), ("Possesso", "Valore"), ("Possesso", "ValoreEsente")):
        v = _num(_t(b, *perc))
        if v is not None:
            return v
    return None


def leggi(xml: bytes) -> dict:
    """Estrae dal file i dati del prospetto. Tutti gli importi sono quelli scritti nel file."""
    root = etree.fromstring(xml, etree.XMLParser(resolve_entities=False, no_network=True))
    dich = next((e for e in root.iter() if isinstance(e.tag, str) and _ln(e) == "Dichiarazione"), root)
    q = {_ln(e): e for e in dich if isinstance(e.tag, str)}
    fr = q.get("Frontespizio")
    gradi, tipi_sogg = _etichette("GradoParentela_Type"), _etichette("TipoSoggetto_Type")

    # soggetti EA: chiave (modulo, rigo) come nelle devoluzioni
    soggetti: dict[tuple[str, str], dict] = {}
    ea = q.get("QuadroEA")
    if ea is not None:
        for m, mod in enumerate((x for x in ea if _ln(x) == "Modulo"), 1):
            for r, s in enumerate((x for x in mod if _ln(x) == "Soggetto"), 1):
                nome = (_t(s, "DatiAnagrafici", "Cognome") + " " + _t(s, "DatiAnagrafici", "Nome")).strip().title() \
                    or _t(s, "Denominazione").title() or _t(s, "CodiceFiscale")
                soggetti[(str(m), str(r))] = {
                    "nome": nome, "cf": _t(s, "CodiceFiscale"), "grado": gradi.get(_t(s, "GradoParentela"), _t(s, "GradoParentela")),
                    "tipo": tipi_sogg.get(_t(s, "TipoSoggetto"), _t(s, "TipoSoggetto")),
                    "attivo": Decimal(0), "passivo": Decimal(0), "beni": []}

    def chi(ident) -> tuple[str, str]:
        return (_t(ident, "Modulo") or "1", _t(ident, "Rigo") or "1")

    beni = []
    for sig, etichetta in QUADRI_BENI.items():
        qd = q.get("Quadro" + sig)
        if qd is None:
            continue
        prec, continua = None, False
        for mod in (x for x in qd if _ln(x) == "Modulo"):
            for b in (x for x in mod if isinstance(x.tag, str)):
                devs = [d for d in b.iter() if isinstance(d.tag, str) and _ln(d) == "Devoluzione"]
                if continua and prec is not None:
                    bene = prec                         # rigo di continuazione: solo ulteriori devoluzioni
                else:
                    v = _valore_bene(b)
                    if v is None and not devs:
                        continue
                    bene = {"quadro": sig, "gruppo": etichetta, "descrizione": _descrizione_bene(sig, b), "valore": v,
                            "possesso": _possesso(b), "devoluzioni": []}
                    beni.append(bene)
                for d in devs:
                    k = chi(_figlio(d, "IdentificazioneSoggetto"))
                    qv = _num(_t(d, "Quota", "QuotaValore"))
                    bene["devoluzioni"].append({"soggetto": k, "quota": _quota(_figlio(d, "Quota")), "valore": qv})
                    if k in soggetti and qv is not None:
                        soggetti[k]["attivo"] += qv
                        soggetti[k]["beni"].append(bene["descrizione"])
                continua, prec = _t(b, "Continuazione") == "1", bene

    passivita = []
    ed = q.get("QuadroED")
    if ed is not None:
        prec, continua = None, False
        for mod in (x for x in ed if _ln(x) == "Modulo"):
            for p in (x for x in mod if _ln(x) == "Passivita"):
                rip = [d for d in p.iter() if isinstance(d.tag, str) and _ln(d) == "Ripartizione"]
                if continua and prec is not None:
                    voce = prec
                else:
                    t = _t(p, "Descrizione")
                    voce = {"descrizione": (t.capitalize() if t.isupper() else t) or "Passività",
                            "documento": " ".join(x for x in (_t(p, "EstremiDocumento"), _data(_t(p, "DataDocumento"))) if x),
                            "valore": _num(_t(p, "Possesso", "Valore")), "ripartizione": []}
                    passivita.append(voce)
                for d in rip:
                    k = chi(_figlio(d, "IdentificazioneSoggetto"))
                    qv = _num(_t(d, "Quota", "QuotaValore"))
                    voce["ripartizione"].append({"soggetto": k, "quota": _quota(_figlio(d, "Quota")), "valore": qv})
                    if k in soggetti and qv is not None:
                        soggetti[k]["passivo"] += qv
                continua, prec = _t(p, "Continuazione") == "1", voce

    ee = q.get("QuadroEE")
    totali = {k: _num(_t(ee, k)) if ee is not None else None
              for k in ("TotaleAttivo", "TotalePassivo", "TotaleValoreAsseEreditarioNetto")}

    ef = q.get("QuadroEF")
    imposte = []
    if ef is not None:
        for etich, perc in (("Imposta ipotecaria", ("SezioneI_ImpostaIpotecaria", "ImpostaIpotecariaDaVersare")),
                            ("Imposta catastale", ("SezioneII_ImpostaCatastale", "ImpostaCatastaleDaVersare")),
                            ("Tassa ipotecaria", ("SezioneIII_TassaIpotecaria", "Circoscrizioni_Imposta")),
                            ("Imposta di bollo", ("SezioneIV_ImpostaBollo", "Circoscrizioni_Imposta")),
                            ("Tributi speciali per l'attestazione di avvenuta presentazione",
                             ("SezioneV_TributiSpeciali", "CopiaConforme", "CopiaConforme_Importo"))):
            v = _num(_t(ef, *perc))
            if v is not None:
                imposte.append((etich, v))
        vb = _figlio(ef, "SezioneVBis_ImpostaSuccessione")
        isn = None
        if vb is not None:
            if _t(vb, "ImpostaNonDovuta") == "1":
                imposte.append(("Imposta di successione", "non dovuta"))
            else:
                isn = _num(_t(vb, "ImpostaCalcolata", "Imposta"))
                da_v = _num(_t(vb, "ImpostaCalcolata", "ImpostaDaVersare"))
                if isn is not None:
                    imposte.append(("Imposta di successione", isn))
                temp = _t(vb, "ImpostaCalcolata", "TempisticaPagamento")
                if temp == "1" and da_v:
                    imposte.append(("di cui da versare entro 90 giorni (non con la dichiarazione)", da_v))
        tot_ef = _num(_t(ef, "TotaleDaVersare"))
    else:
        tot_ef, isn = None, None
    importo = _num(_t(fr, "ImportoDaVersare")) if fr is not None else None

    defunto = {}
    if fr is not None:
        defunto = {"nome": (_t(fr, "DatiDefunto", "DatiAnagrafici", "Cognome") + " " + _t(fr, "DatiDefunto", "DatiAnagrafici", "Nome")).strip().title(),
                   "cf": _t(fr, "CodiceFiscaleDefunto"), "f": _t(fr, "DatiDefunto", "DatiAnagrafici", "Sesso") == "F", "nascita": _data(_t(fr, "DatiDefunto", "DatiAnagrafici", "DataNascita")),
                   "decesso": _data(_t(fr, "DatiDefunto", "UlterioriDati", "DataDecesso")),
                   "per_legge": _t(fr, "TipoDichiarazione", "Devoluzione", "DevoluzionePerLegge") == "1",
                   "addebito": _figlio(fr, "Versamento") is not None}
    return {"defunto": defunto, "soggetti": soggetti, "beni": beni, "passivita": passivita, "totali": totali,
            "imposte": imposte, "totale_ef": tot_ef, "importo_da_versare": importo, "isn_totale": isn}


def isn_per_erede(xml: bytes) -> tuple[dict[tuple[str, str], Decimal], str | None]:
    """Imposta di successione per beneficiario dal calcolo del programma (candidato senza arrotondamenti intermedi).
    Restituisce anche una nota se il calcolo non e' completato."""
    from .telematico.calcolo import calcola_da_xml
    try:
        r = calcola_da_xml(xml)
    except Exception as e:  # pragma: no cover - difensivo: il prospetto resta utilizzabile
        return {}, f"calcolo non eseguito ({e})"
    if r.stato != "completato":
        return {}, f"ripartizione per erede non disponibile: stato del calcolo «{r.stato}»"
    out = {}
    for b in r.beneficiari:
        mod, _, rigo = b.rigo_ea.partition("/")
        f = Fraction(b.isn_esatta) if "/" in b.isn_esatta else Fraction(Decimal(b.isn_esatta))
        out[(mod or "1", rigo or "1")] = (Decimal(f.numerator) / Decimal(f.denominator)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return out, None


CSS = """
@font-face{font-family:"Atkinson Hyperlegible Next";font-weight:200 800;src:url("/static/atkinson-next-latin.woff2") format("woff2")}
@font-face{font-family:"Atkinson Hyperlegible Mono";font-weight:200 800;src:url("/static/atkinson-mono-latin.woff2") format("woff2")}
:root{--inchiostro:#1F2A2A;--t2:#55615F;--verde:#2F6B57;--casella:#DDEBE3;--sep:rgba(31,42,42,.16);--ocra:#8A560C;--rosso:#B3261E}
*{box-sizing:border-box}
body{margin:0;background:#F6F7F4;color:var(--inchiostro);font:15px/1.5 "Atkinson Hyperlegible Next","Segoe UI",system-ui,sans-serif}
.foglio{max-width:860px;margin:24px auto;background:#fff;padding:40px 48px;box-shadow:0 0 0 1px var(--sep)}
.barra{max-width:860px;margin:16px auto 0;display:flex;gap:10px;justify-content:flex-end}
.barra button{font:inherit;font-weight:700;padding:8px 16px;border-radius:4px;border:0;background:var(--verde);color:#fff;cursor:pointer}
header{display:flex;justify-content:space-between;gap:24px;align-items:flex-start;padding-bottom:18px;border-bottom:2px solid var(--verde)}
.studio{font-weight:700;color:var(--verde)} .data{color:var(--t2);font-size:13px;text-align:right}
h1{font-size:26px;line-height:1.2;margin:18px 0 4px} .sotto{color:var(--t2);margin:0}
h2{font-size:17px;margin:30px 0 10px;color:var(--verde)}
.avviso{margin:18px 0 0;padding:10px 14px;border-left:4px solid var(--ocra);background:#FBF4E8;font-size:14px}
.avviso.rosso{border-color:var(--rosso);background:#FBECEB}
.cifre{display:grid;grid-template-columns:repeat(3,1fr);gap:0;margin-top:20px;border:1px solid var(--sep);border-radius:4px}
.cifre div{padding:12px 16px} .cifre div+div{border-left:1px solid var(--sep)}
.cifre span{display:block;font-size:13px;color:var(--t2)} .cifre b{font-size:20px;font-variant-numeric:tabular-nums}
.cifre .netto{background:var(--casella)}
table{width:100%;border-collapse:collapse;font-size:14px}
th{text-align:left;font-weight:700;font-size:13px;color:var(--t2);border-bottom:1px solid var(--inchiostro);padding:6px 8px}
td{padding:7px 8px;border-bottom:1px solid var(--sep);vertical-align:top}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.mono{font-family:"Atkinson Hyperlegible Mono",Consolas,monospace;font-size:13px;letter-spacing:.03em}
.dett{color:var(--t2);font-size:13px} tr.tot td{font-weight:700;border-top:1px solid var(--inchiostro);border-bottom:0}
.gruppo td{background:#F6F7F4;font-weight:700;font-size:13px}
.erede{display:grid;grid-template-columns:1fr auto;gap:2px 16px;padding:12px 0;border-bottom:1px solid var(--sep)}
.erede .chi b{display:block} .erede .chi span{color:var(--t2);font-size:13px}
.erede dl{margin:0;display:grid;grid-template-columns:auto auto;gap:0 14px;font-size:14px}
.erede dt{color:var(--t2)} .erede dd{margin:0;text-align:right;font-variant-numeric:tabular-nums}
.erede dd.forte{font-weight:700}
footer{margin-top:32px;padding-top:12px;border-top:1px solid var(--sep);font-size:12px;color:var(--t2)}
@media (max-width:640px){.foglio{padding:24px 18px;margin:0}.cifre{grid-template-columns:1fr}.cifre div+div{border-left:0;border-top:1px solid var(--sep)}}
@media print{body{background:#fff}.barra{display:none}.foglio{box-shadow:none;margin:0;max-width:none;padding:0}
 @page{size:A4;margin:16mm 15mm}h2{break-after:avoid}tr,.erede{break-inside:avoid}}
"""


def html(xml: bytes, *, titolo: str, studio: str = "", revisione: int | None = None, completo: bool = True,
         obsoleto: bool = False, oggi: date | None = None) -> str:
    d = leggi(xml)
    isn, nota_isn = isn_per_erede(xml) if d["isn_totale"] else ({}, None)
    oggi = oggi or date.today()
    e = escape
    df = d["defunto"]
    avvisi = []
    if not completo:
        avvisi.append(("rosso", "Bozza: la dichiarazione non è ancora completa. Gli importi possono cambiare."))
    if obsoleto:
        avvisi.append(("rosso", "I dati della pratica sono cambiati dopo l’ultima generazione del file: rigenera il file per aggiornare il prospetto."))
    avvisi.append(("", "Riepilogo informativo preparato dallo studio. Non sostituisce la dichiarazione di successione presentata all’Agenzia delle entrate."))

    t = d["totali"]
    cifre = (f'<div class="cifre"><div><span>Attivo</span><b>{euro(t["TotaleAttivo"], decimali=False)}</b></div>'
             f'<div><span>Passività</span><b>{euro(t["TotalePassivo"], decimali=False)}</b></div>'
             f'<div class="netto"><span>Asse ereditario netto</span><b>{euro(t["TotaleValoreAsseEreditarioNetto"], decimali=False)}</b></div></div>')

    eredi = []
    for k, s in d["soggetti"].items():
        righe = [f'<dt>Beni ricevuti</dt><dd>{euro(s["attivo"])}</dd>']
        if s["passivo"]:
            righe.append(f'<dt>Passività a carico</dt><dd>{euro(-s["passivo"])}</dd>')
            righe.append(f'<dt>Netto</dt><dd class="forte">{euro(s["attivo"] - s["passivo"])}</dd>')
        if k in isn:
            righe.append(f'<dt>Imposta di successione</dt><dd class="forte">{euro(isn[k])}</dd>')
        eredi.append(f'<div class="erede"><div class="chi"><b>{e(s["nome"])}</b><span>{e(s["grado"] or s["tipo"])}, '
                     f'C.F. <span class="mono">{e(s["cf"])}</span></span></div><dl>{"".join(righe)}</dl></div>')

    nomi = {k: s["nome"] for k, s in d["soggetti"].items()}
    righe_beni, gruppo = [], None
    for b in d["beni"]:
        if b["gruppo"] != gruppo:
            gruppo = b["gruppo"]
            righe_beni.append(f'<tr class="gruppo"><td colspan="3">{e(gruppo)}</td></tr>')
        a_chi = ", ".join(f'{e(nomi.get(x["soggetto"], "rigo " + "/".join(x["soggetto"])))} {e(x["quota"])}'
                          + (f' ({euro(x["valore"])})' if x["valore"] is not None else "") for x in b["devoluzioni"])
        poss = f'Il defunto ne possedeva {e(b["possesso"])}. ' if b["possesso"] and b["possesso"] != "1/1" else ""
        dett = poss + (f"Va a: {a_chi}." if a_chi else "")
        righe_beni.append(f'<tr><td>{e(b["descrizione"])}<div class="dett">{dett}</div></td>'
                          f'<td class="n">{euro(b["valore"], decimali=False)}</td></tr>')
    tab_beni = (f'<table><thead><tr><th>Bene e a chi va</th><th class="n">Valore dichiarato</th></tr></thead>'
                f'<tbody>{"".join(righe_beni) or "<tr><td colspan=2>Nessun bene nel file.</td></tr>"}</tbody></table>')

    tab_pass = ""
    if d["passivita"]:
        r = []
        for p in d["passivita"]:
            a_chi = ", ".join(f'{e(nomi.get(x["soggetto"], "rigo " + "/".join(x["soggetto"])))} {e(x["quota"])}' for x in p["ripartizione"])
            doc = f'Documento: {e(p["documento"])}. ' if p["documento"] else ""
            r.append(f'<tr><td>{e(p["descrizione"])}<div class="dett">{doc}{"A carico di: " + a_chi + "." if a_chi else ""}</div></td>'
                     f'<td class="n">{euro(p["valore"], decimali=False)}</td></tr>')
        tab_pass = (f'<h2>Passività</h2><table><thead><tr><th>Voce</th><th class="n">Importo</th></tr></thead>'
                    f'<tbody>{"".join(r)}</tbody></table>')

    r_imp = [f'<tr><td>{e(n)}</td><td class="n">{v if isinstance(v, str) else euro(v, decimali=False)}</td></tr>' for n, v in d["imposte"]]
    if d["importo_da_versare"] is not None:
        modo = "con addebito sul conto indicato in dichiarazione" if df.get("addebito") else "al momento della presentazione"
        r_imp.append(f'<tr class="tot"><td>Totale da versare {modo}</td><td class="n">{euro(d["importo_da_versare"])}</td></tr>')
    tab_imp = (f'<h2>Imposte</h2><table><thead><tr><th>Tributo</th><th class="n">Importo</th></tr></thead><tbody>{"".join(r_imp)}</tbody></table>'
               if r_imp else "")
    nota = ""
    if isn:
        nota = ('<p class="dett">L’imposta di successione per erede è quella calcolata dal programma prima dell’arrotondamento '
                'all’euro del totale; il totale dichiarato è quello della tabella Imposte.</p>')
    elif nota_isn:
        nota = f'<p class="dett">{e(nota_isn.capitalize())}.</p>'

    sotto = ", ".join(x for x in (f'C.F. <span class="mono">{e(df.get("cf", ""))}</span>' if df.get("cf") else "",
                                   f'{"nata" if df.get("f") else "nato"} il {e(df["nascita"])}' if df.get("nascita") else "",
                                   f'{"deceduta" if df.get("f") else "deceduto"} il {e(df["decesso"])}' if df.get("decesso") else "") if x)
    devol = "Successione per legge" if df.get("per_legge") else "Successione testamentaria"
    rev = f", revisione {revisione}" if revisione is not None else ""
    return f"""<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Prospetto per il cliente - {e(titolo)}</title><style>{CSS}</style></head><body>
<div class="barra"><button type="button" onclick="window.print()">Stampa o salva in PDF</button></div>
<main class="foglio">
<header><div class="studio">{e(studio) or "&nbsp;"}</div><div class="data">Prospetto del {oggi.strftime("%d/%m/%Y")}<br>{e(titolo)}{e(rev)}</div></header>
<h1>Successione di {e(df.get("nome") or titolo)}</h1>
<p class="sotto">{sotto}</p><p class="sotto">{devol}</p>
{"".join(f'<p class="avviso {c}">{e(m)}</p>' for c, m in avvisi)}
{cifre}
<h2>Eredi e beneficiari</h2>{"".join(eredi) or "<p>Nessun beneficiario nel file.</p>"}
{nota}
<h2>Beni</h2>{tab_beni}
{tab_pass}
{tab_imp}
<footer>Valori e imposte riportati dal file della dichiarazione generato dal programma. Le quote indicano la parte di ciascun bene
che spetta a ogni erede. Per dubbi rivolgersi allo studio.</footer>
</main></body></html>"""
