"""File elaborati: esportazione, schema, controllo ufficiale e invalidazione selettiva (A16). Dati sintetici."""
import os
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from telematico_casi import caso_completo  # noqa: E402
from successioni.archivio import Archivio  # noqa: E402
from successioni.errori import DatiNonValidi  # noqa: E402
from successioni.servizio import Servizio  # noqa: E402

CF_FORN = "RSSNNA70A41H501X"


def ops_da_caso(d: dict) -> list[dict]:
    ops = []
    for coll in ("persone", "beni", "devoluzioni", "passivita", "documenti_ref"):
        for e in d.get(coll, []):
            ops.append({"op": "upsert", "coll": coll, "id": e["id"],
                        "campi": {k: v for k, v in e.items() if k not in ("id", "_origine")}})
    ops.append({"op": "set", "sezione": "opzioni", "campi": dict(d.get("opzioni", {}))})
    return ops


@pytest.fixture
def sv(tmp_path):
    s = Servizio(Archivio(tmp_path / "dati"))
    pid = s.crea_pratica("Caso sintetico", iniziali=ops_da_caso(caso_completo()))["pratica_id"]
    return s, pid


def test_senza_fornitore_errore_chiaro(sv):
    s, pid = sv
    with pytest.raises(DatiNonValidi) as e:
        s.esporta(pid)
    assert e.value.dettagli["campo"] == "opzioni.fornitore.cf"


def test_completo_non_produce_xml_parziale(sv):
    s, pid = sv
    r = s.esporta(pid, cf_fornitore=CF_FORN)
    assert r["generato"] is False and r["completo"] is False and r["xml_sha256"] is None
    st = s.stato_elaborati(pid)
    assert st["export"]["stato"] == "aggiornato" and st["export"]["generato"] is False
    assert st["xsd"]["stato"] == "non_eseguito"
    with pytest.raises(DatiNonValidi):                       # senza file non si puo' controllare
        s.controllo_ufficiale_pratica(pid)


def test_bozza_tecnica_valida_per_schema_ma_marcata_non_trasmissibile(sv):
    s, pid = sv
    r = s.esporta(pid, cf_fornitore=CF_FORN, scopo="bozza_tecnica")
    assert r["generato"] is True and r["completo"] is False and r["xsd_errori"] == []
    assert "NON è una dichiarazione completa" in r["avvertenza"]
    assert (s.arch.base / r["percorso"]).read_bytes()[:5] == b"<?xml"
    st = s.stato_elaborati(pid)
    assert st["xsd"]["stato"] == "valido" and st["export"]["scopo"] == "bozza_tecnica"
    assert st["controllo_ufficiale"]["stato"] == "non_eseguito" and st["trasmissione"]["stato"] == "non_preparata"


def test_a16_invalidazione_selettiva_su_export(sv):
    s, pid = sv
    s.esporta(pid, cf_fornitore=CF_FORN, scopo="bozza_tecnica")
    rev = s.leggi(pid)["revisione"]
    s.aggiorna(pid, rev, [{"op": "set", "sezione": "note", "campi": {"promemoria": "telefonare"}}])
    assert s.stato_elaborati(pid)["export"]["stato"] == "aggiornato"      # nota interna: nessuna invalidazione
    s.aggiorna(pid, rev + 1, [{"op": "upsert", "coll": "persone", "id": "p_luca0001", "campi": {"nome": "Luigi"}}])
    st = s.stato_elaborati(pid)
    assert st["export"]["stato"] == "obsoleto" and st["xsd"]["stato"] == "obsoleto"   # dato dichiarativo: invalida
    s.esporta(pid, cf_fornitore=CF_FORN, scopo="bozza_tecnica")
    assert s.stato_elaborati(pid)["export"]["stato"] == "aggiornato"


def test_controllo_senza_componenti_passaggio_manuale_da_collaudare(sv, monkeypatch):
    s, pid = sv
    monkeypatch.delenv("SUCCESSIONI_CONTROLLI_SUC13", raising=False)
    s.esporta(pid, cf_fornitore=CF_FORN, scopo="bozza_tecnica")
    r = s.controllo_ufficiale_pratica(pid)
    assert r["esito"] == "da_collaudare" and r["stato_controllo"] == "non_eseguito" and r["bozza_tecnica"] is True
    assert r["azione_richiesta"]
    assert s.stato_elaborati(pid)["controllo_ufficiale"]["stato"] == "non_eseguito"   # mai 'positivo' senza esecuzione


JAR = os.environ.get("SUCCESSIONI_CONTROLLI_SUC13")


@pytest.mark.skipif(not JAR or not Path(JAR).is_dir() or not shutil.which("java"),
                    reason="componenti del controllo ufficiale o Java non configurati (SUCCESSIONI_CONTROLLI_SUC13)")
def test_controllo_ufficiale_reale_locale_sulla_bozza_e_invalidazione(sv):
    s, pid = sv
    s.esporta(pid, cf_fornitore=CF_FORN, scopo="bozza_tecnica")
    r = s.controllo_ufficiale_pratica(pid)
    assert r["esito"] in ("passato", "fallito") and r["stato_controllo"] in ("positivo", "negativo")
    assert r["bozza_tecnica"] is True
    st = s.stato_elaborati(pid)["controllo_ufficiale"]
    assert st["stato"] == r["stato_controllo"] and st["versione_controllo"]
    rev = s.leggi(pid)["revisione"]
    s.aggiorna(pid, rev, [{"op": "upsert", "coll": "persone", "id": "p_luca0001", "campi": {"nome": "Luigi"}}])
    assert s.stato_elaborati(pid)["controllo_ufficiale"]["stato"] == "obsoleto"        # esito conservato, non piu' valido
