"""Validazione XSD della fornitura SUC13 e lettura delle enumerazioni dagli XSD ufficiali.

La validazione di schema NON equivale al controllo ufficiale dell'Agenzia: le annotazioni degli XSD
contengono regole applicative che lo schema non esegue (vedi docs/regole/mappa_xsd.md).
"""
from __future__ import annotations

import re
from functools import lru_cache

from lxml import etree

from ..schema import Errore
from . import fonti

_XS = "http://www.w3.org/2001/XMLSchema"


def _parser() -> etree.XMLParser:
    return etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False)


@lru_cache(maxsize=1)
def schema() -> etree.XMLSchema:
    """Schema compilato (XSD principale + import), letto da fonti/ in sola lettura."""
    return etree.XMLSchema(etree.parse(str(fonti.xsd_principale()), parser=_parser()))


# ------------------------------------------------------------------ indice dei tipi
@lru_cache(maxsize=1)
def _indice() -> dict:
    """Indicizza simpleType e dichiarazioni di elemento di tutti gli XSD collegati."""
    radice = fonti.cartella_xsd()
    tipi: dict[tuple[str, str], etree._Element] = {}
    elementi: dict[str, set[str]] = {}
    visti: set = set()

    def carica(p):
        p = p.resolve()
        if p in visti:
            return
        visti.add(p)
        doc = etree.parse(str(p), parser=_parser()).getroot()
        tns = doc.get("targetNamespace", "")
        for c in doc:
            if c.tag == f"{{{_XS}}}simpleType":
                tipi[(tns, c.get("name"))] = (c, doc.nsmap)
        for e in doc.iter(f"{{{_XS}}}element"):
            if e.get("name") and e.get("type"):
                elementi.setdefault(e.get("name"), set()).add(e.get("type"))
        for c in doc:
            if c.tag in (f"{{{_XS}}}import", f"{{{_XS}}}include") and c.get("schemaLocation"):
                carica(p.parent / c.get("schemaLocation"))

    carica(fonti.xsd_principale())
    assert radice.exists()
    return {"tipi": tipi, "elementi": elementi}


def _doc(e) -> str:
    a = e.find(f"{{{_XS}}}annotation")
    d = a.find(f"{{{_XS}}}documentation") if a is not None else None
    return " ".join((d.text or "").split()) if d is not None else ""


def _risolvi(qname: str, nsmap: dict) -> tuple[str, str]:
    pref, _, nome = qname.rpartition(":")
    return nsmap.get(pref or None, ""), nome


def enumerazioni(tipo: str, namespace: str | None = None) -> dict[str, str]:
    """Valori ammessi (codice -> descrizione) di un simpleType a enumerazione, risolvendo union/derivazioni.

    ``tipo`` e' il nome del tipo nello XSD (es. ``CodiciDirittoImmobili_Type``); se il nome esiste in piu'
    namespace va indicato ``namespace``. Restituisce ``{}`` se il tipo non ha enumerazioni (solo pattern).
    """
    idx = _indice()["tipi"]
    cand = [(k, v) for k, v in idx.items() if k[1] == tipo and (namespace is None or k[0] == namespace)]
    if not cand:
        raise KeyError(f"tipo XSD sconosciuto: {tipo}")
    out: dict[str, str] = {}

    def espandi(el, nsmap):
        for r in el.findall(f"{{{_XS}}}restriction"):
            base = r.get("base")
            enums = r.findall(f"{{{_XS}}}enumeration")
            for en in enums:
                out[en.get("value")] = _doc(en)
            if not enums and base and not base.startswith("xs:"):
                ns, nm = _risolvi(base, nsmap)
                if (ns, nm) in idx:
                    espandi(*idx[(ns, nm)])
        for u in el.findall(f"{{{_XS}}}union"):
            for m in (u.get("memberTypes") or "").split():
                ns, nm = _risolvi(m, nsmap)
                if (ns, nm) in idx:
                    espandi(*idx[(ns, nm)])

    for _, (el, nsmap) in cand[:1]:
        espandi(el, nsmap)
    return out


def descrizione_tipo(nome_elemento: str) -> str | None:
    """Documentazione del tipo XSD associato a un elemento, se univoca (usata nei messaggi d'errore)."""
    ts = _indice()["elementi"].get(nome_elemento)
    if not ts or len(ts) != 1:
        return None
    t = next(iter(ts))
    nome = t.split(":")[-1]
    for (ns, n), (el, _) in _indice()["tipi"].items():
        if n == nome:
            d = _doc(el)
            return f"{t}: {d}" if d else t
    return t


# ------------------------------------------------------------------ validazione
_CODICI = {
    "SCHEMAV_CVC_PATTERN_VALID": "XSD_FORMATO",
    "SCHEMAV_CVC_ENUMERATION_VALID": "XSD_VALORE_NON_AMMESSO",
    "SCHEMAV_CVC_DATATYPE_VALID_1_2_1": "XSD_TIPO_DATO",
    "SCHEMAV_CVC_DATATYPE_VALID_1_2_3": "XSD_TIPO_DATO",
    "SCHEMAV_CVC_LENGTH_VALID": "XSD_LUNGHEZZA",
    "SCHEMAV_CVC_MINLENGTH_VALID": "XSD_LUNGHEZZA",
    "SCHEMAV_CVC_MAXLENGTH_VALID": "XSD_LUNGHEZZA",
    "SCHEMAV_ELEMENT_CONTENT": "XSD_STRUTTURA",
    "SCHEMAV_CVC_ELT_1": "XSD_ELEMENTO_RADICE",
    "SCHEMAV_CVC_COMPLEX_TYPE_4": "XSD_ATTRIBUTO_MANCANTE",
    "SCHEMAV_CVC_COMPLEX_TYPE_3_2_1": "XSD_ATTRIBUTO_NON_AMMESSO",
}
_NS = re.compile(r"\{[^}]*\}")


def _pulisci(s: str) -> str:
    return _NS.sub("", s)


def _legge(e) -> tuple[str, str, str]:
    """(codice, messaggio leggibile, nome elemento) da un errore lxml."""
    msg = e.message or ""
    nome = (re.search(r"Element '(?:\{[^}]*\})?([^']+)'", msg) or re.search(r"Attribute '([^']+)'", msg))
    nome = nome.group(1) if nome else ""
    cod = _CODICI.get(e.type_name, "XSD_ALTRO")
    m = re.search(r"\[facet 'pattern'\] The value '(.*)' is not accepted by the pattern '(.*)'", msg, re.S)
    if m:
        return "XSD_FORMATO", (f"valore {m.group(1)!r} non valido per <{nome}>: non rispetta il formato dello "
                               f"schema (espressione ammessa: {m.group(2)})"), nome
    m = re.search(r"Missing child element\(s\)\. Expected is (?:one of )?\( (.*?) \)", msg)
    if m:
        return "XSD_ELEMENTO_MANCANTE", (f"elemento obbligatorio mancante in <{nome}>: atteso {_pulisci(m.group(1))}"), nome
    m = re.search(r"This element is not expected(?:\. Expected is (?:one of )?\( (.*?) \))?", msg)
    if m:
        atteso = f"; atteso: {_pulisci(m.group(1))}" if m.group(1) else ""
        return "XSD_ELEMENTO_NON_ATTESO", (f"elemento <{nome}> non atteso in questa posizione (ordine della "
                                           f"sequenza o elemento non previsto){atteso}"), nome
    m = re.search(r"\[facet 'enumeration'\] The value '(.*)' is not an element of the set \{(.*)\}", msg)
    if m:
        return "XSD_VALORE_NON_AMMESSO", (f"valore {m.group(1)!r} non ammesso per <{nome}>; valori ammessi: "
                                          f"{_pulisci(m.group(2))}"), nome
    m = re.search(r"'(.*)' is not a valid value of the (?:union|atomic|local union|local atomic) type '([^']*)'", msg)
    if m:
        tipo = _pulisci(m.group(2))
        try:
            ammessi = ", ".join(enumerazioni(tipo)) if tipo else ""
        except KeyError:
            ammessi = ""
        return "XSD_VALORE_NON_AMMESSO", (f"valore {m.group(1)!r} non ammesso per <{nome}> (tipo {tipo or 'locale'})"
                                          + (f"; valori ammessi: {ammessi}" if ammessi else "")), nome
    m = re.search(r"\[facet '(maxLength|minLength|length)'\] The value has a length of '(\d+)'; this (?:exceeds|underruns|"
                  r"differs from) the allowed (?:maximum |minimum )?length of '(\d+)'", msg)
    if m:
        return "XSD_LUNGHEZZA", f"<{nome}>: lunghezza {m.group(2)}, ammessa {m.group(1)} {m.group(3)}", nome
    testo = _pulisci(msg.split(": ", 1)[-1] if msg.startswith("Element") else msg)
    return cod, (f"<{nome}>: {testo}" if nome else testo), nome


def valida_xsd(xml: bytes) -> list[Errore]:
    """Valida ``xml`` (bytes) sullo schema SUC13 ufficiale. Lista vuota = conforme allo schema.

    Ogni errore riporta il percorso XPath dell'elemento (con prefissi tm:/suc:) e la fonte
    (XSD + versione + elemento). Non esegue le regole applicative delle annotazioni.
    """
    if isinstance(xml, str):
        xml = xml.encode("utf-8")
    try:
        doc = etree.fromstring(xml, parser=_parser())
    except etree.XMLSyntaxError as e:
        return [Errore("XML_NON_BEN_FORMATO", f"riga {e.lineno}", f"XML non ben formato: {e.msg}",
                       "XML 1.0; " + fonti.DOC_SPEC + " p.6 §2.1")]
    err: list[Errore] = []
    codifica = (doc.getroottree().docinfo.encoding or "").upper()
    if codifica and codifica not in ("UTF-8", "UTF8"):
        err.append(Errore("XML_CODIFICA", "/", f"codifica dichiarata {codifica}: la fornitura deve essere UTF-8",
                          fonti.DOC_SPEC + " p.6 §2.1"))
    s = schema()
    if not s.validate(doc):
        for e in s.error_log:
            cod, msg, nome = _legge(e)
            tipo = descrizione_tipo(nome) if nome else None
            fonte = fonti.fonte_xsd(nome or None) + (f" [{tipo}]" if tipo else "")
            err.append(Errore(cod, e.path or f"riga {e.line}", f"{msg} (riga {e.line})", fonte))
    return err
