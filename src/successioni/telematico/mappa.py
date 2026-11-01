"""Generatore della mappa documentale degli XSD SUC13 (albero degli elementi, occorrenze, tipi, annotazioni,
enumerazioni). Uso::

    python -m successioni.telematico.mappa > docs/regole/mappa_xsd_albero.md

Il testo e' ricavato solo dagli XSD in fonti/ (nessun contenuto scritto a mano), quindi e' rigenerabile quando
cambiano le specifiche. Le annotazioni sono riportate integralmente: contengono regole applicative che la
validazione di schema NON esegue (vedi docs/regole/mappa_xsd.md, sezione "Regole dalle annotazioni").
"""
from __future__ import annotations

import sys
from lxml import etree

from . import fonti
from . import xsd as X

XS = "http://www.w3.org/2001/XMLSchema"
PFX = {fonti.NS_SUC: "suc", fonti.NS_CM: "cm", fonti.NS_SC: "sc", fonti.NS_REG: "reg", fonti.NS_TM: "tm", XS: "xs"}

ENUM_DOCUMENTATE = [
    "CodiciCarica_Type", "StatoCivile_Type", "Sesso_Type", "TipoSoggetto_Type", "GradoParentela_Type",
    "GradoParentela2_Type", "CodiciDirittoImmobili_Type", "CodiciDiritto_Type", "CodiciDirittoNonImmobili",
    "CodiciDirittoNonImmobiliDevoluzione", "CodiciNatura_Type", "TerrenoEdificabile_Type",
    "CodiciCategoriaCatastale_Type", "TipoCespite_Type", "CodiciPassivita_Type", "CodiciAgevolazioni_Type",
    "CodiciRiduzioni25comma1_Type", "DirittoAbitazione_Type", "DichiarazioneSostitutiva_Type",
    "ImpegnoPresentazione_Type", "TempisticaPagamento_Type",
]


def _q(t):
    return f"{{{XS}}}{t}"


class _Albero:
    def __init__(self):
        self.ct, self.el = {}, {}
        self.docs = {}
        self._carica(fonti.xsd_principale())

    def _carica(self, p):
        p = p.resolve()
        if p in self.docs:
            return
        d = etree.parse(str(p), parser=etree.XMLParser(resolve_entities=False, no_network=True)).getroot()
        self.docs[p] = d
        tns = d.get("targetNamespace", "")
        for c in d:
            if c.tag == _q("complexType"):
                self.ct[(tns, c.get("name"))] = (c, d)
            elif c.tag == _q("element") and c.get("name"):
                self.el[(tns, c.get("name"))] = (c, d)
        for c in d:
            if c.tag in (_q("import"), _q("include")):
                self._carica(p.parent / c.get("schemaLocation"))

    @staticmethod
    def _res(qn, d):
        pre, _, n = qn.rpartition(":")
        return d.nsmap.get(pre or None, ""), n

    def _nome(self, qn, d):
        ns, n = self._res(qn, d)
        return f"{PFX.get(ns, ns)}:{n}"

    @staticmethod
    def _doc(e):
        a = e.find(_q("annotation"))
        if a is None:
            return ""
        return " ".join(" ".join((x.text or "") for x in a.findall(_q("documentation"))).split())

    @staticmethod
    def _occ(e):
        mi, ma = e.get("minOccurs", "1"), e.get("maxOccurs", "1")
        return f"{mi}..{'n' if ma == 'unbounded' else ma}"

    def righe(self, e, d, liv, out):
        if e.get("ref"):
            ns, n = self._res(e.get("ref"), d)
            corpo, dd = self.el[(ns, n)]
            nome, tipo = n, corpo.get("type")
        else:
            corpo, dd, nome, tipo = e, d, e.get("name"), e.get("type")
        doc = self._doc(e) or self._doc(corpo)
        ind = "  " * liv
        if tipo and self._res(tipo, dd) in self.ct:
            out.append(f"{ind}- **{nome}** `[{self._occ(e)}]` : `{self._nome(tipo, dd)}`" + (f" — {doc}" if doc else ""))
            c, cd = self.ct[self._res(tipo, dd)]
            self.ct_righe(c, cd, liv + 1, out)
        elif tipo:
            out.append(f"{ind}- {nome} `[{self._occ(e)}]` : `{self._nome(tipo, dd)}`" + (f" — {doc}" if doc else ""))
        else:
            anon, sanon = corpo.find(_q("complexType")), corpo.find(_q("simpleType"))
            if anon is not None:
                out.append(f"{ind}- **{nome}** `[{self._occ(e)}]`" + (f" — {doc}" if doc else ""))
                self.ct_righe(anon, dd, liv + 1, out)
            else:
                r = sanon.find(_q("restriction")) if sanon is not None else None
                base = self._nome(r.get("base"), dd) if r is not None else "?"
                fac = {c.tag.split("}")[1]: c.get("value") for c in r if c.tag != _q("annotation")} if r is not None else {}
                en = [c.get("value") for c in r.findall(_q("enumeration"))] if r is not None else []
                fac = {k: v for k, v in fac.items() if k != "enumeration"}
                extra = (f" {fac}" if fac else "") + (f" valori {en}" if en else "")
                out.append(f"{ind}- {nome} `[{self._occ(e)}]` : `{base}`{extra}" + (f" — {doc}" if doc else ""))

    def ct_righe(self, node, d, liv, out):
        cc = node.find(_q("complexContent"))
        if cc is not None:
            ext = cc.find(_q("extension"))
            restr = ext is None
            if restr:
                ext = cc.find(_q("restriction"))
            key = self._res(ext.get("base"), d)
            out.append("  " * liv + f"- _({'restrizione' if restr else 'estensione'} di `{self._nome(ext.get('base'), d)}`)_")
            if key in self.ct and not restr:
                c, cd = self.ct[key]
                self.ct_righe(c, cd, liv, out)
            self.gruppo(ext, d, liv, out)
            return
        self.gruppo(node, d, liv, out)

    def gruppo(self, node, d, liv, out):
        in_scelta = node.tag == _q("choice")
        for c in node:
            if c.tag == _q("choice"):
                out.append("  " * liv + f"- _scelta `[{self._occ(c)}]` fra:_")
                self.gruppo(c, d, liv + 1, out)
            elif c.tag in (_q("sequence"), _q("all")):
                if c.get("minOccurs") or c.get("maxOccurs") or in_scelta:
                    out.append("  " * liv + f"- _sequenza `[{self._occ(c)}]`:_")
                    self.gruppo(c, d, liv + 1, out)
                else:
                    self.gruppo(c, d, liv, out)
            elif c.tag == _q("element"):
                self.righe(c, d, liv, out)
            elif c.tag == _q("attribute"):
                out.append("  " * liv + f"- @{c.get('name')} : `{c.get('type') or 'anonimo'}` uso {c.get('use', 'optional')}")


def genera(quadri: tuple[str, ...] = ("Frontespizio", "QuadroEA", "QuadroEB", "QuadroEC", "QuadroED", "QuadroEE",
                                       "QuadroER", "QuadroEF", "QuadroEG", "QuadroEH")) -> str:
    a = _Albero()
    out = [f"# Albero XSD SUC13 (generato) — {fonti.FONTE_XSD}", "",
           "Generato da `python -m successioni.telematico.mappa` a partire dagli XSD in `fonti/`. Non modificare a mano.",
           "Notazione: `[min..max]` occorrenze; **grassetto** = elemento complesso; testo dopo — = annotazione XSD "
           "integrale (regole applicative NON eseguite dalla validazione di schema).", ""]
    el, d = a.el[(fonti.NS_SUC, "Fornitura")]
    righe: list[str] = []
    a.righe(el, d, 0, righe)
    # separa per quadro di primo livello della Dichiarazione
    blocco, corrente = {}, None
    for r in righe:
        s = r.lstrip()
        liv = (len(r) - len(s)) // 2
        if liv == 2 and s.startswith("- **"):
            corrente = s[4:].split("**")[0]
        elif liv <= 1:
            corrente = "_busta"
        blocco.setdefault(corrente, []).append(r)
    def dedent(rr):  # evita che il Markdown interpreti l'indentazione iniziale come blocco di codice
        base = min(len(r) - len(r.lstrip()) for r in rr)
        return [r[base:] for r in rr]

    out += ["## Busta e intestazione", ""] + dedent(blocco.get("_busta", [])) + [""]
    for q in quadri:
        if q in blocco:
            out += [f"## {q}", ""] + dedent(blocco[q]) + [""]
    altri = [k for k in blocco if k not in quadri and k != "_busta"]
    out += ["## Altri quadri (non nel perimetro: solo struttura di primo livello)", ""]
    for k in altri:
        out.append(blocco[k][0].strip())
    out += ["", "## Enumerazioni dei codici", ""]
    for t in ENUM_DOCUMENTATE:
        en = X.enumerazioni(t)
        out += [f"### {t} ({len(en)} valori)", "", "| codice | descrizione (documentazione XSD) |", "|---|---|"]
        out += [f"| `{k}` | {v.replace('|', '/')} |" for k, v in en.items()] + [""]
    return "\n".join(out) + "\n"


if __name__ == "__main__":  # pragma: no cover
    sys.stdout.write(genera())
