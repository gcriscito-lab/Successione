"""Anteprima e confronto visivo originale/derivato (indicatore di fedelta', NON una prova).

Le pagine sono rese con Ghostscript (png16m, bassa risoluzione) e confrontate pixel per pixel con Pillow (gia'
richiesto da reportlab). L'esito e' "simili" oppure "da_controllare": la fedelta' visiva e la leggibilita' restano da
verificare con l'anteprima da parte dell'utente su un insieme rappresentativo (specifica par. 7).
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

SOGLIA_MEDIA = 6.0          # differenza media per canale (0-255) oltre la quale la pagina va controllata
SOGLIA_PIXEL = 0.03         # quota di pixel con differenza > 64 oltre la quale la pagina va controllata


def rendi_pagine(pdf: Path | str, cartella: Path | str, dpi: int = 40, timeout: int = 300) -> list[Path]:
    from ..pdfa import StrumentoMancante, trova_gs
    gs = trova_gs()
    if not gs:
        raise StrumentoMancante("Ghostscript non trovato (SUCCESSIONI_GS)")
    d = Path(cartella)
    d.mkdir(parents=True, exist_ok=True)
    modello = d / (Path(pdf).stem + "_p%05d.png")
    subprocess.run([gs, "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-sDEVICE=png16m", f"-r{int(dpi)}",
                    "-dTextAlphaBits=4", "-dGraphicsAlphaBits=4", f"-sOutputFile={modello}", str(pdf)],
                   capture_output=True, timeout=timeout)
    return sorted(d.glob(Path(pdf).stem + "_p*.png"))


def confronta_visivo(originale: Path | str, derivato: Path | str, *, dpi: int = 40,
                     soglia_media: float = SOGLIA_MEDIA, soglia_pixel: float = SOGLIA_PIXEL) -> dict:
    """Confronto pagina per pagina. Pagine mancanti o di dimensioni diverse sono sempre 'da_controllare'."""
    from PIL import Image, ImageChops, ImageStat
    with tempfile.TemporaryDirectory() as t:
        a = rendi_pagine(originale, Path(t) / "a", dpi)
        b = rendi_pagine(derivato, Path(t) / "b", dpi)
        pagine = []
        for i in range(max(len(a), len(b))):
            voce: dict = {"pagina": i + 1}
            if i >= len(a) or i >= len(b):
                voce["problema"] = "pagina assente in uno dei due file"
            else:
                ia, ib = Image.open(a[i]).convert("RGB"), Image.open(b[i]).convert("RGB")
                if ia.size != ib.size:
                    voce["problema"] = f"dimensioni diverse {ia.size} / {ib.size}"
                else:
                    diff = ImageChops.difference(ia, ib)
                    voce["diff_media"] = round(sum(ImageStat.Stat(diff).mean) / 3, 3)
                    grigio = diff.convert("L").point(lambda v: 255 if v > 64 else 0)
                    voce["quota_pixel_diversi"] = round(ImageStat.Stat(grigio).mean[0] / 255, 4)
                    if voce["diff_media"] > soglia_media or voce["quota_pixel_diversi"] > soglia_pixel:
                        voce["problema"] = "differenza visiva oltre soglia"
            pagine.append(voce)
    da_controllare = [p["pagina"] for p in pagine if "problema" in p]
    return {"esito": "da_controllare" if da_controllare or not pagine else "simili", "dpi": dpi,
            "soglie": {"diff_media": soglia_media, "quota_pixel_diversi": soglia_pixel},
            "pagine_da_controllare": da_controllare, "pagine": pagine,
            "dichiarazione": "indicatore automatico a bassa risoluzione: non sostituisce l'anteprima dell'utente"}
