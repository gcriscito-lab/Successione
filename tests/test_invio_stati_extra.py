"""Trasporti dell'invio e stati iniziali per pratica: nessuna trasmissione reale, nessuna copia congelata."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from successioni.archivio import Archivio  # noqa: E402
from successioni.collegamenti import invio as I  # noqa: E402
from successioni.collegamenti.base import sha256_bytes  # noqa: E402
from successioni.servizio import Servizio  # noqa: E402


def test_trasporto_manuale_non_trasmette_e_spiega():
    t = I.TrasportoManualeTracciato()
    assert t.reale is True and t.automatico is False
    r = t.trasmetti(b"<xml/>", "F.xml", {})
    assert r.tipo == "non_disponibile" and "NON trasmette" in r.motivo and "Desktop Telematico" in r.motivo
    assert r.protocollo is None
    c = t.consulta({"sha256": "x"})
    assert c.tipo == "sconosciuto" and "consultazione automatica non disponibile" in c.motivo


def test_trasporto_simulato_non_e_reale_e_assegna_protocolli_progressivi():
    t = I.TrasportoSimulato()
    assert t.reale is False and t.automatico is True
    a = t.trasmetti(b"uno", "A.xml", {})
    b = t.trasmetti(b"due", "B.xml", {})
    assert (a.tipo, b.tipo) == ("accettato", "accettato")
    assert a.protocollo == "SIM00000000000001" and b.protocollo == "SIM00000000000002"
    assert a.originale.startswith(b"SIMULAZIONE")
    assert t.chiamate_trasmetti == 2


def test_guasto_timeout_prima_non_registra_il_file():
    t = I.TrasportoSimulato(guasto="timeout_prima")
    with pytest.raises(TimeoutError, match="prima della ricezione"):
        t.trasmetti(b"x", "F.xml", {})
    assert t.ricevuti == {}
    assert t.consulta({"sha256": sha256_bytes(b"x")}).tipo == "sconosciuto"


def test_guasto_timeout_dopo_ricezione_registra_il_file_e_la_consultazione_lo_trova():
    t = I.TrasportoSimulato(guasto="timeout_dopo_ricezione")
    with pytest.raises(TimeoutError, match="risposta persa"):
        t.trasmetti(b"x", "F.xml", {})
    r = t.consulta({"sha256": sha256_bytes(b"x")})
    assert r.tipo == "accettato" and r.protocollo == "SIM00000000000001"


def test_guasto_rifiuto_con_motivo_personalizzato():
    t = I.TrasportoSimulato(guasto="rifiuto", motivo_rifiuto="scarto di prova")
    r = t.trasmetti(b"x", "F.xml", {})
    assert r.tipo == "rifiutato" and r.motivo == "scarto di prova" and t.ricevuti == {}


def test_consultazione_guasta_solleva_errore_di_connessione():
    t = I.TrasportoSimulato()
    t.consultazione_guasta = True
    with pytest.raises(ConnectionError, match="non raggiungibile"):
        t.consulta({"sha256": "x"})


def test_stati_iniziali_di_una_pratica_senza_copie(tmp_path):
    s = Servizio(Archivio(tmp_path / "dati"))
    pid = s.crea_pratica("Prova")["pratica_id"]
    st = s.stato_elaborati(pid)              # stati_pratica (solo test) rimossa: vale lo stato del servizio
    assert st["pratica_id"] == pid
    assert st["controllo_ufficiale"] == {"stato": "non_eseguito"}
    assert st["trasmissione"]["stato"] == "non_preparata" and "tentativo_aperto" not in st["trasmissione"]
    assert I.InvioAdattatore(s.arch).invio_aperto(pid) == (None, None)


def test_invio_stato_del_servizio_senza_copie(tmp_path):
    s = Servizio(Archivio(tmp_path / "dati"))
    pid = s.crea_pratica("Prova")["pratica_id"]
    assert s.invio_stato(pid) == {"pratica_id": pid, "copie": [], "copia_attiva": None, "tentativo_aperto": None,
                                  "elenco_copie": []}
