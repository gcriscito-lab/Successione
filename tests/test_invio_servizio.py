"""Percorso di invio (prova simulata): copia congelata, conferma solo dalla GUI, trasmissione simulata, nessun doppio invio,
rete interrotta e riconciliazione. Nessun invio reale: il servizio dell'Agenzia e' fittizio (simulazione)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from test_correzioni_codex import pratica_con_allegati  # noqa: E402
from successioni.collegamenti.invio import TrasportoSimulato  # noqa: E402
from successioni.errori import DatiNonValidi, ErroreServizio  # noqa: E402
from test_telematico_controllo import _motivo_salto  # noqa: E402


def _esporta_e_prepara(tmp_path):
    s, pid = pratica_con_allegati(tmp_path)
    r = s.esporta(pid)
    assert r["generato"] and r["completo"], r
    return s, pid


def test_senza_file_completo_non_si_prepara(tmp_path):
    s, pid = pratica_con_allegati(tmp_path)
    with pytest.raises(DatiNonValidi, match="XML completo"):
        s.invio_prepara(pid)


def test_prepara_congela_e_chiede_controllo_ufficiale(tmp_path):
    s, pid = _esporta_e_prepara(tmp_path)
    c = s.invio_prepara(pid, chiave="prep-1")
    assert c["stato"] == "preparata" and c["dettaglio"]["impronta_conferma"]
    assert "controllo ufficiale" in c["azione_richiesta"]
    assert s.invio_prepara(pid, chiave="prep-1")["job_id"] == c["job_id"]          # idempotente


def test_la_conferma_non_si_da_da_mcp(tmp_path):
    """Il rifiuto deve dipendere dal CANALE, non da un altro requisito mancante (review 3: prima bastava qualunque
    ErroreServizio, e la copia senza controllo positivo sarebbe stata rifiutata comunque)."""
    from successioni.collegamenti.base import ConfermaNonValida
    s, pid = _esporta_e_prepara(tmp_path)
    c = s.invio_prepara(pid)
    with pytest.raises(ConfermaNonValida, match="si da' nell'app, non da mcp") as e:
        s.invio_conferma(c["job_id"], c["dettaglio"]["impronta_conferma"], canale="mcp")
    assert "requisiti" not in e.value.dettagli
    with pytest.raises(ConfermaNonValida, match="requisiti mancanti"):     # dalla GUI il motivo e' un altro
        s.invio_conferma(c["job_id"], c["dettaglio"]["impronta_conferma"], canale="gui")
    assert s.invio_copia(c["job_id"])["stato"] == "preparata"


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
def test_la_conferma_da_mcp_rifiutata_anche_su_copia_confermabile(tmp_path):
    s, pid, copia = _pronta(tmp_path)
    assert not copia["dettaglio"].get("requisiti_mancanti") and not copia["azione_richiesta"].startswith("Requisiti")
    for canale in ("mcp", "claude", ""):
        with pytest.raises(ErroreServizio, match="nell'app"):
            s.invio_conferma(copia["job_id"], copia["dettaglio"]["impronta_conferma"], canale=canale)
    assert s.invio_copia(copia["job_id"])["stato"] == "preparata"
    assert s.invio_conferma(copia["job_id"], copia["dettaglio"]["impronta_conferma"])["stato"] == "confermata"


def test_percorso_completo_simulato_senza_controllo_positivo_bloccato(tmp_path):
    s, pid = _esporta_e_prepara(tmp_path)
    c = s.invio_prepara(pid)
    with pytest.raises(ErroreServizio):                       # requisito: controllo ufficiale positivo associato
        s.invio_conferma(c["job_id"], c["dettaglio"]["impronta_conferma"])
    with pytest.raises(ErroreServizio):                       # e senza conferma non si trasmette
        s.invio_trasmetti(c["job_id"], "t-1")


def _pronta(tmp_path):
    """Pratica con file completo, controllo ufficiale locale positivo e copia congelata."""
    s, pid = _esporta_e_prepara(tmp_path)
    c = s.controllo_ufficiale_pratica(pid)
    assert c["stato_controllo"] == "positivo", c
    copia = s.invio_prepara(pid)
    assert "controllo" not in (copia["azione_richiesta"] or "").lower().split("requisiti")[-1], copia["azione_richiesta"]
    return s, pid, copia


skip_ctl = pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")


@skip_ctl
def test_invio_simulato_completo_e_nessun_doppio_invio(tmp_path):
    s, pid, copia = _pronta(tmp_path)
    cid, imp = copia["job_id"], copia["dettaglio"]["impronta_conferma"]
    conf = s.invio_conferma(cid, imp, utente="studio-prova")
    assert conf["stato"] == "confermata"
    r = s.invio_trasmetti(cid, "tent-1", modalita="simulata")
    assert r["esito"] == "simulazione" and "PROVA SIMULATA" in r["avvertenza"]
    assert r["stato"] == "trasmesso", r["stato"]
    assert r["dettaglio"].get("protocollo", "").startswith("SIM")
    assert s._trasporto_simulato.chiamate_trasmetti == 1
    with pytest.raises(ErroreServizio):                       # stessa copia, nuova chiave: nessun secondo invio
        s.invio_trasmetti(cid, "tent-2", modalita="simulata")
    assert s._trasporto_simulato.chiamate_trasmetti == 1
    assert s.invio_trasmetti(cid, "tent-1", modalita="simulata")["job_id"] == r["job_id"]   # stessa richiesta: nessuna nuova chiamata
    assert s._trasporto_simulato.chiamate_trasmetti == 1


@skip_ctl
def test_rete_interrotta_dopo_la_ricezione_si_riconcilia_senza_reinviare(tmp_path):
    s, pid, copia = _pronta(tmp_path)
    cid = copia["job_id"]
    s.invio_conferma(cid, copia["dettaglio"]["impronta_conferma"])
    s._adattatore_invio("simulata")                           # crea il servizio fittizio
    s._trasporto_simulato.guasto = "timeout_dopo_ricezione"
    r = s.invio_trasmetti(cid, "tent-1", modalita="simulata")
    assert r["stato"] == "esito_incerto", r["stato"]
    with pytest.raises(ErroreServizio):                       # incerto: niente nuovo invio
        s.invio_trasmetti(cid, "tent-2", modalita="simulata")
    ric = s.invio_riconcilia(r["job_id"], modalita="simulata")  # il servizio fittizio ricorda il file
    assert ric["stato"] == "trasmesso" and ric["dettaglio"]["protocollo"].startswith("SIM")
    assert s._trasporto_simulato.chiamate_trasmetti == 1


@skip_ctl
def test_modalita_manuale_non_trasmette_nulla(tmp_path):
    s, pid, copia = _pronta(tmp_path)
    cid = copia["job_id"]
    s.invio_conferma(cid, copia["dettaglio"]["impronta_conferma"])
    r = s.invio_trasmetti(cid, "tent-1", modalita="manuale")
    assert "NON ha trasmesso" in r["avvertenza"] and r["esito"] == "da_collaudare"
    assert r["stato"] != "trasmesso"
    assert getattr(s, "_trasporto_simulato", None) is None


@skip_ctl
def test_modifica_della_pratica_rende_obsoleta_la_copia(tmp_path):
    s, pid, copia = _pronta(tmp_path)
    cid = copia["job_id"]
    rev = s.leggi(pid)["revisione"]
    s.aggiorna(pid, rev, [{"op": "upsert", "coll": "persone", "id": "p_luca0001", "campi": {"nome": "Luigi"}}])
    with pytest.raises(ErroreServizio):
        s.invio_conferma(cid, copia["dettaglio"]["impronta_conferma"])
    assert s.invio_copia(cid)["stato"] == "obsoleta"
