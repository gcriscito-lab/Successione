"""Analisi, conversione PDF -> PDF/A (Ghostscript) e validazione (veraPDF).

Regola di progetto: un convertitore con esito positivo o metadati PDF/A NON prova la
conformita'. L'esito "conforme" si emette solo con il rapporto di un validatore indipendente
(veraPDF). Senza validatore l'esito e' "non_verificato" e il motivo e' esplicito.
"""
from __future__ import annotations

import glob
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError

# Dai materiali forniti (specifiche locali, pp. 7 e 3): da riverificare sulle specifiche aggiornate.
LIMITE_ALLEGATO_BYTE = 5 * 1000 * 1000      # prudenziale: 5 MB decimali finche' l'unita' non e' accertata
LIMITE_FORNITURA_BYTE = 40 * 1000 * 1000
PROFILI_AMMESSI = ("1a", "1b")


class StrumentoMancante(RuntimeError):
    pass


def analizza_pdf(percorso: Path | str) -> dict:
    p = Path(percorso)
    out: dict = {"bytes": p.stat().st_size, "formato": "sconosciuto"}
    with open(p, "rb") as f:
        testa = f.read(8)
    if not testa.startswith(b"%PDF-"):
        return {**out, "formato": "non_pdf", "esito": "non_pdf"}
    out["formato"] = "pdf"
    try:
        r = PdfReader(str(p))
    except (PyPdfError, OSError, ValueError) as e:
        return {**out, "esito": "danneggiato", "dettaglio": str(e)[:200]}
    if r.is_encrypted:
        return {**out, "esito": "protetto", "dettaglio": "PDF cifrato/protetto: serve la versione non protetta"}
    try:
        out["pagine"] = len(r.pages)
        campi = r.get_fields() or {}
        out["firme_digitali"] = sum(1 for v in campi.values() if str(v.get("/FT")) == "/Sig")
        xmp = r.xmp_metadata
        meta = ""
        if xmp is not None:
            try:
                meta = xmp.stream.get_data().decode("utf-8", "ignore")
            except Exception:
                meta = ""
        m = re.search(r"pdfaid:part[>=\"' ]+(\d)", meta)
        c = re.search(r"pdfaid:conformance[>=\"' ]+([ABUab])", meta)
        out["dichiara_pdfa"] = f"{m.group(1)}{c.group(1).lower()}" if m and c else None
    except Exception as e:  # file letto ma struttura anomala
        return {**out, "esito": "danneggiato", "dettaglio": f"struttura anomala: {str(e)[:150]}"}
    out["esito"] = "firmato" if out["firme_digitali"] else "leggibile"
    out["avvisi"] = []
    if out["bytes"] > LIMITE_ALLEGATO_BYTE:
        out["avvisi"].append("supera il limite di 5 MB per allegato: occorre ridurre o suddividere")
    if out["firme_digitali"]:
        out["avvisi"].append("firma digitale presente: la riscrittura in PDF/A non ne conserva la validita'")
    return out


def _icc() -> str | None:
    env = os.environ.get("SUCCESSIONI_ICC")
    if env and Path(env).exists():
        return env
    for pat in ("/usr/share/ghostscript/*/iccprofiles/srgb.icc", "/usr/share/color/icc/ghostscript/srgb.icc",
                "C:/Program Files/gs/*/iccprofiles/srgb.icc"):
        h = glob.glob(pat)
        if h:
            return h[0]
    return None


def trova_gs() -> str | None:
    for n in (os.environ.get("SUCCESSIONI_GS"), "gs", "gswin64c", "gswin32c"):
        if n and shutil.which(n):
            return shutil.which(n)
    return None


def converti_in_pdfa(src: Path | str, dst: Path | str, livello: str = "1b") -> dict:
    """Converte con Ghostscript. Restituisce i dati dell'operazione, NON un giudizio di conformita'."""
    if livello not in PROFILI_AMMESSI:
        raise ValueError("livello ammesso: 1a o 1b")
    if livello == "1a":
        raise NotImplementedError("PDF/A-1a richiede struttura taggata: non producibile da Ghostscript; usare 1b")
    gs, icc = trova_gs(), _icc()
    if not gs or not icc:
        raise StrumentoMancante("Ghostscript o profilo ICC sRGB non trovati (SUCCESSIONI_GS / SUCCESSIONI_ICC)")
    src, dst = Path(src), Path(dst)
    with tempfile.TemporaryDirectory() as t:
        icc_ps = icc.replace("\\", "/")
        deff = Path(t) / "PDFA_def.ps"
        deff.write_text(
            "%!\n/ICCProfile (" + icc_ps + ") def\n[/_objdef {icc_PDFA} /type /stream /OBJ pdfmark\n"
            "[{icc_PDFA} <</N 3>> /PUT pdfmark\n[{icc_PDFA} ICCProfile (r) file /PUT pdfmark\n"
            "[/_objdef {OutputIntent_PDFA} /type /dict /OBJ pdfmark\n"
            "[{OutputIntent_PDFA} <</Type /OutputIntent /S /GTS_PDFA1 /DestOutputProfile {icc_PDFA} "
            "/OutputConditionIdentifier (sRGB) /Info (sRGB)>> /PUT pdfmark\n"
            "[{Catalog} <</OutputIntents [ {OutputIntent_PDFA} ]>> /PUT pdfmark\n")
        cmd = [gs, "-dPDFA=1", "-dBATCH", "-dNOPAUSE", "-dQUIET", "-dNOOUTPUTFONTS=false",
               "-sColorConversionStrategy=RGB", "-sProcessColorModel=DeviceRGB",
               "-dPDFACompatibilityPolicy=1", "-sDEVICE=pdfwrite", "-dSAFER",
               f"--permit-file-read={icc}", f"-sOutputFile={dst}", str(deff), str(src)]
        pr = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    ok = pr.returncode == 0 and dst.exists() and dst.stat().st_size > 0
    return {"strumento": "ghostscript", "comando_ok": ok, "stderr": pr.stderr[-500:],
            "livello_richiesto": livello}


def trova_verapdf() -> str | None:
    for n in (os.environ.get("SUCCESSIONI_VERAPDF"), "verapdf"):
        if n and shutil.which(n):
            return shutil.which(n)
    return None


def valida_pdfa(percorso: Path | str, livello: str = "1b") -> dict:
    """Validazione indipendente con veraPDF. Senza veraPDF: esito 'non_verificato'."""
    vp = trova_verapdf()
    if not vp:
        return {"esito": "non_verificato", "validatore": None,
                "motivo": "veraPDF non installato/configurato (SUCCESSIONI_VERAPDF): conformita' non dimostrata"}
    flavour = {"1a": "1a", "1b": "1b"}[livello]
    pr = subprocess.run([vp, "--flavour", flavour, "--format", "xml", str(percorso)],
                        capture_output=True, text=True, timeout=300)
    m = re.search(r'isCompliant="(true|false)"', pr.stdout)
    if not m:
        return {"esito": "non_verificato", "validatore": vp, "motivo": "rapporto veraPDF non interpretabile",
                "stderr": pr.stderr[-300:]}
    return {"esito": "conforme" if m.group(1) == "true" else "non_conforme", "validatore": vp,
            "profilo": livello, "rapporto_xml": pr.stdout}
