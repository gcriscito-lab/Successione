"""Dimensioni degli allegati e della fornitura: riduzione, suddivisione senza perdita, verifica dei limiti.

Fonti (vedi ``limiti``): Specifiche_SUC13_20250702.pdf p.7 par. 2.3 "Ogni file allegato non deve superare la
dimensione massima di 5 MB. Nel caso in cui il file superi la dimensione massima e' necessario suddividerlo in piu'
file." e p.3 par. 1 "la dimensione complessiva delle dichiarazioni di successione da trasmettere non puo' eccedere il
limite previsto di 40 MB compressi" ... "La fornitura deve contenere i dati relativi ad una sola dichiarazione".

ASSUNZIONI (le fonti non le risolvono; restano parametri, mai costanti nascoste):
  * unita' di "MB": il chiamante passa il limite in BYTE; il predefinito e' decimale (5 000 000 / 40 000 000), piu'
    severo del binario (5 242 880 / 41 943 040). Vedi ``limiti.limite_byte``.
  * limite per allegato: misurato sul file binario PRIMA della codifica Base64 (Base64 aggiunge circa un terzo).
  * limite di fornitura: punto di misura scelto con ``punto_misura`` (vedi ``PUNTI_MISURA``); algoritmo e contenitore
    della compressione usati dall'Agenzia/Entratel non sono indicati: DEFLATE (zlib, livello 9) e' una stima.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import zlib
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, ByteStringObject, DictionaryObject, IndirectObject, NameObject, StreamObject

from ..errori import DatiNonValidi, ErroreServizio
from ..schema import Errore
from . import limiti as L
from .base64 import codifica_base64, tipo_file_eg, valida_nome_file_eg

# (dpi, QFactor JPEG): 200 dpi e' l'indicazione di prassi del Fascicolo I p.49; 150 dpi e' l'ultimo tentativo
# predefinito per non compromettere la leggibilita' (scelta del progetto, modificabile dal chiamante).
TENTATIVI_PREDEFINITI: tuple[tuple[int, float], ...] = ((200, 0.4), (150, 0.6))
MARGINE_STIMA = 0.95          # le parti si compongono sulla stima fino al 95% del limite, poi si misurano davvero
SOGLIA_TESTO = 0.90           # somiglianza minima del testo per pagina (pdftotext) fra sorgente e derivato

PUNTI_MISURA = {
    "xml_deflate": "XML della fornitura con gli allegati Base64, compresso con DEFLATE livello 9 (zlib). ASSUNZIONE: "
                   "contenitore e algoritmo di compressione dell'Agenzia non indicati dalle fonti",
    "xml_non_compresso": "XML della fornitura non compresso (stima massima, prudenziale)",
    "allegati_base64_deflate": "solo allegati: somma dei testi Base64 compressi con DEFLATE livello 9. Limite "
                               "INFERIORE della fornitura (esclude i dati dichiarativi): un superamento e' certo, "
                               "il rispetto no",
}


class LimiteNonRaggiungibile(ErroreServizio):
    codice = "LIMITE_NON_RAGGIUNGIBILE"


class ListaParti(list):
    """``list[Path]`` con il rapporto dell'operazione nell'attributo ``rapporto``."""

    def __init__(self, parti, rapporto: dict):
        super().__init__(parti)
        self.rapporto = rapporto


# ------------------------------------------------------------------------------------------------ utilita'

def sha256_file(p: Path | str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blocco in iter(lambda: f.read(1 << 20), b""):
            h.update(blocco)
    return h.hexdigest()


def trova_qpdf() -> str | None:
    for n in (os.environ.get("SUCCESSIONI_QPDF"), "qpdf"):
        if n and shutil.which(n):
            return shutil.which(n)
    return None


def descrivi_byte(n: int) -> str:
    return f"{n} byte ({n / L.MB_DECIMALE:.3f} MB decimali, {n / L.MB_BINARIO:.3f} MiB)"


def testo_pagine(pdf: Path | str) -> list[str]:
    """Testo per pagina con pdftotext (poppler) se presente, altrimenti con pypdf."""
    exe = shutil.which("pdftotext")
    if exe:
        pr = subprocess.run([exe, "-enc", "UTF-8", str(pdf), "-"], capture_output=True, timeout=300)
        if pr.returncode == 0:
            pagine = pr.stdout.decode("utf-8", "replace").split("\f")
            if pagine and not pagine[-1].strip():
                pagine = pagine[:-1]
            return pagine
    return [(pg.extract_text() or "") for pg in PdfReader(str(pdf)).pages]


def _norm(t: str) -> str:
    return re.sub(r"\s+", "", t)


def confronta_testo(rif: list[str], nuovo: list[str], soglia: float = SOGLIA_TESTO) -> dict:
    """Confronto pagina per pagina (spazi ignorati).

    ``differenze``: ogni pagina con testo estratto diverso, con i caratteri della sorgente persi o sostituiti (es. lettere
    accentate quando il convertitore non conserva la mappatura ToUnicode). ``divergenti``: le pagine sotto ``soglia``
    di somiglianza (testo largamente perso o pagine scambiate)."""
    differenze, divergenti = [], []
    for i, (a, b) in enumerate(zip(rif, nuovo), 1):
        na, nb = _norm(a), _norm(b)
        if na == nb:
            continue
        sm = difflib.SequenceMatcher(None, na, nb, autojunk=False)
        r = sm.ratio() if na or nb else 1.0
        persi = "".join(na[i1:i2] for op, i1, i2, _, _ in sm.get_opcodes() if op in ("delete", "replace"))
        voce = {"pagina": i, "somiglianza": round(r, 3), "caratteri_sorgente": len(na), "caratteri_derivato": len(nb),
                "caratteri_persi": len(persi), "esempio_persi": persi[:20]}
        differenze.append(voce)
        if r < soglia:
            divergenti.append(voce)
    return {"pagine_sorgente": len(rif), "pagine_derivato": len(nuovo), "strumento":
            "pdftotext" if shutil.which("pdftotext") else "pypdf", "soglia": soglia, "differenze": differenze,
            "divergenti": divergenti}


# --------------------------------------------------------------------------------------- stima per pagina

def _dim_oggetto(o) -> int:
    if isinstance(o, StreamObject):
        d = getattr(o, "_data", None)
        if d is None:
            try:
                d = o.get_data()
            except Exception:
                d = b""
        return len(d) + 64 + 24 * len(o)
    if isinstance(o, (DictionaryObject, ArrayObject)):
        return 32 + 24 * len(o)
    return 32


_SALTA = {"/Parent", "/P", "/Pg", "/B", "/Prev", "/Next", "/First", "/Last"}


def _raggiungibili(partenza, pagina_id: int | None, salta=_SALTA) -> dict[int, int]:
    """{id oggetto: byte stimati} raggiungibili da ``partenza`` senza entrare in altre pagine."""
    visti: dict[int, int] = {}
    pila = [partenza]
    while pila:
        v = pila.pop()
        if isinstance(v, IndirectObject):
            if v.idnum in visti:
                continue
            o = v.get_object()
            if isinstance(o, DictionaryObject) and o.get("/Type") == "/Page" and v.idnum != pagina_id:
                continue
            visti[v.idnum] = _dim_oggetto(o)
            v = o
        if isinstance(v, DictionaryObject):
            for k, x in dict.items(v):
                if k not in salta and isinstance(x, (IndirectObject, DictionaryObject, ArrayObject)):
                    pila.append(x)
        elif isinstance(v, ArrayObject):
            pila.extend(x for x in v if isinstance(x, (IndirectObject, DictionaryObject, ArrayObject)))
    return visti


def stima_pagine(pdf: Path | str) -> tuple[int, list[dict[int, int]]]:
    """(byte comuni al documento, [oggetti e byte di ogni pagina]). Gli oggetti condivisi si contano una volta per parte."""
    r = PdfReader(str(pdf))
    radice = r.trailer.raw_get("/Root")
    comuni = _raggiungibili(radice, None, salta=_SALTA | {"/Pages"})
    info = r.trailer.raw_get("/Info") if "/Info" in r.trailer else None
    if info is not None:
        comuni.update(_raggiungibili(info, None))
    pagine = []
    for pg in r.pages:
        rif = pg.indirect_reference
        pagine.append(_raggiungibili(rif if rif is not None else pg, rif.idnum if rif is not None else None))
    return sum(comuni.values()) + 1024, pagine


def _gruppi(comuni: int, pagine: list[dict[int, int]], budget: float) -> list[tuple[int, int]]:
    """Intervalli di pagine (0-based, estremi inclusi) composti in ordine, finche' la stima resta nel budget."""
    gruppi, inizio, unione, somma = [], 0, {}, comuni
    for i, pp in enumerate(pagine):
        aggiunta = sum(sz for k, sz in pp.items() if k not in unione)
        if i > inizio and somma + aggiunta > budget:
            gruppi.append((inizio, i - 1))
            inizio, unione, somma = i, dict(pp), comuni + sum(pp.values())
        else:
            unione.update(pp)
            somma += aggiunta
    if pagine:
        gruppi.append((inizio, len(pagine) - 1))
    return gruppi


def _scrivi_parte(base: Path, da: int, a: int, dst: Path) -> str:
    """Copia le pagine da..a (0-based, incluse) in ``dst`` conservando catalogo, XMP e OutputIntent di ``base``."""
    qpdf = trova_qpdf()
    if qpdf:
        cmd = [qpdf, "--object-streams=disable", str(base), "--pages", ".", f"{da + 1}-{a + 1}", "--", str(dst)]
        pr = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if pr.returncode in (0, 3) and dst.exists() and dst.stat().st_size > 0:   # 3 = avvisi, file scritto
            return "qpdf"
        raise RuntimeError(f"qpdf non riuscito ({pr.returncode}): {(pr.stderr or '')[-300:]}")
    r = PdfReader(str(base))
    w = PdfWriter()
    for i in range(da, a + 1):
        w.add_page(r.pages[i])
    radice = r.trailer["/Root"]
    for k in ("/Metadata", "/OutputIntents", "/MarkInfo", "/Lang"):      # identita' PDF/A del documento base
        if k in radice:
            w._root_object[NameObject(k)] = radice.raw_get(k).clone(w)
    ident = ByteStringObject(hashlib.md5(f"{base}:{da}:{a}:{os.urandom(8).hex()}".encode()).digest())
    w._ID = ArrayObject([ident, ident])                                      # 6.1.3-1: ID nel trailer
    with open(dst, "wb") as f:
        w.write(f)
    return "pypdf"


def _pagine(pdf: Path) -> int:
    return len(PdfReader(str(pdf)).pages)


def _sintesi_validazione(v: dict) -> dict:
    ind = v.get("verifica_indicativa") or {}
    return {"esito": v.get("esito"), "validatore": v.get("validatore"), "motivo": v.get("motivo"),
            "indicativo": ind.get("esito"), "motivi_indicativi": [m["codice"] for m in ind.get("motivi", [])],
            "regole_fallite": v.get("regole_fallite")}


# --------------------------------------------------------------------------------- riduzione/suddivisione

def riduci_o_suddividi(pdf: Path | str, limite_byte: int = L.LIMITE_ALLEGATO_DECIMALE, *,
                       cartella_uscita: Path | str | None = None,
                       tentativi: tuple[tuple[int, float], ...] | list = TENTATIVI_PREDEFINITI,
                       scala_di_grigi: bool = False, livello: str = "1b", forza_pdfa: bool = True,
                       valida: bool = True) -> ListaParti:
    """Rende il PDF entro ``limite_byte`` per file, senza perdere pagine. Restituisce i percorsi (``ListaParti``).

    1. nessuna azione se il file e' gia' entro il limite (e dichiara PDF/A, oppure ``forza_pdfa=False``);
    2. altrimenti conversione PDF/A con ricompressione delle immagini (Ghostscript) secondo ``tentativi``;
    3. se nessun tentativo basta, suddivisione per pagine (qpdf; pypdf in mancanza) del candidato piu' piccolo:
       ogni parte e' misurata davvero e, se eccede, divisa ancora; una singola pagina oltre il limite produce
       ``LimiteNonRaggiungibile`` (nessuna perdita silenziosa).
    Ogni uscita e' rivalidata (``pdfa.valida_pdfa``: 'conforme' solo con veraPDF), il testo per pagina confrontato con
    la sorgente (pdftotext) e l'originale verificato invariato (SHA-256). Rapporto in ``risultato.rapporto`` e in
    ``<cartella_uscita>/<nome>_rapporto_dimensioni.json``. ``cartella_uscita`` predefinita: nuova cartella temporanea.
    """
    from .. import pdfa
    src = Path(pdf)
    limite_byte = int(limite_byte)
    if limite_byte <= 0:
        raise ValueError("limite_byte deve essere positivo")
    an = pdfa.analizza_pdf(src)
    if an.get("esito") not in ("leggibile", "firmato"):
        raise DatiNonValidi(f"file non elaborabile: esito '{an.get('esito')}'", esito=an.get("esito"),
                            dettaglio=an.get("dettaglio"))
    h0, n, dim0 = sha256_file(src), an["pagine"], src.stat().st_size
    e_pdfa = an.get("dichiara_pdfa") in ("1a", "1b")
    out = Path(cartella_uscita) if cartella_uscita else Path(tempfile.mkdtemp(prefix="successioni_parti_"))
    out.mkdir(parents=True, exist_ok=True)
    rap: dict = {
        "sorgente": {"percorso": str(src), "sha256": h0, "bytes": dim0, "pagine": n,
                     "dichiara_pdfa": an.get("dichiara_pdfa"), "firme_digitali": an.get("firme_digitali", 0)},
        "limite_byte": limite_byte, "limite": descrivi_byte(limite_byte),
        "assunzioni": ["limite misurato sul file binario prima della codifica Base64",
                       "unita' del limite: quella scelta dal chiamante (byte)"],
        "fonte": L.FONTE_ALLEGATO,
        "parametri": {"tentativi": [list(t) for t in tentativi], "scala_di_grigi": scala_di_grigi, "livello": livello,
                      "forza_pdfa": forza_pdfa, "margine_stima": MARGINE_STIMA, "soglia_testo": SOGLIA_TESTO},
        "tentativi": [], "avvisi": [],
    }
    if an.get("firme_digitali"):
        rap["avvisi"].append("l'originale e' firmato digitalmente: i derivati (ricompressi o suddivisi) NON "
                             "conservano la firma")
    testo_src = testo_pagine(src)

    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        candidati: list[tuple[Path, str]] = []
        if dim0 <= limite_byte and (e_pdfa or not forza_pdfa):
            azione, base = "nessuna", src
        else:
            if e_pdfa or not forza_pdfa:
                candidati.append((src, "sorgente"))
            passi: list[tuple[int | None, float | None]] = []
            if not candidati and (dim0 <= limite_byte or not tentativi):
                passi.append((None, None))                 # conversione semplice in PDF/A
            passi += [tuple(x) for x in tentativi]
            for dpi, q in passi:
                if any(c.stat().st_size <= limite_byte for c, _ in candidati):
                    break
                dst = tmp / f"ridotto_{dpi or 'conv'}_{len(rap['tentativi'])}.pdf"
                conv = pdfa.converti_in_pdfa(src, dst, livello, risoluzione_dpi=dpi,
                                             qfactor_jpeg=q if q is not None else 0.4, scala_di_grigi=scala_di_grigi)
                voce = {"dpi": dpi, "qfactor_jpeg": q, "comando_ok": conv["comando_ok"]}
                if conv["comando_ok"]:
                    np_ = _pagine(dst)
                    voce.update(bytes=dst.stat().st_size, pagine=np_)
                    if np_ != n:
                        voce["scartato"] = f"pagine {np_} invece di {n}"
                    else:
                        candidati.append((dst, f"PDF/A {dpi} dpi" if dpi else "PDF/A conversione semplice"))
                else:
                    voce["errore"] = conv.get("errore") or conv.get("stderr", "")[-200:]
                rap["tentativi"].append(voce)
            if not candidati:
                raise LimiteNonRaggiungibile("nessuna conversione PDF/A riuscita: impossibile ridurre o suddividere",
                                             tentativi=rap["tentativi"])
            entro = [c for c in candidati if c[0].stat().st_size <= limite_byte]
            base, desc = entro[0] if entro else min(candidati, key=lambda c: c[0].stat().st_size)
            if entro:
                azione = "nessuna" if base == src else ("conversione" if desc.endswith("semplice") else "riduzione")
            else:
                azione = "suddivisione" if base == src else "riduzione+suddivisione"
            rap["base"] = {"descrizione": desc, "bytes": base.stat().st_size}

        if azione in ("nessuna", "conversione", "riduzione"):
            intervalli = [(0, n - 1, base)]
            strumento = None
        else:
            comuni, pesi = stima_pagine(base)
            coda = _gruppi(comuni, pesi, limite_byte * MARGINE_STIMA)
            intervalli, strumento = [], None
            while coda:
                da, a = coda.pop(0)
                dst = tmp / f"parte_{da + 1:05d}_{a + 1:05d}.pdf"
                strumento = _scrivi_parte(base, da, a, dst)
                dim = dst.stat().st_size
                if dim <= limite_byte:
                    intervalli.append((da, a, dst))
                elif da == a:
                    raise LimiteNonRaggiungibile(
                        f"la pagina {da + 1} da sola occupa {descrivi_byte(dim)}, oltre il limite di "
                        f"{descrivi_byte(limite_byte)}: ridurre la risoluzione della scansione o usare il TIFF B/N G4",
                        pagina=da + 1, bytes=dim, limite_byte=limite_byte, tentativi=rap["tentativi"])
                else:
                    m = (da + a) // 2
                    coda[0:0] = [(da, m), (m + 1, a)]
            intervalli.sort()
        rap["azione"] = azione
        rap["strumento_suddivisione"] = strumento

        k = len(intervalli)
        risultato: list[Path] = []
        rap["parti"] = []
        testo_out: list[str] = []
        for i, (da, a, p) in enumerate(intervalli, 1):
            if p == src:
                finale = src
            else:
                nome = f"{src.stem}_parte{i:02d}di{k:02d}.pdf" if k > 1 else f"{src.stem}_ridotto.pdf"
                finale = out / nome
                shutil.copyfile(p, finale)
            np_ = _pagine(finale)
            if np_ != a - da + 1:
                raise RuntimeError(f"parte {i}: {np_} pagine invece di {a - da + 1}")
            testo_out += testo_pagine(finale)
            voce = {"parte": i, "di": k, "percorso": str(finale), "sha256": sha256_file(finale),
                    "bytes": finale.stat().st_size, "pagine_sorgente": [da + 1, a + 1], "n_pagine": np_}
            if valida:
                voce["validazione"] = _sintesi_validazione(pdfa.valida_pdfa(finale, livello))
            rap["parti"].append(voce)
            risultato.append(finale)

    totale = sum(v["n_pagine"] for v in rap["parti"])
    if totale != n:
        raise RuntimeError(f"pagine perse: sorgente {n}, uscite {totale}")
    rap["verifica_pagine"] = {"sorgente": n, "uscite": totale, "esito": "passato"}
    rap["verifica_testo"] = confronta_testo(testo_src, testo_out)
    if rap["verifica_testo"]["divergenti"]:
        rap["avvisi"].append("testo divergente su pagine " + ", ".join(
            str(d["pagina"]) for d in rap["verifica_testo"]["divergenti"][:20]) + ": controllare l'anteprima")
    elif rap["verifica_testo"]["differenze"]:
        rap["avvisi"].append("testo estratto con differenze minori (es. lettere accentate) su pagine " + ", ".join(
            str(d["pagina"]) for d in rap["verifica_testo"]["differenze"][:20]) + ": resa visiva da controllare")
    if any(v["bytes"] > limite_byte for v in rap["parti"]):
        raise RuntimeError("una parte supera il limite dopo la scrittura")      # non deve accadere
    if valida:
        non_ok = [v["parte"] for v in rap["parti"] if v["validazione"]["esito"] == "non_conforme"
                  or v["validazione"]["indicativo"] == "indicativo_ko"]
        if non_ok:
            rap["avvisi"].append(f"parti con validazione negativa: {non_ok} (vedi 'validazione')")
    if sha256_file(src) != h0:
        raise RuntimeError("l'originale risulta modificato durante l'elaborazione")
    rap["originale_invariato"] = True
    file_rap = out / f"{src.stem}_rapporto_dimensioni.json"
    rap["file_rapporto"] = str(file_rap)
    file_rap.write_text(json.dumps(rap, ensure_ascii=False, indent=1), encoding="utf-8")
    return ListaParti(risultato, rap)


# ------------------------------------------------------------------------------------------ fornitura

def _deflate_file(p: Path, base64: bool = False) -> int:
    c = zlib.compressobj(9)
    n = 0
    if base64:
        n += len(c.compress(codifica_base64(p.read_bytes()).encode("ascii")))
    else:
        with open(p, "rb") as f:
            for blocco in iter(lambda: f.read(1 << 20), b""):
                n += len(c.compress(blocco))
    return n + len(c.flush())


def misura_fornitura(manifest: dict, punto_misura: str = "xml_deflate") -> dict:
    """Misura della fornitura secondo ``punto_misura`` (vedi ``PUNTI_MISURA``), con assunzioni esplicite.

    ``manifest``: {"dichiarazioni": int (facoltativo), "xml": percorso o bytes dell'XML con allegati Base64
    (facoltativo), "allegati": [{"percorso", "nome_eg"?, "file_type"?, "id"?, "esito_validazione"?}]}.
    Senza XML si ripiega su "allegati_base64_deflate" (limite inferiore) e lo si dichiara."""
    if punto_misura not in PUNTI_MISURA:
        raise ValueError(f"punto_misura ammessi: {sorted(PUNTI_MISURA)}")
    xml = manifest.get("xml")
    effettivo = punto_misura
    if punto_misura.startswith("xml") and xml is None:
        effettivo = "allegati_base64_deflate"
    out = {"punto_misura_richiesto": punto_misura, "punto_misura": effettivo,
           "descrizione": PUNTI_MISURA[effettivo], "completa": effettivo != "allegati_base64_deflate",
           "fonte": L.FONTE_FORNITURA}
    if effettivo == "allegati_base64_deflate":
        tot = 0
        for a in manifest.get("allegati", []):
            p = Path(a["percorso"])
            if p.is_file():
                tot += _deflate_file(p, base64=True)
        out["bytes"] = tot
    elif isinstance(xml, (bytes, bytearray)):
        out["bytes"] = len(xml) if effettivo == "xml_non_compresso" else len(zlib.compress(bytes(xml), 9))
    else:
        p = Path(xml)
        out["bytes"] = p.stat().st_size if effettivo == "xml_non_compresso" else _deflate_file(p)
    out["misura"] = descrivi_byte(out["bytes"])
    return out


def verifica_fornitura(manifest: dict, limite_compresso: int = L.LIMITE_FORNITURA_DECIMALE, *,
                       limite_allegato: int | None = L.LIMITE_ALLEGATO_DECIMALE,
                       punto_misura: str = "xml_deflate", richiedi_xml: bool = False) -> list[Errore]:
    """Controlli dimensionali e formali della fornitura. Restituisce solo le violazioni (lista vuota = nessuna).

    Limiti in BYTE (unita' scelta dal chiamante; predefiniti decimali). Misura del limite per allegato: file binario
    prima della codifica Base64. Misura della fornitura: ``punto_misura`` (vedi ``misura_fornitura``). Senza XML la
    misura e' un limite inferiore: con ``richiedi_xml=True`` l'assenza dell'XML e' segnalata come errore."""
    err: list[Errore] = []
    n_dich = manifest.get("dichiarazioni", 1)
    if n_dich != 1:
        err.append(Errore("FORNITURA_PIU_DICHIARAZIONI", "fornitura.dichiarazioni",
                          f"{n_dich} dichiarazioni: la fornitura deve contenerne una sola", L.FONTE_FORNITURA))
    for i, a in enumerate(manifest.get("allegati", [])):
        perc = f"fornitura.allegati[{a.get('id', i)}]"
        p = Path(a.get("percorso", ""))
        if not p.is_file():
            err.append(Errore("ALLEGATO_MANCANTE", perc, f"file non trovato: {p}", "controllo interno"))
            continue
        dim = p.stat().st_size
        if limite_allegato is not None and dim > limite_allegato:
            err.append(Errore("ALLEGATO_OLTRE_LIMITE", perc,
                              f"{descrivi_byte(dim)} > limite {descrivi_byte(limite_allegato)} (misura: file binario "
                              "prima della codifica Base64): ridurre o suddividere", L.FONTE_ALLEGATO))
        rilevato = tipo_file_eg(p)
        if rilevato is None:
            err.append(Errore("ALLEGATO_FORMATO_NON_AMMESSO", perc, "contenuto non PDF ne' TIFF", L.FONTE_FORMATI))
        ft = a.get("file_type")
        if ft is not None:
            if ft not in L.TIPI_FILE_EG:
                err.append(Errore("ALLEGATO_TIPO_NON_AMMESSO", perc + ".FileType",
                                  f"{ft!r} non tra {list(L.TIPI_FILE_EG)}", L.FONTE_FILEATTACHMENT))
            elif rilevato and (ft == "application/pdf") != (rilevato == "application/pdf"):
                err.append(Errore("ALLEGATO_TIPO_INCOERENTE", perc + ".FileType",
                                  f"FileType {ft!r} ma contenuto {rilevato}", L.FONTE_FILEATTACHMENT))
        if a.get("nome_eg") is not None:
            err += valida_nome_file_eg(a["nome_eg"], perc + ".FileName")
        if "esito_validazione" in a and a["esito_validazione"] != "conforme":
            err.append(Errore("ALLEGATO_CONFORMITA_NON_DIMOSTRATA", perc,
                              f"esito della validazione: {a['esito_validazione']!r}; allegati non conformi causano lo "
                              "scarto della dichiarazione", L.FONTE_FORMATI))
    if richiedi_xml and manifest.get("xml") is None:
        err.append(Errore("FORNITURA_XML_ASSENTE", "fornitura.xml",
                          "XML della fornitura non indicato: la misura degli allegati e' solo un limite inferiore",
                          L.FONTE_FORNITURA))
    m = misura_fornitura(manifest, punto_misura)
    if m["bytes"] > limite_compresso:
        err.append(Errore("FORNITURA_OLTRE_LIMITE", "fornitura",
                          f"{m['misura']} > limite {descrivi_byte(limite_compresso)}; punto di misura: "
                          f"{m['punto_misura']} ({m['descrizione']}). Oltre il limite la dichiarazione va presentata "
                          "presso un ufficio territoriale", L.FONTE_FORNITURA))
    return err


# ------------------------------------------------------------------------------------------ conformita' allegati EG

def valuta_conformita_eg(percorso: Path | str, rapporto: dict | str | None = None,
                         esito_validazione: str | None = None) -> dict:
    """Esito della conformita' di un allegato del quadro EG ai formati ammessi (PDF/A-1a, PDF/A-1b, TIFF: Specifiche_SUC13
    p. 7 par. 2.3; Fascicolo I p. PDF 49), per l'esportazione.

    Restituisce ``{"esito": "conforme" | "non_conforme" | "non_verificato", "motivo": str, "fonte": str}``:

    * ``conforme`` solo se un validatore indipendente lo ha accertato (``esito_validazione`` o ``rapporto.validazione.esito``
      = 'conforme', come scritto da ``allegati.prepara_pdfa`` con veraPDF);
    * ``non_conforme`` se il rapporto dice 'non_conforme', se un TIFF non supera la verifica dei requisiti (``tiff.verifica_tiff``:
      B/N 1 bit, CCITT Group IV, max 300 DPI), se un PDF non dichiara PDF/A-1a/1b nei metadati (nessuna conversione) o se la
      verifica strutturale interna trova violazioni (``pdfa_strutturale``: indicativa, ma ogni motivo e' una violazione del
      profilo). Allegati non conformi causano lo scarto della dichiarazione (stessa regola di ``verifica_fornitura``);
    * ``non_verificato`` negli altri casi (PDF che dichiara PDF/A-1 senza esito di veraPDF, TIFF con verifica indicativa ok)."""
    p = Path(percorso)
    if isinstance(rapporto, str):
        try:
            rapporto = json.loads(rapporto)
        except ValueError:
            rapporto = None
    val = (rapporto or {}).get("validazione") if isinstance(rapporto, dict) else None
    dichiarato = esito_validazione or (val.get("esito") if isinstance(val, dict) else None)
    fonte = L.FONTE_FORMATI
    if dichiarato == "non_conforme":
        return {"esito": "non_conforme", "motivo": "il rapporto di validazione dell'allegato e' 'non_conforme'", "fonte": fonte}
    tipo = tipo_file_eg(p)
    if tipo == "image/tiff":
        from .tiff import verifica_tiff
        vt = verifica_tiff(p)
        if vt["esito"] != "indicativo_ok":
            motivi = "; ".join(m["messaggio"] for m in vt.get("motivi", [])[:5])
            return {"esito": "non_conforme", "motivo": f"TIFF fuori specifica: {motivi}", "fonte": L.FONTE_TIFF}
        return {"esito": "conforme" if dichiarato == "conforme" else "non_verificato",
                "motivo": "TIFF: requisiti verificati in modo indicativo (nessun validatore indipendente)", "fonte": L.FONTE_TIFF}
    if tipo != "application/pdf":
        return {"esito": "non_conforme", "motivo": "contenuto non PDF ne' TIFF", "fonte": fonte}
    if dichiarato == "conforme":
        return {"esito": "conforme", "motivo": "validazione indipendente: conforme", "fonte": fonte}
    from .. import pdfa
    an = pdfa.analizza_pdf(p)
    livello = an.get("dichiara_pdfa")
    if livello not in ("1a", "1b"):
        return {"esito": "non_conforme", "motivo": "PDF senza conversione PDF/A dimostrata: i metadati non dichiarano PDF/A-1a o "
                f"PDF/A-1b (rilevato: {livello or 'nessuna dichiarazione PDF/A'}); convertirlo con 'Prepara PDF/A'", "fonte": fonte}
    from .pdfa_strutturale import verifica_strutturale_pdfa
    ind = verifica_strutturale_pdfa(p, livello)
    if ind["esito"] != "indicativo_ok":
        codici = ", ".join(sorted({m["codice"] for m in ind.get("motivi", [])})[:8])
        return {"esito": "non_conforme", "motivo": f"dichiara PDF/A-{livello} ma la verifica strutturale trova violazioni ({codici})",
                "fonte": fonte}
    return {"esito": "non_verificato", "motivo": f"dichiara PDF/A-{livello} e supera la verifica strutturale interna, ma la "
            "conformita' non e' accertata da un validatore indipendente (veraPDF)", "fonte": fonte}
