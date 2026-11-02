"""Analisi, conversione PDF -> PDF/A (Ghostscript) e validazione (veraPDF).

Regola di progetto: un convertitore con esito positivo o metadati PDF/A NON prova la
conformita'. L'esito "conforme" si emette solo con il rapporto di un validatore indipendente
(veraPDF). Senza validatore l'esito e' "non_verificato" e il motivo e' esplicito. Il verificatore
strutturale interno (``documenti.pdfa_strutturale``) produce soltanto un'indicazione
("indicativo_ok" / "indicativo_ko") e non sostituisce veraPDF.

Limiti e formati: vedi ``documenti.limiti`` (fonte: Specifiche_SUC13_20250702.pdf p.3 e p.7).
"""
from __future__ import annotations

import glob
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from lxml import etree
from pypdf import PdfReader
from pypdf.errors import PyPdfError

from .documenti.limiti import LIMITE_ALLEGATO_DECIMALE, LIMITE_FORNITURA_DECIMALE

# Specifiche_SUC13_20250702.pdf p.7 par. 2.3 (5 MB per allegato) e p.3 par. 1 (40 MB compressi).
# Unita' effettiva non accertata: valore DECIMALE (piu' severo) finche' non si prova con CIVIS.
LIMITE_ALLEGATO_BYTE = LIMITE_ALLEGATO_DECIMALE
LIMITE_FORNITURA_BYTE = LIMITE_FORNITURA_DECIMALE
PROFILI_AMMESSI = ("1a", "1b")

_FINESTRA_CODA = 4096


class StrumentoMancante(RuntimeError):
    pass


# ---------------------------------------------------------------------------------------------- analisi

def _controllo_chiusura(dati: bytes) -> str | None:
    """None se la coda del file e' coerente (startxref + %%EOF + xref raggiungibile), altrimenti il motivo."""
    coda = dati[-_FINESTRA_CODA:]
    i = coda.rfind(b"startxref")
    if i < 0:
        return "manca 'startxref' in coda: file troncato o incompleto"
    m = re.match(rb"startxref\s+(\d+)", coda[i:])
    if not m:
        return "'startxref' senza offset valido"
    if b"%%EOF" not in coda[i:]:
        return "manca '%%EOF' dopo 'startxref': file troncato"
    off = int(m.group(1))
    if off >= len(dati):
        return "l'offset della tabella xref e' oltre la fine del file"
    testa = dati[off:off + 40]
    if not (testa.startswith(b"xref") or re.match(rb"\d+\s+\d+\s+obj", testa)):
        # alcuni file hanno byte iniziali estranei prima di %PDF: tolleranza di 1 KB sull'offset
        scarto = dati.find(b"%PDF-", 0, 1024)
        t2 = dati[off + scarto:off + scarto + 40] if scarto > 0 else b""
        if not (t2.startswith(b"xref") or re.match(rb"\d+\s+\d+\s+obj", t2)):
            return "'startxref' non punta a una tabella/stream xref valida"
    return None


def _conta_firme(reader: PdfReader, dati: bytes) -> tuple[int, int]:
    """(firme apposte, campi firma vuoti). Una firma apposta ha /V nel campo /FT /Sig."""
    firmate = vuote = 0
    campi = reader.get_fields() or {}
    for v in campi.values():
        if str(v.get("/FT")) == "/Sig":
            if v.get("/V") is not None:
                firmate += 1
            else:
                vuote += 1
    if not firmate and b"/ByteRange" in dati:
        # firma non raggiungibile dai campi AcroForm: segnalata comunque (prudenza)
        firmate = dati.count(b"/ByteRange")
    return firmate, vuote


def analizza_pdf(percorso: Path | str) -> dict:
    """Classifica il file: non_pdf | danneggiato | protetto | firmato | leggibile (e dati utili)."""
    p = Path(percorso)
    dati = p.read_bytes()
    out: dict = {"bytes": len(dati), "formato": "sconosciuto"}
    if not dati.startswith(b"%PDF-"):
        if dati[:4] in (b"II*\x00", b"MM\x00*"):
            from .documenti.tiff import verifica_tiff
            vt = verifica_tiff(p)
            return {**out, "formato": "tiff", "esito": "tiff", "pagine": vt.get("pagine"), "verifica_tiff": vt,
                    "dettaglio": "file TIFF: non si converte in PDF/A; requisiti di Specifiche p.7 verificati in "
                                 f"modo indicativo ({vt['esito']})"}
        return {**out, "formato": "non_pdf", "esito": "non_pdf"}
    out["formato"] = "pdf"
    try:
        r = PdfReader(str(p))
    except (PyPdfError, OSError, ValueError) as e:
        return {**out, "esito": "danneggiato", "dettaglio": str(e)[:200]}
    if r.is_encrypted:
        try:
            senza_password = bool(r.decrypt(""))
        except Exception:
            senza_password = False
        det = ("PDF cifrato/protetto: serve la versione non protetta (il PDF/A vieta la cifratura)"
               + (" - si apre con password utente vuota ma ha restrizioni/cifratura attive" if senza_password else ""))
        return {**out, "esito": "protetto", "dettaglio": det, "apribile_senza_password": senza_password}
    problema = _controllo_chiusura(dati)
    if problema:
        # pypdf ricostruisce spesso la xref di un file troncato e restituisce MENO pagine senza errore:
        # convertirlo perderebbe pagine in silenzio. Respinto.
        try:
            n = len(r.pages)
        except Exception:
            n = None
        return {**out, "esito": "danneggiato", "pagine_recuperabili": n,
                "dettaglio": f"struttura incompleta ({problema}): fornire il file integro"}
    try:
        out["pagine"] = len(r.pages)
        for pg in r.pages:           # forza la lettura dell'albero e dei contenuti di ogni pagina
            pg.get("/Contents")
        firmate, vuote = _conta_firme(r, dati)
        out["firme_digitali"] = firmate
        out["campi_firma_vuoti"] = vuote
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
    if out["campi_firma_vuoti"]:
        out["avvisi"].append("campi firma non firmati presenti: nel derivato i campi modulo possono essere appiattiti")
    if out["dichiara_pdfa"]:
        out["avvisi"].append(f"dichiara PDF/A-{out['dichiara_pdfa']} nei metadati: la conformita' non e' verificata "
                             "(solo veraPDF la accerta)")
    return out


# ------------------------------------------------------------------------------------------ conversione

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


_RE_FONT = re.compile(r"Loading font (.+?) \(or substitute\) from (.+)")


def converti_in_pdfa(src: Path | str, dst: Path | str, livello: str = "1b", *,
                     risoluzione_dpi: int | None = None, qfactor_jpeg: float = 0.4,
                     scala_di_grigi: bool = False, timeout: int = 300) -> dict:
    """Converte con Ghostscript. Restituisce i dati dell'operazione, NON un giudizio di conformita'.

    ``risoluzione_dpi``: se indicato, riduce a quella risoluzione le immagini a colori/grigi (soglia 1.0) e le
    ricodifica JPEG con ``qfactor_jpeg`` (0.1 qualita' alta ... 1.3 bassa). Le immagini 1 bit non sono toccate.
    ``scala_di_grigi``: converte tutto in grigi (il Fascicolo 1 p.49 indica "colore Bianco e Nero").
    Senza questi parametri il comportamento e' quello della conversione semplice.
    """
    if livello not in PROFILI_AMMESSI:
        raise ValueError("livello ammesso: 1a o 1b")
    if livello == "1a":
        raise NotImplementedError("PDF/A-1a richiede struttura taggata: non producibile da Ghostscript; usare 1b")
    gs, icc = trova_gs(), _icc()
    if not gs or not icc:
        raise StrumentoMancante("Ghostscript o profilo ICC sRGB non trovati (SUCCESSIONI_GS / SUCCESSIONI_ICC)")
    src, dst = Path(src), Path(dst)
    if src.resolve() == dst.resolve():
        raise ValueError("il derivato deve avere un percorso diverso dall'originale")
    modello = "DeviceGray" if scala_di_grigi else "DeviceRGB"
    strategia = "Gray" if scala_di_grigi else "RGB"
    with tempfile.TemporaryDirectory() as t:
        # Ghostscript Windows rifiuta alcuni percorsi assoluti oltre MAX_PATH,
        # anche quando Python puo' leggerli. Lavora su copie con nomi brevi:
        # l'originale e i percorsi dell'utente non entrano nel programma PostScript.
        lavoro = Path(t)
        shutil.copyfile(src, lavoro / 'input.pdf')
        shutil.copyfile(icc, lavoro / 'srgb.icc')
        icc_ps = 'srgb.icc'
        deff = Path(t) / "successioni_pdfa_def.ps"
        ps = ("%!\n/ICCProfile (" + icc_ps + ") def\n[/_objdef {icc_PDFA} /type /stream /OBJ pdfmark\n"
              "[{icc_PDFA} <</N 3>> /PUT pdfmark\n[{icc_PDFA} ICCProfile (r) file /PUT pdfmark\n"
              "[/_objdef {OutputIntent_PDFA} /type /dict /OBJ pdfmark\n"
              "[{OutputIntent_PDFA} <</Type /OutputIntent /S /GTS_PDFA1 /DestOutputProfile {icc_PDFA} "
              "/OutputConditionIdentifier (sRGB) /Info (sRGB)>> /PUT pdfmark\n"
              "[{Catalog} <</OutputIntents [ {OutputIntent_PDFA} ]>> /PUT pdfmark\n")
        extra: list[str] = []
        if risoluzione_dpi:
            q = float(qfactor_jpeg)
            ps += (f"<< /ColorImageDict << /QFactor {q} /Blend 1 /HSamples [2 1 1 2] /VSamples [2 1 1 2] >> "
                   f"/ColorACSImageDict << /QFactor {q} /Blend 1 /HSamples [2 1 1 2] /VSamples [2 1 1 2] >> "
                   f"/GrayImageDict << /QFactor {q} /Blend 1 /HSamples [1 1 1 1] /VSamples [1 1 1 1] >> "
                   f"/GrayACSImageDict << /QFactor {q} /Blend 1 /HSamples [1 1 1 1] /VSamples [1 1 1 1] >> >> "
                   "setdistillerparams\n")
            r = int(risoluzione_dpi)
            extra = ["-dDownsampleColorImages=true", "-dDownsampleGrayImages=true", "-dDownsampleMonoImages=false",
                     f"-dColorImageResolution={r}", f"-dGrayImageResolution={r}",
                     "-dColorImageDownsampleType=/Bicubic", "-dGrayImageDownsampleType=/Bicubic",
                     "-dColorImageDownsampleThreshold=1.0", "-dGrayImageDownsampleThreshold=1.0",
                     "-dAutoFilterColorImages=false", "-dColorImageFilter=/DCTEncode",
                     "-dAutoFilterGrayImages=false", "-dGrayImageFilter=/DCTEncode"]
        deff.write_text(ps, encoding='ascii')
        cmd = [gs, "-dPDFA=1", "-dBATCH", "-dNOPAUSE", "-dNOOUTPUTFONTS=false",
               f"-sColorConversionStrategy={strategia}", f"-sProcessColorModel={modello}",
               "-dPDFACompatibilityPolicy=1", "-sDEVICE=pdfwrite", "-dSAFER", *extra,
               "--permit-file-read=srgb.icc", "-sOutputFile=derivato.pdf", deff.name, 'input.pdf']
        pr = subprocess.run(cmd, cwd=lavoro, capture_output=True, text=True, timeout=timeout)
        testo = (pr.stdout or "") + "\n" + (pr.stderr or "")
        abortita = "PDF/A processing aborted" in testo
        generato = lavoro / 'derivato.pdf'
        ok = pr.returncode == 0 and generato.is_file() and generato.stat().st_size > 0 and not abortita
        if ok:
            shutil.copyfile(generato, dst)
    testo = (pr.stdout or "") + "\n" + (pr.stderr or "")
    font = [{"nome": m.group(1), "sostituto": Path(m.group(2).strip()).name} for m in _RE_FONT.finditer(testo)]
    avvisi_gs = [ln.strip() for ln in testo.splitlines()
                 if re.search(r"warning|\*\*\*\*|error|abort", ln, re.I)][:10]
    esito = {"strumento": "ghostscript", "comando_ok": ok, "stderr": (pr.stderr or "")[-500:],
             "livello_richiesto": livello, "parametri": {"risoluzione_dpi": risoluzione_dpi,
                                                          "scala_di_grigi": scala_di_grigi,
                                                          "qfactor_jpeg": qfactor_jpeg if risoluzione_dpi else None},
             "font_non_incorporati_sostituiti": font, "avvisi_gs": avvisi_gs}
    if abortita:
        esito["errore"] = "Ghostscript ha interrotto l'elaborazione PDF/A (profilo ICC o permessi): output non valido"
    return esito


# ----------------------------------------------------------------------------------------- validazione

def trova_verapdf() -> str | None:
    for n in (os.environ.get("SUCCESSIONI_VERAPDF"), "verapdf"):
        if n and shutil.which(n):
            return shutil.which(n)
    return None


def _versione_verapdf(vp: str) -> str | None:
    try:
        pr = subprocess.run([vp, "--version"], capture_output=True, text=True, timeout=60)
        return (pr.stdout or pr.stderr).strip()[:300] or None
    except (OSError, subprocess.SubprocessError):
        return None


def interpreta_rapporto_verapdf(xml_testo: str) -> dict:
    """Interpreta il rapporto XML di veraPDF (formato predefinito = MRR).

    Struttura documentata: ``report/jobs/job/validationReport`` con attributi ``profileName``, ``statement`` e
    ``isCompliant`` (https://docs.verapdf.org/cli/validation/). Restituisce {"interpretabile": bool, ...}.
    """
    try:
        parser = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False)
        radice = etree.fromstring(xml_testo.encode("utf-8"), parser)
    except (etree.XMLSyntaxError, ValueError):
        return {"interpretabile": False, "motivo": "XML non ben formato"}
    rapporti = [e for e in radice.iter() if isinstance(e.tag, str) and etree.QName(e).localname == "validationReport"]
    if len(rapporti) != 1:
        return {"interpretabile": False, "motivo": f"attesi 1 validationReport, trovati {len(rapporti)}"}
    rep = rapporti[0]
    valore = rep.get("isCompliant")
    if valore not in ("true", "false"):
        return {"interpretabile": False, "motivo": "attributo isCompliant assente o non booleano"}
    fallite = []
    for r in rep.iter():
        if isinstance(r.tag, str) and etree.QName(r).localname == "rule" and r.get("status") == "failed":
            desc = next((d.text for d in r if isinstance(d.tag, str) and etree.QName(d).localname == "description"), "")
            fallite.append({"specifica": r.get("specification"), "clausola": r.get("clause"),
                            "test": r.get("testNumber"), "descrizione": (desc or "").strip()[:300]})
    errori_job = [e.text for e in radice.iter() if isinstance(e.tag, str)
                  and etree.QName(e).localname in ("exceptionMessage",) and e.text]
    return {"interpretabile": True, "conforme": valore == "true", "profilo_rapporto": rep.get("profileName"),
            "dichiarazione": rep.get("statement"), "regole_fallite": fallite[:50], "errori_job": errori_job[:5]}


def valida_pdfa(percorso: Path | str, livello: str = "1b") -> dict:
    """Validazione indipendente con veraPDF. Senza veraPDF: esito 'non_verificato'.

    In ogni caso allega ``verifica_indicativa`` (controlli strutturali interni, NON una prova di conformita').
    """
    if livello not in PROFILI_AMMESSI:
        raise ValueError("livello ammesso: 1a o 1b")
    from .documenti.pdfa_strutturale import verifica_strutturale_pdfa
    ind = verifica_strutturale_pdfa(percorso, livello)
    vp = trova_verapdf()
    if not vp:
        return {"esito": "non_verificato", "validatore": None, "esito_collaudo": "da_collaudare",
                "motivo": "veraPDF non installato/configurato (SUCCESSIONI_VERAPDF): conformita' non dimostrata",
                "verifica_indicativa": ind}
    try:
        pr = subprocess.run([vp, "--flavour", livello, str(percorso)], capture_output=True, text=True,
                            timeout=300)
    except (OSError, subprocess.SubprocessError) as e:
        return {"esito": "non_verificato", "validatore": vp, "motivo": f"veraPDF non eseguibile: {str(e)[:200]}",
                "verifica_indicativa": ind}
    rep = interpreta_rapporto_verapdf(pr.stdout or "")
    if not rep["interpretabile"]:
        return {"esito": "non_verificato", "validatore": vp, "motivo": "rapporto veraPDF non interpretabile: "
                + rep["motivo"], "stderr": (pr.stderr or "")[-300:], "verifica_indicativa": ind}
    return {"esito": "conforme" if rep["conforme"] else "non_conforme", "validatore": vp,
            "versione_validatore": _versione_verapdf(vp), "profilo": livello,
            "profilo_rapporto": rep["profilo_rapporto"], "regole_fallite": rep["regole_fallite"],
            "rapporto_xml": pr.stdout, "verifica_indicativa": ind}
