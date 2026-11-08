"""Fascicolo unico per il cliente (versione 0.4): un solo PDF con copertina e indice, modello ministeriale stampato, allegati del
quadro EG (nell'ordine dei righi) e ricevute in PDF, con un segnalibro per ogni documento.

Solo documenti gia' presenti nella pratica: nulla viene calcolato o modificato. Cio' che manca (modello non ancora stampato,
allegati assenti dal deposito, ricevute non in PDF) e' elencato nella copertina con il motivo. Non e' la dichiarazione da
trasmettere: e' una raccolta per il cliente e per l'archivio dello studio.
"""
from __future__ import annotations

import io
from datetime import datetime

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


def _copertina(titolo: str, docs: list[tuple[str, int]], assenti: list[str]) -> bytes:
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=A4)
    larg, alt = A4
    y = alt - 25 * mm

    def riga(testo, dim=10, grassetto=False, rientro=0):
        nonlocal y
        if y < 20 * mm:
            c.showPage(); y = alt - 25 * mm
        c.setFont("Helvetica-Bold" if grassetto else "Helvetica", dim)
        c.drawString(20 * mm + rientro, y, testo[:110])
        y -= dim * 0.5 * mm + 3 * mm

    riga("Fascicolo per il cliente", 18, True)
    riga(titolo, 12)
    riga("Preparato il " + datetime.now().strftime("%d/%m/%Y alle %H:%M"), 9)
    y -= 4 * mm
    riga("Contenuto", 12, True)
    pagina = 2
    for t, n in docs:
        riga(f"{t}  —  da pagina {pagina} ({n} {'pagina' if n == 1 else 'pagine'})", 10, rientro=4 * mm)
        pagina += n
    if not docs:
        riga("Nessun documento disponibile.", 10, rientro=4 * mm)
    if assenti:
        y -= 3 * mm
        riga("Non inclusi", 12, True)
        for a in assenti:
            riga(a, 9, rientro=4 * mm)
    y -= 6 * mm
    riga("Raccolta dei documenti presenti nella pratica: non e' la dichiarazione da trasmettere.", 8)
    c.save()
    return out.getvalue()


def fascicolo(sv, pid: str) -> tuple[bytes, dict]:
    """PDF unico e indice {documenti: [(titolo, pagine)], non_inclusi: [...]}."""
    titolo = sv.leggi(pid)["titolo"]
    docs, assenti = _documenti(sv, pid)
    letti = []
    for t, b in docs:
        try:
            letti.append((t, PdfReader(io.BytesIO(b))))
        except Exception as e:   # PDF danneggiato: si segnala, non blocca il resto
            assenti.append(f"{t}: PDF non leggibile ({type(e).__name__})")
    indice = [(t, len(r.pages)) for t, r in letti]
    w = PdfWriter()
    cop = PdfReader(io.BytesIO(_copertina(titolo, indice, assenti)))
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
