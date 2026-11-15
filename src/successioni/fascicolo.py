"""Fascicolo unico per il cliente (versione 0.4): un solo PDF con copertina e indice, modello ministeriale stampato, allegati del
quadro EG (nell'ordine dei righi) e ricevute in PDF, con un segnalibro per ogni documento.

Solo documenti gia' presenti nella pratica: nulla viene calcolato o modificato. Cio' che manca (modello non ancora stampato,
allegati assenti dal deposito, ricevute non in PDF) e' elencato nella copertina con il motivo. Non e' la dichiarazione da
trasmettere: e' una raccolta per il cliente e per l'archivio dello studio.
"""
from __future__ import annotations

import io
from datetime import date, datetime

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from .errori import ErroreServizio


def _pdf_da_tiff(dati: bytes) -> bytes:
    from PIL import Image, ImageSequence
    img = Image.open(io.BytesIO(dati))
    pagine = [p.convert("RGB") for p in ImageSequence.Iterator(img)]
    out = io.BytesIO()
    pagine[0].save(out, format="PDF", save_all=True, append_images=pagine[1:], resolution=200.0)
    return out.getvalue()


def _documenti(sv, pid: str) -> tuple[list[tuple[str, bytes]], list[str]]:
    docs, assenti = [], []
    try:
        pdf, _ = sv.file_stampa_modello(pid)
        superata = sv.stato_elaborati(pid).get("stampa_modello", {}).get("stato") == "obsoleta"
        docs.append(("Modello ministeriale (stampa del file telematico)"
                     + (" - SUPERATO: i dati sono cambiati dopo la stampa, rigenerala" if superata else ""), pdf))
        if superata:
            assenti.append("Modello ministeriale aggiornato: la stampa inclusa e' precedente alle ultime modifiche "
                           "(rigenera la stampa e poi il fascicolo)")
    except ErroreServizio as e:
        assenti.append(f"Modello ministeriale: {e.messaggio}")
    dati = sv.leggi(pid)["dati"]
    from .schema import STRUTTURATI
    nomi_eg = {o["valore"]: o["etichetta"] for o in (STRUTTURATI.get("documenti_ref.tipo_eg") or {}).get("opzioni", [])}
    for r in dati.get("documenti_ref", []):
        aid = r.get("allegato_id")
        if not aid:
            continue
        titolo = (nomi_eg.get(r.get("tipo_eg")) or r.get("tipo_eg") or "Documento") + (f" — {r['finalita']}" if r.get("finalita") else "")
        try:
            contenuto, riga = sv.file_allegato(aid)
        except ErroreServizio as e:
            assenti.append(f"{titolo}: {e.messaggio}")
            continue
        if contenuto[:5] == b"%PDF-":
            docs.append((titolo, contenuto))
        elif contenuto[:4] in (b"II*\x00", b"MM\x00*"):
            docs.append((titolo + " (immagine TIFF convertita)", _pdf_da_tiff(contenuto)))
        else:
            assenti.append(f"{titolo}: formato non PDF ne' TIFF ({riga.get('nome')})")
    try:
        # il tentativo con protocollo della copia attiva, altrimenti della copia piu' recente che ne ha uno
        elenco = sv.invio_stato(pid).get("elenco_copie") or []
        con_prot = [c for c in elenco if c.get("protocollo") and c.get("tentativo_corrente")]
        scelta = next((c for c in con_prot if c.get("attiva")), con_prot[0] if con_prot else None)
        tid = scelta["tentativo_corrente"] if scelta else None
        if tid:
            from .collegamenti.base import DepositoArtefatti
            stato = sv.ricevute_stato(pid, tid)
            dep = DepositoArtefatti(sv.arch)
            for d in stato.get("documenti", []):
                j = sv._adattatore_invio("manuale").job.leggi(d["job_id"], "ricevuta_suc13")
                a = j["risultato"]["artefatti"][0]
                b = dep.leggi(a)
                if b[:5] == b"%PDF-":
                    docs.append((f"Ricevuta: {d.get('tipo', '')} {d.get('esito') or ''}".strip(), b))
                else:
                    assenti.append(f"Ricevuta {a.get('nome')}: non in PDF (conservata nella pratica)")
    except ErroreServizio:
        pass   # nessun invio con protocollo: nessuna ricevuta da raccogliere
    return docs, assenti


VERDE, VERDE_CHIARO, OCRA, INCHIOSTRO, GRIGIO = "#2F6B57", "#DDEBE3", "#A86A12", "#1F2A2A", "#55615F"
VOCI_PER_PAGINA = 14


def _data_it(iso) -> str:
    s = str(iso or "")
    return f"{s[8:10]}/{s[5:7]}/{s[0:4]}" if len(s) == 10 and s[4] == "-" and s[7] == "-" else s


def _defunto(dati: dict | None) -> dict:
    p = next((x for x in (dati or {}).get("persone", []) if x.get("ruolo") == "defunto"), {}) or {}
    nome = " ".join(str(p.get(k) or "").strip().title() for k in ("nome", "cognome")).strip()
    return {"nome": nome, "cf": str(p.get("codice_fiscale") or "").upper(), "decesso": _data_it(p.get("data_decesso")),
            "f": p.get("sesso") == "F"}


def _a_capo(c, testo: str, font: str, dim: float, larghezza: float) -> list[str]:
    parole, righe, riga = (testo or "").split(), [], ""
    for p in parole:
        prova = (riga + " " + p).strip()
        if c.stringWidth(prova, font, dim) <= larghezza or not riga:
            riga = prova
        else:
            righe.append(riga)
            riga = p
    return righe + ([riga] if riga else [])


def _taglia(c, testo: str, font: str, dim: float, larghezza: float) -> str:
    if c.stringWidth(testo, font, dim) <= larghezza:
        return testo
    while testo and c.stringWidth(testo + "…", font, dim) > larghezza:
        testo = testo[:-1]
    return testo.rstrip() + "…"


def _copertina(titolo: str, docs: list[tuple[str, int]], assenti: list[str], studio: list[str] | None = None, *,
               dati: dict | None = None, oggi: date | None = None) -> bytes:
    """Copertina e indice; le pagine dell'indice si contano disegnando (i numeri di pagina dipendono da quante sono)."""
    n_cop = 2
    for _ in range(4):
        pdf = _disegna_copertina(titolo, docs, assenti, studio, dati=dati, oggi=oggi, n_cop=n_cop)
        pagine = len(PdfReader(io.BytesIO(pdf)).pages)
        if pagine == n_cop:
            return pdf
        n_cop = pagine
    return pdf


def _disegna_copertina(titolo: str, docs: list[tuple[str, int]], assenti: list[str], studio: list[str] | None, *,
                       dati: dict | None, oggi: date | None, n_cop: int) -> bytes:
    """Copertina e indice del fascicolo (disegno approvato il 15/11/2026, fatto su Canva con dati di prova e rifatto qui):
    carta intestata dello studio con la barretta ocra, titolo, defunto, riquadro con gli estremi di registrazione (dalle note
    della pratica, se l'attestazione e' stata conservata), poi l'indice con i numeri di pagina e i documenti non inclusi.
    Piede su ogni pagina con «pag. N di M» calcolato sull'intero fascicolo."""
    from reportlab.lib.colors import HexColor
    larg, alt = A4
    sx, dx = 22 * mm, larg - 22 * mm
    oggi = oggi or date.today()
    df = _defunto(dati)
    reg = ((dati or {}).get("note") or {}).get("registrazione") or {}
    nome_studio = (studio or [""])[0]
    totale_doc = sum(n for _, n in docs)

    totale = n_cop + totale_doc

    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=A4)
    c.setTitle(f"Fascicolo per il cliente - {titolo}")
    pagina = [0]

    def piede(linea: bool):
        pagina[0] += 1
        c.setFillColor(HexColor(GRIGIO))
        c.setFont("Helvetica", 8)
        sinistra = " – ".join(x for x in (nome_studio, "Fascicolo per il cliente") if x)
        c.drawString(sx, 14 * mm, _taglia(c, sinistra, "Helvetica", 8, dx - sx - 30 * mm))
        c.drawRightString(dx, 14 * mm, f"pag. {pagina[0]} di {totale}")
        if linea:
            c.setStrokeColor(HexColor(VERDE))
            c.setLineWidth(0.6)
            c.line(sx, 19 * mm, dx, 19 * mm)

    # ---------------------------------------------------------------- copertina
    y = alt - 24 * mm
    if studio:
        c.setFillColor(HexColor(OCRA))
        c.rect(sx - 6 * mm, y - (len(studio) - 1) * 4.6 * mm - 3 * mm, 1.6 * mm, (len(studio) - 1) * 4.6 * mm + 8 * mm,
               stroke=0, fill=1)
        c.setFillColor(HexColor(INCHIOSTRO))
        c.setFont("Helvetica-Bold", 12)
        c.drawString(sx, y, studio[0])
        c.setFont("Helvetica", 8.5)
        for r in studio[1:]:
            y -= 4.6 * mm
            c.drawString(sx, y, _taglia(c, r, "Helvetica", 8.5, dx - sx))
        y -= 9 * mm
        c.setStrokeColor(HexColor(VERDE))
        c.setLineWidth(0.8)
        c.line(sx, y, dx, y)
    cx = larg / 2
    y = alt * 0.6
    c.setFillColor(HexColor(VERDE))
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(cx, y, "Fascicolo per il cliente")
    y -= 17 * mm
    c.setFillColor(HexColor(INCHIOSTRO))
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(cx, y, _taglia(c, f"Successione di {df['nome']}" if df["nome"] else titolo, "Helvetica-Bold", 15, dx - sx))
    sotto = " – ".join(x for x in (f"C.F. {df['cf']}" if df["cf"] else "",
                                   f"{'deceduta' if df['f'] else 'deceduto'} il {df['decesso']}" if df["decesso"] else "") if x)
    if sotto:
        y -= 8 * mm
        c.setFont("Helvetica", 12.5)
        c.drawCentredString(cx, y, sotto)
    if reg.get("volume") and reg.get("numero"):
        frase = " – ".join(x for x in (
            f"Dichiarazione presentata il {reg['data_presentazione']}" if reg.get("data_presentazione") else "Dichiarazione presentata",
            f"registrata al volume {reg['volume']}, numero {reg['numero']}" + (f", anno {reg['anno']}" if reg.get("anno") else ""),
            str(reg.get("ufficio") or "").strip()) if x)
        righe = _a_capo(c, frase, "Helvetica", 11, dx - sx - 16 * mm)
        h = (len(righe) * 6 + 12) * mm
        y -= 20 * mm
        c.setFillColor(HexColor(VERDE_CHIARO))
        c.rect(sx, y - h, dx - sx, h, stroke=0, fill=1)
        c.setFillColor(HexColor(INCHIOSTRO))
        c.setFont("Helvetica", 11)
        yy = y - 9 * mm
        for r in righe:
            c.drawCentredString(cx, yy, r)
            yy -= 6 * mm
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(HexColor(INCHIOSTRO))
    c.drawCentredString(cx, 48 * mm, f"Preparato il {oggi.strftime('%d/%m/%Y')}")
    c.setFont("Helvetica", 10)
    c.setFillColor(HexColor(GRIGIO))
    c.drawCentredString(cx, 41 * mm, "Raccolta dei documenti della pratica: non è la dichiarazione da trasmettere")
    piede(False)
    c.showPage()

    # ---------------------------------------------------------------- indice
    def testata_indice(continua: bool) -> float:
        yt = alt - 32 * mm
        c.setFillColor(HexColor(OCRA))
        c.rect(sx - 6 * mm, yt - 3 * mm, 1.6 * mm, 14 * mm, stroke=0, fill=1)
        c.setFillColor(HexColor(VERDE))
        c.setFont("Helvetica", 28)
        c.drawString(sx, yt, "Contenuto" + (" (segue)" if continua else ""))
        c.setStrokeColor(HexColor(VERDE))
        c.setLineWidth(0.8)
        c.line(sx, yt - 9 * mm, dx, yt - 9 * mm)
        return yt - 24 * mm

    y = testata_indice(False)
    usate = 0
    inizio = n_cop + 1
    voci = docs or []
    if not voci:
        c.setFillColor(HexColor(GRIGIO))
        c.setFont("Helvetica", 11)
        c.drawString(sx, y, "Nessun documento disponibile.")
        y -= 12 * mm
        usate += 1
    for i, (t, n) in enumerate(voci, 1):
        if usate and usate % VOCI_PER_PAGINA == 0:
            piede(True)
            c.showPage()
            y = testata_indice(True)
        num = f"pag. {inizio}"
        c.setFillColor(HexColor(VERDE))
        c.setFont("Helvetica-Bold", 14)
        c.drawString(sx, y, str(i))
        c.setFillColor(HexColor(INCHIOSTRO))
        c.setFont("Helvetica", 11)
        tx = sx + 11 * mm
        fine_num = dx
        larg_num = c.stringWidth(num, "Helvetica", 11)
        testo = _taglia(c, f"{t} ({n} {'pagina' if n == 1 else 'pagine'})", "Helvetica", 11, fine_num - larg_num - tx - 12 * mm)
        c.drawString(tx, y, testo)
        c.drawRightString(fine_num, y, num)
        c.setFillColor(HexColor(GRIGIO))
        punti_da = tx + c.stringWidth(testo, "Helvetica", 11) + 3 * mm
        punti_a = fine_num - larg_num - 3 * mm
        c.setFont("Helvetica", 9)
        while punti_da < punti_a:
            c.drawString(punti_da, y, ".")
            punti_da += 1.6 * mm
        y -= 12 * mm
        usate += 1
        inizio += n
    if assenti:
        if usate % VOCI_PER_PAGINA + 3 > VOCI_PER_PAGINA or y < 60 * mm:
            piede(True)
            c.showPage()
            y = testata_indice(True)
        y -= 4 * mm
        c.setFillColor(HexColor(VERDE))
        c.setFont("Helvetica", 15)
        c.drawString(sx, y, "Non inclusi")
        y -= 8 * mm
        c.setFillColor(HexColor(GRIGIO))
        c.setFont("Helvetica", 9.5)
        for a in assenti:
            for r in _a_capo(c, a, "Helvetica", 9.5, dx - sx):
                if y < 28 * mm:
                    piede(True)
                    c.showPage()
                    y = testata_indice(True)
                    c.setFillColor(HexColor(GRIGIO))
                    c.setFont("Helvetica", 9.5)
                c.drawString(sx, y, r)
                y -= 5 * mm
            y -= 1.5 * mm
    piede(True)
    c.showPage()
    c.save()
    return out.getvalue()


def fascicolo(sv, pid: str) -> tuple[bytes, dict]:
    """PDF unico e indice {documenti: [(titolo, pagine)], non_inclusi: [...]}."""
    pratica = sv.leggi(pid)
    titolo = pratica["titolo"]
    docs, assenti = _documenti(sv, pid)
    letti = []
    for t, b in docs:
        try:
            letti.append((t, PdfReader(io.BytesIO(b))))
        except Exception as e:   # PDF danneggiato: si segnala, non blocca il resto
            assenti.append(f"{t}: PDF non leggibile ({type(e).__name__})")
    indice = [(t, len(r.pages)) for t, r in letti]
    w = PdfWriter()
    from . import carta_intestata as CI
    studio = CI.righe_studio(CI.dati_studio(getattr(getattr(sv, "arch", None), "base", None)))
    cop = PdfReader(io.BytesIO(_copertina(titolo, indice, assenti, studio, dati=pratica["dati"])))
    for p in cop.pages:
        w.add_page(p)
    w.add_outline_item("Copertina e indice", 0)
    for t, r in letti:
        inizio = len(w.pages)
        for p in r.pages:
            w.add_page(p)
        w.add_outline_item(t, inizio)
    w.add_metadata({"/Title": f"Fascicolo per il cliente - {titolo}", "/Producer": "Successioni"})
    out = io.BytesIO()
    w.write(out)
    return out.getvalue(), {"documenti": indice, "non_inclusi": assenti}
