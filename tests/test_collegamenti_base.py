"""Collegamenti: persistenza dei tentativi, esiti, deposito artefatti, rifiuto dei segreti (area 3)."""
import threading

import pytest

from successioni.archivio import Archivio
from successioni.collegamenti.base import (ESITI, CatastoEntratel, ControlloUfficiale, DepositoArtefatti, Esito,
                                           InvioSUC13, RegistroJob, Ricevute, RisultatoAdattatore,
                                           SegretoRifiutato, TransizioneNonAmmessa, verifica_assenza_segreti)
from successioni.errori import ChiaveRiutilizzata, ErroreServizio, NonTrovato


@pytest.fixture
def arch(tmp_path):
    return Archivio(tmp_path / "dati")


def test_esiti_quattro_parole_fisse():
    assert ESITI == ("passato", "fallito", "da_collaudare", "simulazione")
    r = RisultatoAdattatore("simulazione", {"job_id": "x", "stato": "s"})
    assert r.esito is Esito.SIMULAZIONE and r.asdict()["esito"] == "simulazione" and r.job_id == "x"
    with pytest.raises(ValueError):
        RisultatoAdattatore("ok", {})


def test_crea_idempotente_e_chiave_riutilizzata(arch):
    reg = RegistroJob(arch)
    a, nuovo = reg.crea("controllo_ufficiale", "pr_1", {"x": 1}, stato="creato", chiave="k")
    b, nuovo2 = reg.crea("controllo_ufficiale", "pr_1", {"x": 1}, stato="creato", chiave="k")
    assert nuovo and not nuovo2 and a["job_id"] == b["job_id"]
    with pytest.raises(ChiaveRiutilizzata):
        reg.crea("controllo_ufficiale", "pr_1", {"x": 2}, stato="creato", chiave="k")
    assert len(reg.elenca("controllo_ufficiale")) == 1


def test_a15_stato_sopravvive_alla_chiusura_del_client(tmp_path):
    reg = RegistroJob(Archivio(tmp_path / "d"))
    j, _ = reg.crea("catasto_entratel", "pr_1", {"a": 1}, stato="attesa_utente")
    reg.annota(j["job_id"], {"pagina": "p2"})
    del reg  # "chiusura del client": un nuovo processo apre lo stesso archivio
    reg2 = RegistroJob(Archivio(tmp_path / "d"))
    letto = reg2.leggi(j["job_id"])
    assert letto["stato"] == "attesa_utente" and letto["risultato"]["pagina"] == "p2"
    assert [c["stato"] for c in letto["risultato"]["cronologia"]] == ["attesa_utente", "attesa_utente"]


def test_transizione_compare_and_set_un_solo_vincitore(arch):
    reg = RegistroJob(arch)
    j, _ = reg.crea("invio_copia", "pr_1", {"a": 1}, stato="confermata")
    vinti, persi = [], []

    def prova():
        try:
            reg.transizione(j["job_id"], ["confermata"], "in_invio")
            vinti.append(1)
        except TransizioneNonAmmessa:
            persi.append(1)

    th = [threading.Thread(target=prova) for _ in range(8)]
    [t.start() for t in th]
    [t.join() for t in th]
    assert len(vinti) == 1 and len(persi) == 7


def test_annota_non_annulla_una_transizione(arch):
    reg = RegistroJob(arch)
    j, _ = reg.crea("invio_tentativo", None, {"a": 1}, stato="in_trasmissione")
    reg.transizione(j["job_id"], ["in_trasmissione"], "trasmesso")
    reg.annota(j["job_id"], {"nota": "x"})
    assert reg.leggi(j["job_id"])["stato"] == "trasmesso"


def test_segreti_rifiutati(arch):
    reg = RegistroJob(arch)
    for dato in ({"password": "VAL0RE_SEGRETO"}, {"profilo": {"pin_entratel": "VAL0RE_SEGRETO"}},
                 {"a": [{"token_sessione": "VAL0RE_SEGRETO"}]}, {"Password_Sito": "VAL0RE_SEGRETO"}):
        with pytest.raises(SegretoRifiutato) as e:
            reg.crea("invio_copia", None, dato, stato="preparata")
        assert "VAL0RE_SEGRETO" not in str(e.value.asdict())  # il valore non finisce nemmeno nell'errore
    verifica_assenza_segreti({"pratica_id": "pr_1", "codice_fiscale": "X", "chiave_richiesta": "k"})  # ammessi
    assert reg.elenca() == []


def test_deposito_immutabile_e_verificato(arch, tmp_path):
    dep = DepositoArtefatti(arch)
    a = dep.salva_bytes(b"ciao", "f.txt", "prova")
    assert dep.leggi(a) == b"ciao"
    assert dep.salva_bytes(b"ciao", "g.txt", "prova")["percorso"] == a["percorso"]
    (arch.base / a["percorso"]).write_bytes(b"alterato")
    with pytest.raises(ErroreServizio):
        dep.leggi(a)
    with pytest.raises(NonTrovato):
        dep.leggi({**a, "percorso": "allegati/zz/inesistente"})


def test_protocolli_implementati():
    from successioni.collegamenti.catasto import CatastoEntratelAdattatore
    from successioni.collegamenti.controllo import ControlloJar, ControlloManuale
    from successioni.collegamenti.invio import InvioAdattatore
    metodi = {ControlloUfficiale: ("esegui",), CatastoEntratel: ("avvia", "riprendi", "leggi_risultati"),
              InvioSUC13: ("prepara", "conferma", "trasmetti", "riconcilia"), Ricevute: ("associa",)}
    for cls, proto in ((ControlloJar, ControlloUfficiale), (ControlloManuale, ControlloUfficiale),
                       (CatastoEntratelAdattatore, CatastoEntratel), (InvioAdattatore, InvioSUC13),
                       (InvioAdattatore, Ricevute)):
        assert all(callable(getattr(cls, m, None)) for m in metodi[proto]), (cls, proto)
