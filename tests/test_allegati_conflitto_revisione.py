"""Spostamento dei righi EG sul PDF/A (``riordina_allegati`` e ``_dopo_conversione``) con la pratica modificata nel frattempo.

Prima della correzione ``_sposta_riferimenti`` leggeva righi e revisione in due momenti e non riprovava: una modifica concorrente
(GUI e MCP lavorano in parallelo) faceva fallire riordino o conversione con ``ConflittoRevisione``. Ora rilegge la pratica e
riprova (come ``_collega_eg6`` dell'albero genealogico), spostando anche i righi collegati nel frattempo. Dati SINTETICI."""
import pytest

from successioni.archivio import Archivio
from successioni.errori import ConflittoRevisione
from successioni.servizio import Servizio
from test_pdfa import crea_pdf

RAP = {"conversione": {"comando_ok": True}, "validazione": {"esito": "non_verificato"}, "avvisi": [], "livello": "1b"}


def _prepara(tmp_path):
    sv = Servizio(Archivio(tmp_path / "d"))
    altro = Servizio(Archivio(tmp_path / "d"))          # seconda istanza, come il server MCP
    pid = sv.crea_pratica("conflitto")["pratica_id"]
    crea_pdf(sv.cartella_ingresso / "doc.pdf", 1)
    aid = sv.acquisisci_da_ingresso(pid, "doc.pdf", tipo_eg="Altro")["allegato_id"]
    p = tmp_path / "der.pdf"
    crea_pdf(p, 1)
    with sv.arch.transazione() as c:
        did = sv._registra(c, pid, "doc_pdfa.pdf", p, "derivato", aid, "Altro", None, None, {}, RAP)["allegato_id"]
    _collega(sv, pid, aid, "dr_rigo0001")
    return sv, altro, pid, aid, did


def _collega(sv, pid, aid, rid):
    return sv.aggiorna(pid, sv.leggi(pid)["revisione"],
                       [{"op": "upsert", "coll": "documenti_ref", "id": rid, "campi": {"allegato_id": aid, "tipo_eg": "Altro"}}])


def _concorrente(sv, altro, pid, aid, volte=1):
    """Prima di ognuna delle prime ``volte`` scritture del programma, l'altra istanza collega un nuovo rigo all'originale:
    la revisione letta dal programma diventa vecchia."""
    originale = sv.aggiorna
    stato = {"n": 0}

    def aggiorna(*a, **k):
        if k.get("autore") == "programma" and stato["n"] < volte:
            stato["n"] += 1
            _collega(altro, pid, aid, f"dr_conc{stato['n']:04d}")
        return originale(*a, **k)

    sv.aggiorna = aggiorna
    return stato


def _righi(sv, pid):
    return {r["id"]: r["allegato_id"] for r in sv.leggi(pid)["dati"].get("documenti_ref", [])}


def test_dopo_conversione_riprova_dopo_conflitto(tmp_path):
    sv, altro, pid, aid, did = _prepara(tmp_path)
    stato = _concorrente(sv, altro, pid, aid)
    r = sv._dopo_conversione(sv._riga_allegato(aid), did, RAP, "gui")
    assert stato["n"] == 1
    assert r["righi_eg_aggiornati"] == 2 and r["originale_rimosso"] is True
    assert _righi(sv, pid) == {"dr_rigo0001": did, "dr_conc0001": did}      # anche il rigo collegato nel frattempo


def test_riordina_riprova_dopo_conflitto(tmp_path):
    sv, altro, pid, aid, did = _prepara(tmp_path)
    _concorrente(sv, altro, pid, aid)
    r = sv.riordina_allegati(pid)
    assert r["righi_eg_aggiornati"] == 2 and aid in r["rimossi"]
    assert _righi(sv, pid) == {"dr_rigo0001": did, "dr_conc0001": did}


def test_conflitto_persistente_dopo_cinque_tentativi(tmp_path):
    sv, altro, pid, aid, did = _prepara(tmp_path)
    _concorrente(sv, altro, pid, aid, volte=5)
    with pytest.raises(ConflittoRevisione):
        sv._dopo_conversione(sv._riga_allegato(aid), did, RAP, "gui")
    assert aid in {a["id"] for a in sv.elenca_allegati(pid)}                  # l'originale resta
