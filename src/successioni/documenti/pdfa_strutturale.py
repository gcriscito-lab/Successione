"""Verificatore STRUTTURALE e PRUDENTE per PDF/A-1 (livello b e, in parte, a).

NON e' un validatore PDF/A. L'esito puo' essere soltanto:

* ``indicativo_ok``  - nessuna delle violazioni controllate e' stata trovata (NON significa conforme);
* ``indicativo_ko``  - almeno una violazione (o il file non e' leggibile) - il file non va presentato come PDF/A.

Non emette mai "conforme": solo un validatore indipendente (veraPDF, vedi ``successioni.pdfa.valida_pdfa`` e
``docs/PDFA.md``) puo' accertarlo. Ogni risposta riporta l'elenco dei controlli eseguiti e di quelli NON eseguiti.

Origine dell'elenco di regole: la norma ISO 19005-1:2005 non e' presente in ``fonti/``. Le clausole citate sono
quelle della tabella pubblica delle regole PDF/A-1 di veraPDF ("PDFA Part 1 rules", wiki del repository
veraPDF-validation-profiles, consultata il 2026-11-01), che riporta per ogni regola la clausola ISO 19005-1.
Le regole contrassegnate "prudenziale" sono scelte di cautela del progetto, non requisiti accertati.
"""
from __future__ import annotations

import re
from pathlib import Path

from lxml import etree
from pypdf import PdfReader
from pypdf.errors import PyPdfError
from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject, StreamObject

NS_PDFAID = "http://www.aiim.org/pdfa/ns/id/"

FONTE_REGOLE = ("ISO 19005-1:2005 (clausole come da tabella veraPDF 'PDFA Part 1 rules'); "
                "norma non presente in fonti/, elenco indicativo e non esaustivo")

CONTROLLI_ESEGUITI = {
    "PDFA_LEGGIBILITA": "file leggibile e non troncato (6.1)",
    "PDFA_HEADER": "intestazione %PDF-1.n all'offset 0 (6.1.2-1)",
    "PDFA_HEADER_BINARIO": "commento binario con >=4 byte >127 dopo l'intestazione (6.1.2-2)",
    "PDFA_TRAILER_ID": "chiave ID nel trailer (6.1.3-1)",
    "PDFA_CIFRATURA": "assenza di Encrypt (6.1.3-2)",
    "PDFA_DOPO_EOF": "nulla dopo l'ultimo %%EOF salvo un fine riga (6.1.3-3)",
    "PDFA_XREF_STREAM": "assenza di xref stream e object stream (6.1.4-3)",
    "PDFA_LZW": "assenza del filtro LZWDecode (6.1.10)",
    "PDFA_RIF_ESTERNO": "stream senza F/FFilter/FDecodeParms - riferimenti esterni (6.1.7-3)",
    "PDFA_FILE_INCORPORATI": "assenza di EmbeddedFiles e di EF nelle specifiche di file (6.1.11)",
    "PDFA_OPTIONAL_CONTENT": "assenza di OCProperties (6.1.13)",
    "PDFA_METADATA": "stream Metadata XMP nel catalogo, senza Filter (6.7.2)",
    "PDFA_XMP_FORMA": "XMP ben formato; intestazione xpacket senza bytes/encoding (6.7.5, 6.7.9)",
    "PDFA_XMP_PDFAID": "pdfaid:part=1 e pdfaid:conformance coerente col livello (6.7.11)",
    "PDFA_OUTPUTINTENT": "OutputIntent GTS_PDFA1 con DestOutputProfile (6.2.2-1) - prudenziale: sempre richiesto",
    "PDFA_ICC": "profilo ICC incorporato: intestazione 'acsp', dimensione, spazio colore coerente con N (6.2.2, 6.2.3.2)",
    "PDFA_COLORE_VS_INTENT": "spazi device nelle immagini/risorse compatibili con l'OutputIntent (6.2.3.3)",
    "PDFA_FONT": "tutti i font (anche i 14 standard) con programma incorporato; Type3 escluso (6.3.4-1)",
    "PDFA_TRASPARENZA": "nessuna SMask, BM diverso da Normal, CA/ca diversi da 1, gruppo di trasparenza (6.4)",
    "PDFA_AZIONI": "nessuna azione Launch/Sound/Movie/ResetForm/ImportData/JavaScript/Hide/SetState/NoOp; "
                   "Named solo NextPage/PrevPage/FirstPage/LastPage; nessun AA su catalogo/campi (6.6.1, 6.6.2)",
    "PDFA_JAVASCRIPT": "nessun JavaScript (chiave JS, Names/JavaScript) (6.6.1-1)",
    "PDFA_ANNOTAZIONI": "annotazioni senza Sound/Movie/FileAttachment; flag Print e non Hidden/Invisible/NoView; "
                        "AP con solo N (6.5.2, 6.5.3)",
    "PDFA_MULTIMEDIA": "nessuna annotazione Screen/3D/RichMedia - prudenziale (tipi non definiti in PDF 1.4)",
    "PDFA_FORM": "NeedAppearances assente o false; ogni widget con AP (6.9)",
    "PDFA_IMMAGINI": "niente Alternates, OPI, Interpolate true, XObject PS/Ref (6.2.4, 6.2.5, 6.2.6, 6.2.7)",
    "PDFA_1A_STRUTTURA": "solo livello 1a: MarkInfo/Marked e StructTreeRoot (6.8.2.2-1, 6.8.3.3-1)",
}

CONTROLLI_NON_ESEGUITI = [
    "operatori e colori nei content stream; testo in modalita' di rendering invisibile (6.2.10, 6.3.4-1)",
    "presenza nel font incorporato di tutti i glifi usati; coerenza Widths; CIDSet/CharSet (6.3.5, 6.3.6)",
    "codifica dei font TrueType simbolici e non simbolici; CMap non Identity (6.3.3, 6.3.7)",
    "corrispondenza fra dizionario Info e proprieta' XMP (6.7.3)",
    "schemi di estensione XMP e conformita' dei tipi delle proprieta' (6.7.8, 6.7.9)",
    "validita' interna del profilo ICC oltre intestazione e spazio colore (6.2.3.2-1)",
    "limiti di implementazione: dimensioni di stringhe, array, dizionari, annidamento (6.1.12)",
    "sintassi minuta: EOL, spaziature, lunghezza reale degli stream (6.1.4, 6.1.7, 6.1.8)",
    "intento di rendering e funzioni di trasferimento (6.2.8, 6.2.9)",
    "livello 1a: tag semantici, RoleMap, ToUnicode, lingua (6.8.3, 6.8.4, 6.3.8)",
]

DICHIARAZIONE = ("Verifica strutturale INDICATIVA: non prova la conformita' PDF/A. "
                 "Solo un validatore indipendente (veraPDF) puo' accertarla; esito del collaudo A11: da_collaudare.")

AZIONI_VIETATE = {"Launch", "Sound", "Movie", "ResetForm", "ImportData", "JavaScript", "Hide", "SetState", "NoOp"}
NAMED_AMMESSE = {"NextPage", "PrevPage", "FirstPage", "LastPage"}
ANNOT_VIETATE = {"Sound", "Movie", "FileAttachment"}                # 6.5.2-1
ANNOT_MULTIMEDIA_PRUDENZIALI = {"Screen", "3D", "RichMedia"}
ANNOT_NOTE_PDF14 = {"Text", "Link", "FreeText", "Line", "Square", "Circle", "Polygon", "PolyLine", "Highlight",
                    "Underline", "Squiggly", "StrikeOut", "Stamp", "Ink", "Popup", "Widget", "PrinterMark",
                    "TrapNet"}


def _r(o):
    """Risolve un riferimento indiretto."""
    try:
        return o.get_object() if hasattr(o, "get_object") else o
    except Exception:
        return None


def _g(d, k):
    try:
        return _r(dict.get(d, k))
    except Exception:
        return None


def _nome(o) -> str | None:
    o = _r(o)
    return str(o)[1:] if o is not None and str(o).startswith("/") else None


class _Esito:
    def __init__(self):
        self.motivi: dict[str, dict] = {}
        self.avvisi: list[str] = []

    def ko(self, codice: str, messaggio: str, oggetto: str | None = None, clausola: str | None = None):
        m = self.motivi.setdefault(codice, {"codice": codice, "clausola": clausola or CONTROLLI_ESEGUITI[codice],
                                            "messaggio": messaggio, "occorrenze": 0, "oggetti": []})
        m["occorrenze"] += 1
        if oggetto and len(m["oggetti"]) < 5 and oggetto not in m["oggetti"]:
            m["oggetti"].append(oggetto)


def _oid(ref) -> str | None:
    return f"{ref.idnum} {ref.generation} R" if isinstance(ref, IndirectObject) else None


def _percorri(reader: PdfReader):
    """Visita ogni oggetto raggiungibile dal trailer una volta sola: genera (oggetto, id indiretto)."""
    visti: set[int] = set()
    pila: list = [(reader.trailer, None)]
    while pila:
        o, rid = pila.pop()
        if isinstance(o, IndirectObject):
            if o.idnum in visti:
                continue
            visti.add(o.idnum)
            rid = _oid(o)
            o = _r(o)
        if o is None:
            continue
        if isinstance(o, DictionaryObject):          # include StreamObject
            yield o, rid
            for v in dict.values(o):
                if isinstance(v, (IndirectObject, DictionaryObject, ArrayObject)):
                    pila.append((v, None))
        elif isinstance(o, ArrayObject):
            for v in o:
                if isinstance(v, (IndirectObject, DictionaryObject, ArrayObject)):
                    pila.append((v, None))


def _verifica_icc(es: _Esito, prof, oid: str | None):
    if not isinstance(prof, StreamObject):
        es.ko("PDFA_ICC", "DestOutputProfile non e' uno stream: profilo ICC non incorporato", oid)
        return None
    try:
        dati = prof.get_data()
    except Exception as e:
        es.ko("PDFA_ICC", f"profilo ICC illeggibile: {str(e)[:80]}", oid)
        return None
    if len(dati) < 128 or dati[36:40] != b"acsp":
        es.ko("PDFA_ICC", "il contenuto non ha l'intestazione di un profilo ICC (firma 'acsp' assente)", oid)
        return None
    if int.from_bytes(dati[0:4], "big") > len(dati):
        es.ko("PDFA_ICC", "dimensione dichiarata dal profilo ICC superiore ai dati incorporati", oid)
    n_prof = {b"RGB ": 3, b"GRAY": 1, b"CMYK": 4}.get(dati[16:20])
    n_dic = _g(prof, "/N")
    if n_prof is None:
        es.ko("PDFA_ICC", f"spazio colore del profilo non ammesso/riconosciuto: {dati[16:20]!r}", oid)
    elif n_dic is None or int(n_dic) != n_prof:
        es.ko("PDFA_ICC", f"/N del dizionario ({n_dic}) non coincide con lo spazio colore del profilo ({n_prof})", oid)
    return n_prof


def _verifica_xmp(es: _Esito, root, livello: str):
    meta = _g(root, "/Metadata")
    if not isinstance(meta, StreamObject):
        es.ko("PDFA_METADATA", "catalogo senza stream Metadata XMP")
        es.ko("PDFA_XMP_PDFAID", "identificazione PDF/A (pdfaid) assente perche' manca l'XMP")
        return
    if _nome(_g(meta, "/Subtype")) != "XML":
        es.ko("PDFA_METADATA", "lo stream Metadata non ha Subtype /XML")
    if _g(meta, "/Filter") is not None:
        es.ko("PDFA_METADATA", "lo stream Metadata XMP non deve avere Filter (6.7.2-2)")
    try:
        dati = meta.get_data()
    except Exception as e:
        es.ko("PDFA_XMP_FORMA", f"stream XMP illeggibile: {str(e)[:80]}")
        return
    testo = dati.decode("utf-8", "ignore")
    inizio = re.search(r"<\?xpacket\s+begin[^>]*\?>", testo)
    if inizio and re.search(r"\b(bytes|encoding)\s*=", inizio.group(0)):
        es.ko("PDFA_XMP_FORMA", "l'intestazione xpacket usa gli attributi 'bytes' o 'encoding' (6.7.5)")
    try:
        radice = etree.fromstring(dati, etree.XMLParser(resolve_entities=False, no_network=True))
    except etree.XMLSyntaxError as e:
        es.ko("PDFA_XMP_FORMA", f"XMP non ben formato: {str(e)[:100]}")
        es.ko("PDFA_XMP_PDFAID", "pdfaid non rilevabile in un XMP non ben formato")
        return
    parte = conf = None
    for el in radice.iter():
        if not isinstance(el.tag, str):
            continue
        for chiave, val in el.attrib.items():
            if chiave == f"{{{NS_PDFAID}}}part":
                parte = val
            elif chiave == f"{{{NS_PDFAID}}}conformance":
                conf = val
        if el.tag == f"{{{NS_PDFAID}}}part" and el.text:
            parte = el.text.strip()
        elif el.tag == f"{{{NS_PDFAID}}}conformance" and el.text:
            conf = el.text.strip()
    if parte is None or conf is None:
        es.ko("PDFA_XMP_PDFAID", "pdfaid:part / pdfaid:conformance assenti nell'XMP (6.7.11-1)")
        return
    if parte != "1":
        es.ko("PDFA_XMP_PDFAID", f"pdfaid:part={parte!r}: atteso '1' per PDF/A-1 (6.7.11-2)")
    ammessi = {"A"} if livello == "1a" else {"A", "B"}
    if conf not in ammessi:
        es.ko("PDFA_XMP_PDFAID", f"pdfaid:conformance={conf!r}: ammessi {sorted(ammessi)} per il livello {livello} "
                                 "(6.7.11-3)")


def verifica_strutturale_pdfa(percorso: Path | str, livello: str = "1b") -> dict:
    """Controlli strutturali prudenti. Vedi il docstring del modulo: l'esito e' INDICATIVO."""
    if livello not in ("1a", "1b"):
        raise ValueError("livello ammesso: 1a o 1b")
    es = _Esito()
    p = Path(percorso)
    dati = p.read_bytes()
    risultato = {"validatore": "strutturale_interno", "profilo": livello, "fonte_regole": FONTE_REGOLE,
                 "dichiarazione": DICHIARAZIONE, "controlli_non_eseguiti": list(CONTROLLI_NON_ESEGUITI)}

    def chiudi(eseguiti: list[str]) -> dict:
        motivi = sorted(es.motivi.values(), key=lambda m: m["codice"])
        return {**risultato, "esito": "indicativo_ko" if motivi else "indicativo_ok", "motivi": motivi,
                "avvisi": es.avvisi, "controlli_eseguiti": eseguiti}

    if not dati.startswith(b"%PDF-1."):
        es.ko("PDFA_HEADER", "il file non inizia con '%PDF-1.n' (non e' un PDF o ha byte iniziali estranei)")
        return chiudi(["PDFA_HEADER"])
    riga2 = dati[: dati.find(b"\n", 0, 100) + 1 + 20][dati.find(b"\n", 0, 100) + 1:] if b"\n" in dati[:100] else b""
    if riga2.startswith(b"%") and sum(1 for b in riga2[1:] if b > 127) < 4:
        es.ko("PDFA_HEADER_BINARIO", "il commento dopo l'intestazione non ha almeno 4 byte > 127")
    elif not riga2.startswith(b"%"):
        es.ko("PDFA_HEADER_BINARIO", "manca il commento binario dopo l'intestazione")
    try:
        reader = PdfReader(str(p))
    except (PyPdfError, OSError, ValueError) as e:
        es.ko("PDFA_LEGGIBILITA", f"file non leggibile/danneggiato: {str(e)[:120]}")
        return chiudi(["PDFA_HEADER", "PDFA_LEGGIBILITA"])
    if reader.is_encrypted:
        es.ko("PDFA_CIFRATURA", "il trailer contiene Encrypt: la cifratura non e' ammessa in PDF/A (6.1.3-2)")
        return chiudi(["PDFA_HEADER", "PDFA_CIFRATURA"])

    eseguiti = [c for c in CONTROLLI_ESEGUITI if c != "PDFA_1A_STRUTTURA" or livello == "1a"]
    try:
        # --- sintassi grezza -------------------------------------------------------------------
        ultimo_eof = dati.rfind(b"%%EOF")
        if ultimo_eof < 0:
            es.ko("PDFA_LEGGIBILITA", "manca %%EOF: file troncato")
        elif dati[ultimo_eof + 5:].strip(b"\r\n") != b"":
            es.ko("PDFA_DOPO_EOF", "byte dopo l'ultimo %%EOF (6.1.3-3)")
        if re.search(rb"/Type\s*/XRef\b", dati) or re.search(rb"/Type\s*/ObjStm\b", dati):
            es.ko("PDFA_XREF_STREAM", "xref stream o object stream presenti (non ammessi, 6.1.4-3)")
        if reader.trailer.get("/ID") is None:
            es.ko("PDFA_TRAILER_ID", "il trailer non contiene la chiave ID (6.1.3-1)")
        if reader.trailer.get("/Encrypt") is not None:
            es.ko("PDFA_CIFRATURA", "Encrypt nel trailer (6.1.3-2)")

        root = reader.trailer["/Root"]
        # --- metadati XMP, OutputIntent --------------------------------------------------------
        _verifica_xmp(es, root, livello)
        intent_n = _verifica_outputintent(es, root)
        if _g(root, "/OCProperties") is not None:
            es.ko("PDFA_OPTIONAL_CONTENT", "OCProperties nel catalogo (6.1.13-1)")
        if _g(root, "/AA") is not None:
            es.ko("PDFA_AZIONI", "azioni aggiuntive (AA) nel catalogo (6.6.2-3)")
        nomi = _g(root, "/Names")
        if isinstance(nomi, DictionaryObject):
            if _g(nomi, "/EmbeddedFiles") is not None:
                es.ko("PDFA_FILE_INCORPORATI", "EmbeddedFiles nel name dictionary (6.1.11-2)")
            if _g(nomi, "/JavaScript") is not None:
                es.ko("PDFA_JAVASCRIPT", "albero Names/JavaScript presente (6.6.1-1)")
        acro = _g(root, "/AcroForm")
        if isinstance(acro, DictionaryObject) and _g(acro, "/NeedAppearances") is True:
            es.ko("PDFA_FORM", "NeedAppearances true (6.9-1)")
        if livello == "1a":
            mark = _g(root, "/MarkInfo")
            if not (isinstance(mark, DictionaryObject) and _g(mark, "/Marked") is True):
                es.ko("PDFA_1A_STRUTTURA", "MarkInfo/Marked true assente (6.8.2.2-1)")
            if _g(root, "/StructTreeRoot") is None:
                es.ko("PDFA_1A_STRUTTURA", "StructTreeRoot assente (6.8.3.3-1)")
        # --- grafo degli oggetti -----------------------------------------------------------------
        device_usati: set[str] = set()
        for d, rid in _percorri(reader):
            _controlla_dizionario(es, d, rid, device_usati)
        if intent_n == 3 and "DeviceCMYK" in device_usati:
            es.ko("PDFA_COLORE_VS_INTENT", "DeviceCMYK usato con un OutputIntent RGB (6.2.3.3-2)")
        if intent_n == 4 and "DeviceRGB" in device_usati:
            es.ko("PDFA_COLORE_VS_INTENT", "DeviceRGB usato con un OutputIntent CMYK (6.2.3.3-1)")
    except Exception as e:  # struttura anomala durante la visita: mai un esito positivo
        es.ko("PDFA_LEGGIBILITA", f"errore durante la visita della struttura: {type(e).__name__}: {str(e)[:100]}")
    return chiudi(eseguiti)


def _verifica_outputintent(es: _Esito, root) -> int | None:
    oi = _g(root, "/OutputIntents")
    if not isinstance(oi, ArrayObject) or len(oi) == 0:
        es.ko("PDFA_OUTPUTINTENT", "OutputIntent assente (prudenziale: richiesto in pratica da 6.2.3.3-3)")
        return None
    n_prof = None
    profili_ids = set()
    gts = False
    for voce in oi:
        d = _r(voce)
        if not isinstance(d, DictionaryObject):
            continue
        if _nome(_g(d, "/S")) == "GTS_PDFA1":
            gts = True
        rif = dict.get(d, "/DestOutputProfile")
        if rif is None:
            continue
        if isinstance(rif, IndirectObject):
            profili_ids.add(rif.idnum)
        n_prof = _verifica_icc(es, _r(rif), _oid(rif)) or n_prof
    if not gts:
        es.ko("PDFA_OUTPUTINTENT", "nessun OutputIntent con /S /GTS_PDFA1 (6.2.2-1)")
    if n_prof is None and not any(es.motivi.get(c) for c in ("PDFA_ICC",)):
        es.ko("PDFA_OUTPUTINTENT", "OutputIntent senza DestOutputProfile: profilo ICC non incorporato (6.2.2-1)")
    if len(profili_ids) > 1:
        es.ko("PDFA_OUTPUTINTENT", "piu' OutputIntent con profili diversi (6.2.2-2)")
    return n_prof


def _controlla_dizionario(es: _Esito, d: DictionaryObject, rid: str | None, device_usati: set[str]):
    tipo, sub = _nome(_g(d, "/Type")), _nome(_g(d, "/Subtype"))
    chiavi = set(dict.keys(d))

    # filtri e riferimenti esterni su stream (6.1.10, 6.1.7-3)
    if isinstance(d, StreamObject):
        filtro = _g(d, "/Filter")
        nomi_filtri = [str(_r(x)) for x in filtro] if isinstance(filtro, ArrayObject) else ([str(filtro)] if filtro else [])
        if any(n in ("/LZWDecode", "/LZW") for n in nomi_filtri):
            es.ko("PDFA_LZW", "filtro LZWDecode (6.1.10)", rid)
        if chiavi & {"/F", "/FFilter", "/FDecodeParms"}:
            es.ko("PDFA_RIF_ESTERNO", "stream con riferimento a file esterno (F/FFilter/FDecodeParms) (6.1.7-3)", rid)
    if "/EF" in chiavi:
        es.ko("PDFA_FILE_INCORPORATI", "specifica di file con EF: file incorporato (6.1.11-1)", rid)

    # font (6.3.4-1)
    if tipo == "Font" and sub in ("Type1", "MMType1", "TrueType", "CIDFontType0", "CIDFontType2"):
        fd = _g(d, "/FontDescriptor")
        incorporato = isinstance(fd, DictionaryObject) and bool(
            {"/FontFile", "/FontFile2", "/FontFile3"} & set(dict.keys(fd)))
        if not incorporato:
            es.ko("PDFA_FONT", f"font non incorporato: {_nome(_g(d, '/BaseFont')) or '?'} (6.3.4-1)", rid)

    # trasparenza (6.4)
    sm = _g(d, "/SMask")
    if "/SMask" in chiavi and not (_nome(sm) == "None"):
        es.ko("PDFA_TRASPARENZA", "SMask presente (6.4-1/6.4-2)", rid)
    bm = _g(d, "/BM")
    if bm is not None:
        nomi_bm = [_nome(x) for x in bm] if isinstance(bm, ArrayObject) else [_nome(bm)]
        if any(n not in ("Normal", "Compatible") for n in nomi_bm):
            es.ko("PDFA_TRASPARENZA", f"modo di fusione BM non ammesso: {nomi_bm} (6.4-4)", rid)
    for k in ("/CA", "/ca"):
        if k in chiavi:
            try:
                if abs(float(_g(d, k)) - 1.0) > 1e-9:
                    es.ko("PDFA_TRASPARENZA", f"opacita' {k} diversa da 1.0 (6.4-5/6.4-6)", rid)
            except (TypeError, ValueError):
                pass
    grp = _g(d, "/Group")
    if isinstance(grp, DictionaryObject) and _nome(_g(grp, "/S")) == "Transparency":
        es.ko("PDFA_TRASPARENZA", "gruppo di trasparenza su pagina o form XObject (6.4-3)", rid)

    # immagini e XObject (6.2.4-6.2.7)
    if sub == "Image":
        if "/Alternates" in chiavi:
            es.ko("PDFA_IMMAGINI", "immagine con Alternates (6.2.4-1)", rid)
        if _g(d, "/Interpolate") is True:
            es.ko("PDFA_IMMAGINI", "immagine con Interpolate true (6.2.4-3)", rid)
        cs = _g(d, "/ColorSpace")
        if cs is not None and _nome(cs) in ("DeviceRGB", "DeviceCMYK", "DeviceGray"):
            device_usati.add(_nome(cs))
    if "/OPI" in chiavi:
        es.ko("PDFA_IMMAGINI", "chiave OPI in un XObject (6.2.4-2)", rid)
    if sub == "PS" or "/PS" in chiavi:
        es.ko("PDFA_IMMAGINI", "PostScript XObject (6.2.5/6.2.7)", rid)
    if "/Ref" in chiavi and sub == "Form":
        es.ko("PDFA_IMMAGINI", "reference XObject (6.2.6-1)", rid)
    csd = _g(d, "/ColorSpace")
    if isinstance(csd, DictionaryObject) and sub != "Image":
        for v in dict.values(csd):
            if _nome(v) in ("DeviceRGB", "DeviceCMYK", "DeviceGray"):
                device_usati.add(_nome(v))

    # azioni e JavaScript (6.6)
    s = _nome(_g(d, "/S"))
    if "/JS" in chiavi:
        es.ko("PDFA_JAVASCRIPT", "JavaScript presente (chiave JS) (6.6.1-1)", rid)
    if s is not None and (tipo == "Action" or s in AZIONI_VIETATE or s == "Named"):
        if s in AZIONI_VIETATE:
            es.ko("PDFA_AZIONI", f"azione vietata: {s} (6.6.1-1)", rid)
        elif s == "Named" and _nome(_g(d, "/N")) not in NAMED_AMMESSE:
            es.ko("PDFA_AZIONI", f"azione Named non ammessa: {_nome(_g(d, '/N'))} (6.6.1-2)", rid)
    if sub in ("URI",) or s in ("URI", "GoToR"):
        if f"collegamento esterno ({s or sub})" not in es.avvisi:
            es.avvisi.append(f"collegamento esterno ({s or sub}) presente: non verificato rispetto alla norma")
    if ("/AA" in chiavi) and (sub == "Widget" or "/FT" in chiavi):
        es.ko("PDFA_AZIONI", "azioni aggiuntive (AA) su widget/campo (6.6.2-1/6.6.2-2)", rid)
    if "/A" in chiavi and "/FT" in chiavi:
        es.ko("PDFA_AZIONI", "azione A su un campo di modulo (6.6.1-3)", rid)

    # annotazioni (6.5) e moduli (6.9)
    if tipo == "Annot" or (sub is not None and sub in ANNOT_NOTE_PDF14 | ANNOT_VIETATE | ANNOT_MULTIMEDIA_PRUDENZIALI
                           and "/Rect" in chiavi):
        if sub in ANNOT_VIETATE:
            es.ko("PDFA_ANNOTAZIONI", f"annotazione vietata: {sub} (6.5.2-1)", rid)
        elif sub in ANNOT_MULTIMEDIA_PRUDENZIALI:
            es.ko("PDFA_MULTIMEDIA", f"contenuto multimediale/interattivo: annotazione {sub} (prudenziale)", rid)
        elif sub is not None and sub not in ANNOT_NOTE_PDF14:
            es.ko("PDFA_ANNOTAZIONI", f"tipo di annotazione non definito in PDF 1.4: {sub} (prudenziale, 6.5.2-1)", rid)
        if sub != "Popup":
            try:
                f = int(_g(d, "/F") or 0)
            except (TypeError, ValueError):
                f = 0
            if not f & 4:
                es.ko("PDFA_ANNOTAZIONI", "annotazione senza flag Print (6.5.3-2)", rid)
            if f & (1 | 2 | 32):
                es.ko("PDFA_ANNOTAZIONI", "annotazione con flag Hidden/Invisible/NoView (6.5.3-2)", rid)
        ap = _g(d, "/AP")
        if isinstance(ap, DictionaryObject) and set(dict.keys(ap)) - {"/N"}:
            es.ko("PDFA_ANNOTAZIONI", "dizionario AP con voci diverse da N (6.5.3-4)", rid)
        if sub == "Widget" and not isinstance(ap, DictionaryObject):
            es.ko("PDFA_FORM", "widget/campo di modulo senza dizionario di aspetto AP (6.9-2)", rid)
