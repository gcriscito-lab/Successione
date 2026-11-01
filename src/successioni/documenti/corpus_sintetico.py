"""Corpus SINTETICO di prova per A11/A12 (nessun documento reale; contenuti generati da codice).

Uso:  ``python -m successioni.documenti.corpus_sintetico <cartella>``           genera il corpus e ``corpus.json``
      ``python -m successioni.documenti.corpus_sintetico <cartella> --collaudo`` genera e poi esegue conversione e
                                                                                validazione, scrivendo
                                                                                ``collaudo_a11.json``

La "firma" del file ``firmato_simulato.pdf`` e' SIMULATA: un dizionario /Sig con /ByteRange e /Contents fittizi, senza
alcun valore crittografico. Serve solo a provare il riconoscimento e l'avviso di firma non conservata.
I file di questo corpus non dimostrano compatibilita' con i servizi dell'Agenzia.
"""
from __future__ import annotations

import io
import json
import os
import platform
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import (ArrayObject, ByteStringObject, DecodedStreamObject, DictionaryObject, NameObject,
                           NumberObject, TextStringObject)

SILLABE = ("ca", "sa", "re", "di", "to", "mo", "na", "li", "ve", "ro", "pa", "te", "ni", "co", "la", "be", "su", "gu")
XMP_FALSO_PDFA = (
    b'<?xpacket begin="\xef\xbb\xbf" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
    b'<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
    b'<rdf:Description rdf:about="" xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/">'
    b'<pdfaid:part>1</pdfaid:part><pdfaid:conformance>B</pdfaid:conformance></rdf:Description>'
    b'</rdf:RDF></x:xmpmeta>\n<?xpacket end="w"?>')


def _font_incorporabile() -> str:
    """Registra in reportlab un TrueType incorporabile (Vera, distribuito con reportlab) e ne restituisce il nome."""
    import reportlab
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    if "VeraSint" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("VeraSint", str(Path(reportlab.__file__).parent / "fonts" / "Vera.ttf")))
    return "VeraSint"


def _parole(rnd: random.Random, n: int) -> str:
    return " ".join("".join(rnd.choice(SILLABE) for _ in range(rnd.randint(2, 4))) for _ in range(n))


def _immagine_scansione(larghezza: int, altezza: int, seme: int, rumore: float = 0.35):
    """Immagine RGB 'da scansione': gradiente + rumore pseudo-casuale riproducibile (poco comprimibile con Flate)."""
    from PIL import Image
    rnd = random.Random(seme)
    grad = Image.linear_gradient("L").resize((larghezza, altezza))
    canali = []
    for k in range(3):
        rumore_img = Image.frombytes("L", (larghezza, altezza), rnd.randbytes(larghezza * altezza))
        canali.append(Image.blend(grad.rotate(90 * k, expand=False), rumore_img, rumore))
    return Image.merge("RGB", canali)


def pdf_testo(dst: Path, pagine: int = 3, *, incorpora_font: bool = True, righe: int = 6, seme: int = 1,
              immagine: bool = True, trasparenza: bool = False) -> Path:
    """PDF di testo con numero di pagina leggibile ("Pagina N di M") e accenti italiani."""
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
    font = _font_incorporabile() if incorpora_font else "Helvetica"
    rnd = random.Random(seme)
    c = canvas.Canvas(str(dst))
    c.setTitle("Documento sintetico di prova")
    piccola = ImageReader(_immagine_scansione(64, 64, seme, 0.1)) if immagine else None
    for i in range(pagine):
        c.setFont(font, 13)
        c.drawString(72, 790, f"Documento sintetico - Pagina {i + 1} di {pagine} - è così àèìòù")
        c.setFont(font, 9)
        for r in range(righe):
            c.drawString(72, 770 - 12 * r, _parole(rnd, 12))
        c.rect(72, 300, 200, 100)                      # grafica vettoriale
        if piccola is not None:
            c.drawImage(piccola, 300, 300, 64, 64)
        if trasparenza:
            c.setFillAlpha(0.5)
            c.setFillColorRGB(1, 0, 0)
            c.rect(100, 320, 150, 60, fill=1, stroke=0)
            c.setFillAlpha(1)
        c.showPage()
    c.save()
    return dst


def pdf_immagini_grandi(dst: Path, *, pagine: int = 1, lato_px: int = 2000, seme: int = 7) -> Path:
    """Pagine con un'immagine RGB da scansione ad alta risoluzione (circa 400 dpi): file oltre 5 MB."""
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
    font = _font_incorporabile()
    c = canvas.Canvas(str(dst))
    for i in range(pagine):
        c.setFont(font, 12)
        c.drawString(72, 800, f"Scansione sintetica - Pagina {i + 1} di {pagine}")
        c.drawImage(ImageReader(_immagine_scansione(lato_px, lato_px, seme + i)), 72, 400, 360, 360)
        c.showPage()
    c.save()
    return dst


def pdf_cifrato(src: Path, dst: Path, password_utente: str = "segreto", password_proprietario: str = "proprietario"
                ) -> Path:
    w = PdfWriter(clone_from=str(src))
    w.encrypt(user_password=password_utente, owner_password=password_proprietario)  # RC4-128 (nessuna dipendenza)
    with open(dst, "wb") as f:
        w.write(f)
    return dst


def pdf_firmato_simulato(src: Path, dst: Path) -> Path:
    """Aggiunge un campo firma con /V valorizzato (firma SIMULATA, priva di valore crittografico)."""
    w = PdfWriter(clone_from=str(src))
    firma = DictionaryObject({
        NameObject("/Type"): NameObject("/Sig"), NameObject("/Filter"): NameObject("/Adobe.PPKLite"),
        NameObject("/SubFilter"): NameObject("/adbe.pkcs7.detached"),
        NameObject("/ByteRange"): ArrayObject([NumberObject(0)] * 4),
        NameObject("/Contents"): ByteStringObject(b"\x00" * 64),
        NameObject("/Name"): TextStringObject("FIRMA SIMULATA - NESSUN VALORE CRITTOGRAFICO")})
    pagina = w.pages[0]
    campo = DictionaryObject({
        NameObject("/FT"): NameObject("/Sig"), NameObject("/T"): TextStringObject("FirmaSimulata"),
        NameObject("/V"): w._add_object(firma), NameObject("/Type"): NameObject("/Annot"),
        NameObject("/Subtype"): NameObject("/Widget"), NameObject("/F"): NumberObject(132),
        NameObject("/Rect"): ArrayObject([NumberObject(0)] * 4), NameObject("/P"): pagina.indirect_reference})
    rif = w._add_object(campo)
    pagina[NameObject("/Annots")] = ArrayObject([rif])
    w._root_object[NameObject("/AcroForm")] = DictionaryObject({
        NameObject("/Fields"): ArrayObject([rif]), NameObject("/SigFlags"): NumberObject(3)})
    with open(dst, "wb") as f:
        w.write(f)
    return dst


def pdf_falso_pdfa(src: Path, dst: Path) -> Path:
    """Dichiara PDF/A-1b nei metadati XMP senza esserlo (font non incorporati, nessun OutputIntent)."""
    w = PdfWriter(clone_from=str(src))
    s = DecodedStreamObject()
    s.set_data(XMP_FALSO_PDFA)
    s.update({NameObject("/Type"): NameObject("/Metadata"), NameObject("/Subtype"): NameObject("/XML")})
    w._root_object[NameObject("/Metadata")] = w._add_object(s)
    with open(dst, "wb") as f:
        w.write(f)
    return dst


def pdf_javascript(src: Path, dst: Path) -> Path:
    w = PdfWriter(clone_from=str(src))
    w.add_js("app.alert('JavaScript sintetico di prova');")
    with open(dst, "wb") as f:
        w.write(f)
    return dst


def genera_corpus(cartella: Path | str, *, con_ghostscript: bool = True, pagine_multipagina: int = 40) -> dict:
    """Genera il corpus nella cartella. Restituisce {nome: {percorso, descrizione, atteso, sha256, bytes}}.

    ``atteso.analisi`` e' l'esito atteso di ``pdfa.analizza_pdf``; ``atteso.strutturale_originale`` quello del
    verificatore strutturale sul file cosi' com'e'."""
    from .dimensioni import sha256_file
    d = Path(cartella)
    d.mkdir(parents=True, exist_ok=True)
    voci: dict[str, dict] = {}

    def reg(nome, descrizione, analisi, strutturale=None, **extra):
        p = d / nome
        voci[nome] = {"percorso": str(p), "descrizione": descrizione,
                      "atteso": {"analisi": analisi, "strutturale_originale": strutturale, **extra},
                      "sha256": sha256_file(p), "bytes": p.stat().st_size, "sintetico": True}

    pdf_testo(d / "ordinario.pdf", 3)
    reg("ordinario.pdf", "3 pagine, TrueType incorporato, grafica e piccola immagine: da convertire", "leggibile",
        "indicativo_ko")
    pdf_testo(d / "font_non_incorporati.pdf", 2, incorpora_font=False)
    reg("font_non_incorporati.pdf", "2 pagine con Helvetica non incorporato: non PDF/A, convertibile", "leggibile",
        "indicativo_ko")
    pdf_immagini_grandi(d / "immagini_grandi.pdf")
    reg("immagini_grandi.pdf", "1 pagina con immagine RGB ~400 dpi: oltre 5 MB, riducibile ricomprimendo", "leggibile",
        "indicativo_ko", oltre_5mb=True)
    pdf_testo(d / "multipagina_grande.pdf", pagine_multipagina, righe=55, seme=3)
    reg("multipagina_grande.pdf", f"{pagine_multipagina} pagine di testo fitto: non riducibile ricomprimendo le "
        "immagini, da suddividere con limiti piccoli", "leggibile", "indicativo_ko")
    pdf_cifrato(d / "ordinario.pdf", d / "cifrato.pdf")
    reg("cifrato.pdf", "cifrato con password utente: respinto (protetto)", "protetto", "indicativo_ko")
    pdf_cifrato(d / "ordinario.pdf", d / "protetto_senza_password.pdf", password_utente="")
    reg("protetto_senza_password.pdf", "apribile senza password ma cifrato con restrizioni: respinto (protetto)",
        "protetto", "indicativo_ko")
    dati = (d / "ordinario.pdf").read_bytes()
    (d / "troncato.pdf").write_bytes(dati[: int(len(dati) * 0.6)])
    reg("troncato.pdf", "primi 60% dei byte di ordinario.pdf: respinto (danneggiato)", "danneggiato", "indicativo_ko")
    pdf_firmato_simulato(d / "ordinario.pdf", d / "firmato_simulato.pdf")
    reg("firmato_simulato.pdf", "campo firma con /V (firma SIMULATA): convertibile con avviso di firma non conservata",
        "firmato", "indicativo_ko")
    pdf_falso_pdfa(d / "font_non_incorporati.pdf", d / "falso_pdfa.pdf")
    reg("falso_pdfa.pdf", "dichiara PDF/A-1b nell'XMP ma ha font non incorporati e niente OutputIntent", "leggibile",
        "indicativo_ko", dichiara_pdfa="1b")
    pdf_javascript(d / "ordinario.pdf", d / "javascript.pdf")
    reg("javascript.pdf", "contiene JavaScript a livello di documento", "leggibile", "indicativo_ko")
    pdf_testo(d / "trasparenza.pdf", 1, trasparenza=True)
    reg("trasparenza.pdf", "rettangolo semitrasparente (ca 0.5)", "leggibile", "indicativo_ko")
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (0, 128, 255)).save(buf, "PNG")
    (d / "non_pdf.pdf").write_bytes(buf.getvalue())
    reg("non_pdf.pdf", "immagine PNG con estensione .pdf: respinta (non_pdf)", "non_pdf", "indicativo_ko")
    Image.new("RGB", (300, 200), (200, 10, 10)).save(d / "tiff_colori_lzw.tif", compression="tiff_lzw",
                                                     dpi=(600, 600))
    reg("tiff_colori_lzw.tif", "TIFF a colori LZW 600 dpi: non rispetta p.7", "tiff", None, tiff="indicativo_ko")
    non_generati = []
    if con_ghostscript:
        from .. import pdfa
        from .tiff import converti_in_tiff_g4
        if pdfa.trova_gs() and pdfa._icc():
            conv = pdfa.converti_in_pdfa(d / "ordinario.pdf", d / "gia_pdfa.pdf")
            if conv["comando_ok"]:
                reg("gia_pdfa.pdf", "ordinario.pdf convertito da Ghostscript (dichiara PDF/A-1b)", "leggibile",
                    "indicativo_ok", dichiara_pdfa="1b")
            if converti_in_tiff_g4(d / "ordinario.pdf", d / "tiff_g4_200dpi.tif", dpi=200)["comando_ok"]:
                reg("tiff_g4_200dpi.tif", "ordinario.pdf in TIFF B/N CCITT G4 a 200 dpi (3 pagine)", "tiff", None,
                    tiff="indicativo_ok")
        else:
            non_generati += ["gia_pdfa.pdf", "tiff_g4_200dpi.tif"]
    indice = {"generato": datetime.now(timezone.utc).isoformat(timespec="seconds"), "sintetico": True,
              "nota": "file generati da codice; la firma e' simulata; nessuna prova di compatibilita' con l'Agenzia",
              "voci": voci, "non_generati": non_generati}
    (d / "corpus.json").write_text(json.dumps(indice, ensure_ascii=False, indent=1), encoding="utf-8")
    return voci


def collaudo_a11(cartella: Path | str) -> dict:
    """Esegue sul corpus analisi, conversione e validazione e scrive ``collaudo_a11.json`` (evidenza riprendibile).

    Con veraPDF configurato (SUCCESSIONI_VERAPDF) gli esiti sono 'conforme'/'non_conforme'; senza, 'non_verificato'
    e il requisito A11 resta da_collaudare."""
    from .. import pdfa
    from .dimensioni import sha256_file, testo_pagine
    d = Path(cartella)
    if not (d / "corpus.json").exists():
        genera_corpus(d)
    indice = json.loads((d / "corpus.json").read_text(encoding="utf-8"))
    vp = pdfa.trova_verapdf()
    righe = []
    uscite = d / "derivati"
    uscite.mkdir(exist_ok=True)
    for nome, voce in indice["voci"].items():
        p = Path(voce["percorso"])
        h0 = sha256_file(p)
        an = pdfa.analizza_pdf(p)
        riga = {"file": nome, "analisi": an.get("esito"), "atteso": voce["atteso"]["analisi"],
                "analisi_come_attesa": an.get("esito") == voce["atteso"]["analisi"]}
        if an.get("formato") == "pdf" and an.get("esito") in ("leggibile", "firmato"):
            riga["validazione_originale"] = pdfa.valida_pdfa(p)["esito"]
            dst = uscite / (p.stem + "_pdfa.pdf")
            conv = pdfa.converti_in_pdfa(p, dst)
            riga["conversione_ok"] = conv["comando_ok"]
            if conv["comando_ok"]:
                v = pdfa.valida_pdfa(dst)
                riga.update(validazione_derivato=v["esito"],
                            indicativo_derivato=v["verifica_indicativa"]["esito"],
                            regole_fallite=v.get("regole_fallite"),
                            pagine=[an.get("pagine"), pdfa.analizza_pdf(dst).get("pagine")],
                            testo_pagine_vuote_derivato=[i + 1 for i, t in enumerate(testo_pagine(dst))
                                                         if not t.strip()])
        riga["originale_invariato"] = sha256_file(p) == h0
        righe.append(riga)
    rapporto = {"eseguito": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "ambiente": {"sistema": platform.platform(), "python": sys.version.split()[0],
                             "ghostscript": pdfa.trova_gs(), "verapdf": vp,
                             "versione_verapdf": pdfa._versione_verapdf(vp) if vp else None},
                "esito_collaudo_a11": "da_collaudare" if not vp else "da_esaminare",
                "nota": ("senza veraPDF nessun esito 'conforme' e' possibile" if not vp else
                         "controllare che ordinario/gia_pdfa siano 'conforme' e falso_pdfa 'non_conforme', poi "
                         "registrare l'esito e la fedelta' visiva (anteprima) in docs/PDFA.md"),
                "risultati": righe}
    (d / "collaudo_a11.json").write_text(json.dumps(rapporto, ensure_ascii=False, indent=1), encoding="utf-8")
    return rapporto


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cartella = Path(argv[0])
    voci = genera_corpus(cartella)
    print(f"corpus sintetico: {len(voci)} file in {cartella}")
    if "--collaudo" in argv:
        r = collaudo_a11(cartella)
        print(json.dumps({k: r[k] for k in ("ambiente", "esito_collaudo_a11", "nota")}, ensure_ascii=False, indent=1))
        for riga in r["risultati"]:
            print(riga["file"], riga.get("analisi"), riga.get("validazione_originale", ""),
                  riga.get("validazione_derivato", ""), riga.get("indicativo_derivato", ""))
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    raise SystemExit(main())
