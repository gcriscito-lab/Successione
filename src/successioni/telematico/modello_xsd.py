"""Lettura del modello di contenuto degli XSD SUC13 (ordine, namespace, tipi) e serializzatore guidato dallo schema.

Il serializzatore riceve dati annidati con i NOMI LOCALI degli elementi XSD e produce l'XML con namespace e
ordine di sequenza ricavati dagli XSD effettivi (nessun ordine/namespace scritto a mano). Chiavi non previste
dal tipo -> ``ErroreModello`` (nessuna perdita silenziosa). Gli attributi si indicano con prefisso ``@``.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from lxml import etree

from . import fonti

_XS = "http://www.w3.org/2001/XMLSchema"


def _q(t: str) -> str:
    return f"{{{_XS}}}{t}"


class ErroreModello(ValueError):
    """Dato non rappresentabile nello schema (chiave sconosciuta, tipo atteso diverso)."""


@dataclass(frozen=True)
class CT:
    """complexType (con documento di origine per risolvere prefissi e namespace)."""
    nodo: etree._Element
    tns: str
    nsmap: tuple  # coppie (prefisso, uri)

    def risolvi(self, qname: str) -> tuple[str, str]:
        pref, _, nome = qname.rpartition(":")
        return dict(self.nsmap).get(pref or None, ""), nome


@dataclass(frozen=True)
class Figlio:
    nome: str
    ns: str
    min: int
    max: int | None  # None = unbounded
    ct: CT | None  # None se tipo semplice


class Modello:
    def __init__(self):
        self.ct: dict[tuple[str, str], CT] = {}
        self.el: dict[tuple[str, str], tuple[etree._Element, CT]] = {}
        self._visti: set = set()
        self._carica(fonti.xsd_principale())

    def _carica(self, p):
        p = p.resolve()
        if p in self._visti:
            return
        self._visti.add(p)
        radice = etree.parse(str(p), parser=etree.XMLParser(resolve_entities=False, no_network=True)).getroot()
        tns = radice.get("targetNamespace", "")
        nsmap = tuple((k, v) for k, v in radice.nsmap.items())
        for c in radice:
            if c.tag == _q("complexType"):
                self.ct[(tns, c.get("name"))] = CT(c, tns, nsmap)
            elif c.tag == _q("element") and c.get("name"):
                self.el[(tns, c.get("name"))] = (c, CT(c, tns, nsmap))
            elif c.tag in (_q("import"), _q("include")) and c.get("schemaLocation"):
                self._carica(p.parent / c.get("schemaLocation"))

    # ----------------------------------------------------------------- contenuto
    def _ct_di_elemento(self, e, ctx: CT) -> CT | None:
        t = e.get("type")
        if t:
            ns, nome = ctx.risolvi(t)
            return self.ct.get((ns, nome))
        anon = e.find(_q("complexType"))
        return CT(anon, ctx.tns, ctx.nsmap) if anon is not None else None

    def figli(self, ct: CT) -> list[Figlio]:
        out: list[Figlio] = []

        def percorri(cont, ctx: CT):
            for c in cont:
                if c.tag == _q("element"):
                    if c.get("ref"):
                        ns, nome = ctx.risolvi(c.get("ref"))
                        e, ctx2 = self.el[(ns, nome)]
                        out.append(Figlio(nome, ns, int(c.get("minOccurs", 1)), _max(c), self._ct_di_elemento(e, ctx2)))
                    else:
                        out.append(Figlio(c.get("name"), ctx.tns, int(c.get("minOccurs", 1)), _max(c),
                                          self._ct_di_elemento(c, ctx)))
                elif c.tag in (_q("sequence"), _q("choice"), _q("all")):
                    percorri(c, ctx)

        def _max(c):
            m = c.get("maxOccurs", "1")
            return None if m == "unbounded" else int(m)

        def corpo(ctx: CT):
            cc = ctx.nodo.find(_q("complexContent"))
            if cc is not None:
                est = cc.find(_q("extension"))
                if est is not None:
                    ns, nome = ctx.risolvi(est.get("base"))
                    if (ns, nome) in self.ct:
                        out.extend(self.figli(self.ct[(ns, nome)]))
                    percorri(est, ctx)
                return
            percorri(ctx.nodo, ctx)

        corpo(ct)
        return out

    def attributi(self, ct: CT) -> dict[str, bool]:
        """nome attributo -> obbligatorio (anche ereditati)."""
        out: dict[str, bool] = {}
        cc = ct.nodo.find(_q("complexContent"))
        nodo = ct.nodo
        if cc is not None:
            est = cc.find(_q("extension"))
            if est is not None:
                ns, nome = ct.risolvi(est.get("base"))
                if (ns, nome) in self.ct:
                    out.update(self.attributi(self.ct[(ns, nome)]))
                nodo = est
        for a in nodo.findall(_q("attribute")):
            out[a.get("name")] = a.get("use") == "required"
        return out


@lru_cache(maxsize=1)
def modello() -> Modello:
    return Modello()


def radice_suc() -> CT:
    """Tipo della dichiarazione (suc:Dichiarazione_SUC_Type)."""
    from .fonti import NS_SUC
    return modello().ct[(NS_SUC, "Dichiarazione_SUC_Type")]


def costruisci(parent: etree._Element, ct: CT, dati: dict, percorso: str = "") -> None:
    """Aggiunge a ``parent`` i figli di ``ct`` secondo l'ordine XSD, leggendo i valori da ``dati``."""
    m = modello()
    figli = m.figli(ct)
    attr = m.attributi(ct)
    noti = {f.nome for f in figli} | {f"@{a}" for a in attr}
    sconosciute = [k for k in dati if k not in noti]
    if sconosciute:
        raise ErroreModello(f"{percorso or '/'}: elementi non previsti dal tipo XSD: {sconosciute}; ammessi: {sorted(noti)}")
    for a, obbl in attr.items():
        if f"@{a}" in dati:
            parent.set(a, str(dati[f"@{a}"]))
        elif obbl:
            raise ErroreModello(f"{percorso or '/'}: attributo obbligatorio @{a} mancante")
    for f in figli:
        if f.nome not in dati:
            continue
        v = dati[f.nome]
        valori = v if isinstance(v, list) else [v]
        if f.max is not None and len(valori) > f.max:
            raise ErroreModello(f"{percorso}/{f.nome}: {len(valori)} occorrenze, massimo {f.max}")
        for i, val in enumerate(valori, 1):
            e = etree.SubElement(parent, f"{{{f.ns}}}{f.nome}")
            p = f"{percorso}/{f.nome}" + (f"[{i}]" if len(valori) > 1 else "")
            if f.ct is None:
                if isinstance(val, dict):
                    raise ErroreModello(f"{p}: elemento semplice, atteso testo")
                e.text = str(val)
            else:
                if not isinstance(val, dict):
                    raise ErroreModello(f"{p}: elemento complesso, atteso dict")
                costruisci(e, f.ct, val, p)
