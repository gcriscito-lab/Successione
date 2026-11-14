"""Ricevute e attestazioni prese dalla cartella dei download (14/11/2026). Dati SINTETICI: l'attestazione di prova e' scritta qui
con reportlab sulla falsariga del testo dell'Agenzia, con defunto, codice fiscale ed estremi inventati."""
import io

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

import telematico_casi as T
from successioni import anonimizza as AN
from successioni.archivio import Archivio
from successioni.collegamenti import ricevute_pdf as R
from successioni.errori import DatiNonValidi
from successioni.servizio import Servizio

RIGHE = [
    "copia per il contribuente",
    "DIREZIONE PROVINCIALE DI ROMA",
    "UFFICIO TERRITORIALE DI PROVA",
    "(Codice Ufficio TZZ) Imposta di bollo e",
    "ATTESTAZIONE DI AVVENUTA PRESENTAZIONE DELLA DICHIARAZIONE DI",
    "SUCCESSIONE TELEMATICA",
    "Si attesta che in data 02/07/2025 il sistema informativo dell'Agenzia delle Entrate",
    f"ha acquisito l'allegata dichiarazione di successione del defunto MARIO ROSSI , nato",
    f"a ROMA, il 01/01/1940, codice fiscale {T.CF_DEFUNTO}.",
    "La dichiarazione è stata registrata al volume 88888, numero 123456, anno 2025.",
    "L’ufficio competente alla lavorazione della dichiarazione è l’UFFICIO TERRITORIALE DI PROVA",
    "IL FUNZIONARIO DELEGATO (*)",
    "Verifica di corrispondenza con il documento originale disponibile fino al 12/01/2026 sul sito",
    "Codice di verifica:abc123def0 - ID documento",
]


def _pdf(righe, pagine=2) -> bytes:
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=A4)
    for n in range(pagine):
        y = 800
        for r in (righe if n == 0 else ["Copia della dichiarazione"]):
            c.drawString(40, y, r)
            y -= 16
        c.showPage()
    c.save()
    return out.getvalue()


ATTESTAZIONE = _pdf(RIGHE)


def test_riconosce_l_attestazione():
    r = R.riconosci(ATTESTAZIONE)
    assert r["tipo"] == "attestazione" and r["codice_fiscale_defunto"] == T.CF_DEFUNTO and r["pagine"] == 2
    d = r["dati"]
    assert d["registrazione"] == {"volume": "88888", "numero": "123456", "anno": "2025"}
    assert (d["data_presentazione"], d["codice_ufficio"], d["defunto"], d["codice_verifica"]) == \
        ("02/07/2025", "TZZ", "MARIO ROSSI", "abc123def0")
    assert d["ufficio"].startswith("UFFICIO TERRITORIALE DI PROVA")
    assert R.riconosci(_pdf(["Biglietto aereo", "nessuna successione"]))["tipo"] is None
    assert R.riconosci(b"non un pdf")["tipo"] is None


def test_solo_i_nomi_da_documento_della_successione():
    assert R.candidato_per_nome("RSSMRA40A01H501K_SUC13_dcm_Attestazione.pdf") and R.candidato_per_nome("ricevuta (2).pdf")
    assert not R.candidato_per_nome("vacanze.pdf") and not R.candidato_per_nome("SUC13_appunti.txt")


def _servizio(tmp_path):
    sv = Servizio(Archivio(tmp_path / "d"))
    pid = sv.crea_pratica("Successione ROSSI MARIO", iniziali=AN.operazioni(T.caso_completo()))["pratica_id"]
    return sv, pid


def test_cerca_conserva_e_non_ricarica(tmp_path):
    sv, pid = _servizio(tmp_path)
    dl = tmp_path / "Download"
    dl.mkdir()
    (dl / f"{T.CF_DEFUNTO}_SUC13_dcm_Attestazione.pdf").write_bytes(ATTESTAZIONE)
    (dl / "ricevuta.pdf").write_bytes(_pdf(["Prenotazione", "nessuna successione"]))   # aperto per il nome, non riconosciuto
    (dl / "vacanze.pdf").write_bytes(b"%PDF-1.4 rotto")                                 # mai aperto (nome non candidato)
    r = sv.ricevute_cerca(dl)
    assert [d["file"] for d in r["documenti"]] == [f"{T.CF_DEFUNTO}_SUC13_dcm_Attestazione.pdf"]
    doc = r["documenti"][0]
    assert doc["pratiche"] == [{"pratica_id": pid, "titolo": "Successione ROSSI MARIO"}] and doc["conservato_in"] is None
    rev = sv.leggi(pid)["revisione"]
    a = sv.ricevuta_da_cartella(pid, doc["file"], cartella=dl)
    assert a["tipo"] == "attestazione" and a["protocollo"] == "registrazione 88888/123456/2025" and not a["ripetuta"]
    p = sv.leggi(pid)
    assert p["revisione"] == rev + 1 and p["dati"]["note"]["registrazione"]["numero"] == "123456"
    assert sv.ricevute_cerca(dl)["documenti"][0]["conservato_in"] == pid
    again = sv.ricevuta_da_cartella(pid, doc["file"], cartella=dl)
    assert again["ripetuta"] and sv.leggi(pid)["revisione"] == rev + 1


def test_rifiuta_altro_defunto_e_file_fuori_cartella(tmp_path):
    sv, pid = _servizio(tmp_path)
    dl = tmp_path / "Download"
    dl.mkdir()
    altro = [r.replace(T.CF_DEFUNTO, T.CF_ANNA) for r in RIGHE]
    (dl / "altro_SUC13_dcm_Attestazione.pdf").write_bytes(_pdf(altro))
    with pytest.raises(DatiNonValidi, match="altro defunto"):
        sv.ricevuta_da_cartella(pid, "altro_SUC13_dcm_Attestazione.pdf", cartella=dl)
    with pytest.raises(DatiNonValidi, match="non disponibile"):
        sv.ricevuta_da_cartella(pid, "../fuori_SUC13.pdf", cartella=dl)
    with pytest.raises(DatiNonValidi, match="cartella non trovata"):
        sv.ricevute_cerca(tmp_path / "inesistente")
