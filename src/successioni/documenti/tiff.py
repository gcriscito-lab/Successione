"""TIFF per gli allegati EG: verifica dei requisiti dichiarati e conversione PDF -> TIFF CCITT G4.

Requisiti (Specifiche_SUC13_20250702.pdf p.7 par. 2.3): "TIF e/o TIFF: tali formati sono prodotti a fronte della
scansione del documento. Ai fini dell'accettazione e' necessario utilizzare una risoluzione non superiore a 300 DPI,
selezionare il colore B/N e specificare la Compressione CCITT Group IV (modalita' Fax)." FileType ammessi: image/tif,
image/tiff (typesReg_v2.xsd FileType_Type). Indicazione di prassi: 200x200 dpi B/N (Fascicolo I p.49).

Corrispondenza con i campi TIFF 6.0 (scelta tecnica del progetto, da confermare con il servizio CIVIS):
  * CCITT Group IV  -> Compression (259) = 4 ("CCITT T.6 bi-level encoding");
  * B/N             -> BitsPerSample (258) = 1, SamplesPerPixel (277) = 1, PhotometricInterpretation (262) 0 o 1;
  * <= 300 DPI      -> XResolution (282) e YResolution (283) <= 300 con ResolutionUnit (296) 2=pollice / 3=cm.
Incognite: TIFF multipagina (non citato dalle specifiche: accettato qui, da collaudare); TIFF senza risoluzione
dichiarata o con ResolutionUnit=1 (respinto in via prudenziale). L'esito e' INDICATIVO: l'accettazione effettiva la
stabilisce il controllo dell'Agenzia (CIVIS / software di controllo), da collaudare.
"""
from __future__ import annotations

import struct
import subprocess
from pathlib import Path

from . import limiti as L

TAG_COMPRESSIONE, TAG_BPS, TAG_SPP, TAG_FOTOMETRIA = 259, 258, 277, 262
TAG_XRES, TAG_YRES, TAG_UNITA = 282, 283, 296
TAG_LARGHEZZA, TAG_ALTEZZA = 256, 257
# 273/279 StripOffsets/StripByteCounts, 324/325 TileOffsets/TileByteCounts: controllo di troncamento.
COMPRESSIONE_G4 = 4
_DIM_TIPO = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8}
_FMT_TIPO = {1: "B", 3: "H", 4: "I", 6: "b", 8: "h", 9: "i", 11: "f", 12: "d"}
MAX_IFD = 10000

DICHIARAZIONE = ("Verifica INDICATIVA dei soli requisiti di Specifiche p.7 (<=300 DPI, B/N, CCITT Group IV): "
                 "l'accettazione dipende dal controllo dell'Agenzia (CIVIS), da collaudare.")


class TiffNonLeggibile(ValueError):
    pass


def _leggi_ifd(dati: bytes) -> list[dict[int, tuple]]:
    """Restituisce, per ogni pagina (IFD), {tag: valori}. Solo TIFF classico (non BigTIFF)."""
    if dati[:4] == b"II*\x00":
        e = "<"
    elif dati[:4] == b"MM\x00*":
        e = ">"
    elif dati[:4] in (b"II+\x00", b"MM\x00+"):
        raise TiffNonLeggibile("BigTIFF non supportato")
    else:
        raise TiffNonLeggibile("intestazione TIFF assente")
    (off,) = struct.unpack(e + "I", dati[4:8])
    pagine, visti = [], set()
    while off:
        if off in visti or len(pagine) >= MAX_IFD:
            raise TiffNonLeggibile("catena di IFD ciclica o eccessiva")
        visti.add(off)
        if off + 2 > len(dati):
            raise TiffNonLeggibile("IFD oltre la fine del file (troncato)")
        (n,) = struct.unpack(e + "H", dati[off:off + 2])
        fine = off + 2 + 12 * n
        if fine + 4 > len(dati):
            raise TiffNonLeggibile("IFD incompleta (file troncato)")
        tag: dict[int, tuple] = {}
        for i in range(n):
            voce = dati[off + 2 + 12 * i: off + 14 + 12 * i]
            t, tipo, cnt = struct.unpack(e + "HHI", voce[:8])
            dim = _DIM_TIPO.get(tipo)
            if dim is None:
                continue
            tot = dim * cnt
            if tot <= 4:
                grezzo = voce[8:8 + tot]
            else:
                (p,) = struct.unpack(e + "I", voce[8:12])
                if p + tot > len(dati):
                    raise TiffNonLeggibile(f"valore del tag {t} oltre la fine del file")
                grezzo = dati[p:p + tot]
            if tipo in (5, 10):        # RATIONAL / SRATIONAL
                f = "I" if tipo == 5 else "i"
                v = struct.unpack(e + f * (2 * cnt), grezzo)
                tag[t] = tuple((v[2 * k] / v[2 * k + 1]) if v[2 * k + 1] else None for k in range(cnt))
            elif tipo == 2:
                tag[t] = (grezzo.rstrip(b"\x00").decode("latin-1"),)
            elif tipo in _FMT_TIPO:
                tag[t] = struct.unpack(e + _FMT_TIPO[tipo] * cnt, grezzo)
            else:
                tag[t] = (grezzo,)
        pagine.append(tag)
        (off,) = struct.unpack(e + "I", dati[fine:fine + 4])
    if not pagine:
        raise TiffNonLeggibile("nessuna immagine (IFD) nel file")
    return pagine


def verifica_tiff(percorso: Path | str, *, dpi_max: int = L.TIFF_DPI_MAX) -> dict:
    """Esito ``indicativo_ok`` / ``indicativo_ko`` (mai "conforme") con motivi per pagina."""
    p = Path(percorso)
    dati = p.read_bytes()
    base = {"formato": "tiff", "bytes": len(dati), "fonte": L.FONTE_TIFF, "dichiarazione": DICHIARAZIONE}
    try:
        pagine = _leggi_ifd(dati)
    except (TiffNonLeggibile, struct.error) as ex:
        return {**base, "esito": "indicativo_ko", "pagine": None,
                "motivi": [{"codice": "TIFF_ILLEGGIBILE", "pagina": None, "messaggio": str(ex)}]}
    motivi, dettaglio = [], []
    for i, t in enumerate(pagine, 1):
        compr = (t.get(TAG_COMPRESSIONE) or (1,))[0]
        bps = t.get(TAG_BPS) or (1,)
        spp = (t.get(TAG_SPP) or (1,))[0]
        foto = (t.get(TAG_FOTOMETRIA) or (None,))[0]
        unita = (t.get(TAG_UNITA) or (2,))[0]
        xr, yr = (t.get(TAG_XRES) or (None,))[0], (t.get(TAG_YRES) or (None,))[0]
        fattore = {2: 1.0, 3: 2.54}.get(unita)
        dpi = (round(xr * fattore, 2) if xr and fattore else None, round(yr * fattore, 2) if yr and fattore else None)
        dettaglio.append({"pagina": i, "compressione": compr, "bit_per_campione": list(bps), "campioni": spp,
                          "fotometria": foto, "dpi": list(dpi),
                          "dimensioni_px": [(t.get(TAG_LARGHEZZA) or (None,))[0], (t.get(TAG_ALTEZZA) or (None,))[0]]})
        off_strisce, len_strisce = t.get(273) or t.get(324), t.get(279) or t.get(325)   # strip o tile
        if not off_strisce or not len_strisce or len(off_strisce) != len(len_strisce):
            motivi.append({"codice": "TIFF_ILLEGGIBILE", "pagina": i, "messaggio": "dati immagine non localizzabili"})
        elif max(o + n for o, n in zip(off_strisce, len_strisce)) > len(dati):
            motivi.append({"codice": "TIFF_ILLEGGIBILE", "pagina": i,
                           "messaggio": "dati immagine oltre la fine del file (troncato)"})
        if compr != COMPRESSIONE_G4:
            motivi.append({"codice": "TIFF_COMPRESSIONE", "pagina": i,
                           "messaggio": f"Compression={compr}: richiesta CCITT Group IV (valore 4)"})
        if spp != 1 or any(b != 1 for b in bps) or foto not in (0, 1, None):
            motivi.append({"codice": "TIFF_NON_BN", "pagina": i,
                           "messaggio": f"non bianco e nero a 1 bit (BitsPerSample={list(bps)}, SamplesPerPixel={spp},"
                                        f" Photometric={foto})"})
        if fattore is None:
            motivi.append({"codice": "TIFF_RISOLUZIONE", "pagina": i,
                           "messaggio": f"ResolutionUnit={unita}: risoluzione in DPI non determinabile (prudenziale)"})
        elif dpi[0] is None or dpi[1] is None:
            motivi.append({"codice": "TIFF_RISOLUZIONE", "pagina": i,
                           "messaggio": "XResolution/YResolution assenti: risoluzione non verificabile (prudenziale)"})
        elif dpi[0] > dpi_max or dpi[1] > dpi_max:
            motivi.append({"codice": "TIFF_RISOLUZIONE", "pagina": i,
                           "messaggio": f"risoluzione {dpi[0]}x{dpi[1]} DPI oltre {dpi_max}"})
    return {**base, "esito": "indicativo_ko" if motivi else "indicativo_ok", "pagine": len(pagine),
            "motivi": motivi, "dettaglio_pagine": dettaglio}


def converti_in_tiff_g4(src: Path | str, dst: Path | str, *, dpi: int = L.DPI_PRASSI, timeout: int = 300) -> dict:
    """PDF -> TIFF multipagina B/N CCITT G4 con Ghostscript (dispositivo ``tiffg4``). ``dpi`` <= 300.

    Il documento diventa un'immagine: testo non piu' selezionabile, firma digitale non conservata."""
    from ..pdfa import StrumentoMancante, trova_gs
    if not 0 < int(dpi) <= L.TIFF_DPI_MAX:
        raise ValueError(f"dpi ammessi: 1..{L.TIFF_DPI_MAX} (Specifiche p.7)")
    gs = trova_gs()
    if not gs:
        raise StrumentoMancante("Ghostscript non trovato (SUCCESSIONI_GS)")
    src, dst = Path(src), Path(dst)
    cmd = [gs, "-dSAFER", "-dBATCH", "-dNOPAUSE", "-sDEVICE=tiffg4", f"-r{int(dpi)}", f"-sOutputFile={dst}", str(src)]
    pr = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    ok = pr.returncode == 0 and dst.exists() and dst.stat().st_size > 0
    out = {"strumento": "ghostscript tiffg4", "comando_ok": ok, "dpi": int(dpi), "stderr": (pr.stderr or "")[-500:]}
    if ok:
        out["verifica"] = verifica_tiff(dst)
    return out
