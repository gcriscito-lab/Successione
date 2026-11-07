"""Revisione 2 dei collegamenti (controllo ufficiale e invio): regressioni sui difetti segnalati.

Nessun invio reale. I diagnostici costruiti a mano sono SIMULAZIONI del tracciato (Visual.coda), non uscite del
componente ufficiale; i registri reali sono quelli di src/successioni/collegamenti/fixture/controllo_reale_20261101.
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import successioni.collegamenti.controllo as C  # noqa: E402
import successioni.collegamenti.invio as I  # noqa: E402
from successioni.archivio import Archivio  # noqa: E402
from successioni.collegamenti.base import ConfermaNonValida, Esito, RegistroJob, ReinvioNonAmmesso  # noqa: E402
from successioni.errori import DatiNonValidi, ErroreServizio  # noqa: E402
from test_collegamenti_controllo import (DGN_POSITIVO_SIMULATO, FIX, LOG_VALIDO, EsecutoreFinto,  # noqa: E402
                                         ambiente_finto, leggi)
from test_collegamenti_invio import adesso_esi, controllo_finto, ctx, prepara  # noqa: E402,F401

RADICE = Path(__file__).resolve().parents[1]
LOG_TRONCATO = LOG_VALIDO[: len(LOG_VALIDO) // 2]   # _logSchema.xml interrotto a meta' (Java terminato)


def dgn_simulato(nome_file: str) -> bytes:
    return DGN_POSITIVO_SIMULATO.replace("in/x.xml", nome_file).encode()


@pytest.fixture
def arch(tmp_path):
    return Archivio(tmp_path / "dati")


# ------------------------------------------------------------------ 1. _logSchema.xml troncato
def test_1_logschema_troncato_job_in_errore_e_cartella_rimossa(arch, tmp_path):
    ctl = C.ControlloJar(arch, ambiente_finto(tmp_path), esecutore=EsecutoreFinto(leggi("frontespizio.dgn"), LOG_TRONCATO))
    r = ctl.esegui(FIX / "frontespizio.xml", pratica_id="pr_1")       # nessuna eccezione grezza
    j = ctl.job.leggi(r.job_id)
    assert j["stato"] == "errore_esecuzione" and j["risultato"]["stato_controllo"] == "non_verificabile"
    assert any("illeggibile" in m for m in j["risultato"]["motivi"]) and j["risultato"]["file_illeggibili"]
    assert "rieseguire" in r.azione_richiesta
    assert not (arch.base / j["risultato"]["cartella_lavoro"]).exists()
    assert {a["ruolo"] for a in r.artefatti} >= {"diagnostico_dgn", "esito_schema"}   # originali conservati


def test_1_errore_imprevisto_dopo_avvio_chiude_il_job(arch, tmp_path, monkeypatch):
    ctl = C.ControlloJar(arch, ambiente_finto(tmp_path), esecutore=EsecutoreFinto(DGN_POSITIVO_SIMULATO.encode(), LOG_VALIDO))
    monkeypatch.setattr(ctl, "_completa_con_diagnostici", lambda *a, **k: (_ for _ in ()).throw(ValueError("rotto")))
    r = ctl.esegui(FIX / "frontespizio.xml")
    j = ctl.job.leggi(r.job_id)
    assert j["stato"] == "errore_esecuzione" and "ValueError" in j["errore"]
    assert not (arch.base / j["risultato"]["cartella_lavoro"]).exists()


def test_1_manuale_logschema_troncato_rifiutato_job_resta_aperto(arch):
    ctl = C.ControlloManuale(arch)
    r = ctl.esegui(FIX / "frontespizio.xml")
    with pytest.raises(DatiNonValidi, match="non e' leggibile"):
        ctl.registra_diagnostico(r.job_id, dgn=leggi("frontespizio.dgn"), log_schema=LOG_TRONCATO)
    assert ctl.leggi(r.job_id).stato == "attesa_diagnostico"


def _servizio_con_export(tmp_path):
    from test_correzioni_codex import pratica_con_allegati
    s, pid = pratica_con_allegati(tmp_path)
    e = s.esporta(pid)
    assert e["generato"] and e["completo"], e
    return s, pid, e


def test_1_servizio_scrive_sempre_il_record(tmp_path, monkeypatch):
    s, pid, _ = _servizio_con_export(tmp_path)

    class Rotto(C.ControlloManuale):
        def esegui(self, *a, **k):
            raise RuntimeError("guasto imprevisto")

    monkeypatch.setattr(C, "controllo_ufficiale", lambda arch, config=None: Rotto(arch))
    with pytest.raises(ErroreServizio, match="non concluso"):
        s.controllo_ufficiale_pratica(pid)
    ctl = s.stato_elaborati(pid)["controllo_ufficiale"]
    assert ctl["stato"] == "non_verificabile" and "guasto imprevisto" in ctl["azione_richiesta"]


def test_1_servizio_logschema_troncato_stato_non_verificabile(tmp_path, monkeypatch):
    s, pid, _ = _servizio_con_export(tmp_path)
    es = EsecutoreFinto(leggi("frontespizio.dgn"), LOG_TRONCATO)
    monkeypatch.setattr(C, "controllo_ufficiale", lambda arch, config=None: C.ControlloJar(arch, ambiente_finto(tmp_path), es))
    r = s.controllo_ufficiale_pratica(pid)
    assert r["stato_controllo"] == "non_verificabile" and r["esito"] == "simulazione"
    st = s.stato_elaborati(pid)["controllo_ufficiale"]
    assert st["stato_job"] == "errore_esecuzione" and st["stato"] == "non_verificabile"
    assert not list((s.arch.base / "lavoro" / "controlli").glob("*"))


# ------------------------------------------------------------------ 2. prova simulata sulla copia reale
def _copia_reale_confermata(ctx):
    reale = I.InvioAdattatore(ctx["arch"])                 # trasporto manuale (copia per l'invio reale)
    c = prepara(ctx, reale)
    assert c.dettaglio["modalita_copia"] == "manuale"
    reale.conferma(c.job_id, impronta_mostrata=c.dettaglio["impronta_conferma"], utente="professionista")
    return reale, c.job_id


def test_2_prova_simulata_non_consuma_la_copia_reale(ctx):
    reale, cid = _copia_reale_confermata(ctx)
    tr = I.TrasportoSimulato()
    prova = I.InvioAdattatore(ctx["arch"], tr)
    t = prova.trasmetti(cid, chiave_richiesta="prova-1")
    assert t.stato == I.TRASMESSO and t.esito is Esito.SIMULAZIONE and t.dettaglio["prova_simulata"] is True
    c = reale.leggi_copia(cid)
    assert c.stato == I.CONFERMATA and c.dettaglio["tentativo_corrente"] is None
    assert c.dettaglio["prove"] == [t.job_id] and c.dettaglio["tentativi"] == []
    with pytest.raises(ReinvioNonAmmesso):                 # fra le prove: nessuna seconda prova dopo un'accettata
        prova.trasmetti(cid, chiave_richiesta="prova-2")
    st = I.stati_pratica(ctx["arch"], ctx["pid"])
    assert st["trasmissione"]["stato"] == I.CONFERMATA and "protocollo" not in st["trasmissione"]
    assert st["trasmissione"]["prova_simulata"]["protocollo_fittizio"].startswith("SIM")
    # l'invio reale (manuale tracciato) resta possibile
    m = reale.trasmetti(cid, chiave_richiesta="reale-1")
    assert m.stato == I.ATTESA_INVIO_MANUALE and m.esito is Esito.DA_COLLAUDARE
    assert reale.leggi_copia(cid).stato == I.IN_INVIO
    assert m.dettaglio["prova_simulata"] is False


def test_2_prova_incerta_si_riconcilia_senza_toccare_la_copia(ctx):
    reale, cid = _copia_reale_confermata(ctx)
    tr = I.TrasportoSimulato(guasto="timeout_dopo_ricezione")
    prova = I.InvioAdattatore(ctx["arch"], tr)
    t = prova.trasmetti(cid, chiave_richiesta="p")
    assert t.stato == I.ESITO_INCERTO and reale.leggi_copia(cid).stato == I.CONFERMATA
    assert prova.riconcilia(t.job_id).stato == I.TRASMESSO
    assert reale.leggi_copia(cid).stato == I.CONFERMATA


def test_2_archivio_precedente_con_copia_reale_consumata_viene_riparato(ctx):
    sim = I.InvioAdattatore(ctx["arch"], I.TrasportoSimulato())
    c = prepara(ctx, sim)
    sim.conferma(c.job_id, impronta_mostrata=c.dettaglio["impronta_conferma"], utente="professionista")
    t = sim.trasmetti(c.job_id, chiave_richiesta="vecchia-prova")
    assert sim.leggi_copia(c.job_id).stato == I.TRASMESSA
    # come le copie della versione precedente: create dal servizio (reali), consumate da una prova simulata
    RegistroJob(ctx["arch"]).annota(c.job_id, {"modalita_copia": "manuale"})
    assert I.stati_pratica(ctx["arch"], ctx["pid"])["trasmissione"]["stato"] == I.CONFERMATA   # gia' in lettura
    reale = I.InvioAdattatore(ctx["arch"])
    r = reale.verifica_validita(c.job_id)
    assert r.stato == I.CONFERMATA and r.dettaglio["prove"] == [t.job_id] and r.dettaglio["tentativi"] == []
    assert reale.leggi_tentativo(t.job_id).dettaglio["prova_simulata"] is True
    assert reale.trasmetti(c.job_id, chiave_richiesta="reale").stato == I.ATTESA_INVIO_MANUALE


def test_2_prova_richiede_copia_confermata(ctx):
    reale = I.InvioAdattatore(ctx["arch"])
    c = prepara(ctx, reale)
    with pytest.raises(ConfermaNonValida):
        I.InvioAdattatore(ctx["arch"], I.TrasportoSimulato()).trasmetti(c.job_id, chiave_richiesta="p")


def test_2_istruzioni_invio_manuale_con_impronta(ctx):
    reale, cid = _copia_reale_confermata(ctx)
    sha = reale.leggi_copia(cid).dettaglio["manifest"][0]["sha256"]
    t = reale.trasmetti(cid, chiave_richiesta="m")
    assert sha in t.azione_richiesta


# ------------------------------------------------------------------ 3. passaggio manuale da GUI/MCP
def _manuale(monkeypatch):
    monkeypatch.setattr(C, "controllo_ufficiale", lambda arch, config=None: C.ControlloManuale(arch))


def test_3_manuale_riusa_il_job_aperto_e_stato_attuale(tmp_path, monkeypatch):
    _manuale(monkeypatch)
    s, pid, e = _servizio_con_export(tmp_path)
    a = s.controllo_ufficiale_pratica(pid)
    b = s.controllo_ufficiale_pratica(pid)
    assert a["job_adattatore"] == b["job_adattatore"] and a["job_id"] == b["job_id"]
    assert len(RegistroJob(s.arch).elenca(C.TIPO_JOB, pid)) == 1
    st = s.stato_elaborati(pid)["controllo_ufficiale"]
    assert st["stato_job"] == "attesa_diagnostico" and st["stato"] == "non_eseguito"
    assert "successione_rev" in st["azione_richiesta"]           # nomi riconosciuti elencati all'utente
    # SIMULAZIONE: .dgn positivo costruito a mano con il nome del file scaricato dall'app
    rev = s.leggi(pid)["revisione"]
    out = s.registra_diagnostico_controllo(pid, dgn=dgn_simulato(f"C:\\Users\\x\\successione_rev{rev}.xml"),
                                           log_schema=LOG_VALIDO, ambiente_dichiarato={"os": "Windows 11"})
    assert out["stato"] == "positivo" and out["stato_job"] == "completato"
    st = s.stato_elaborati(pid)["controllo_ufficiale"]          # letto dal job dell'adattatore, non dall'istantanea
    assert st["stato"] == "positivo" and st["parola_esito"] == "passato"
    with pytest.raises(DatiNonValidi):                           # gia' registrato
        s.registra_diagnostico_controllo(pid, dgn=dgn_simulato(f"successione_rev{rev}.xml"), log_schema=LOG_VALIDO)


def test_3_registrazione_rifiuta_revisione_diversa(tmp_path, monkeypatch):
    _manuale(monkeypatch)
    s, pid, e = _servizio_con_export(tmp_path)
    s.controllo_ufficiale_pratica(pid)
    rev = s.leggi(pid)["revisione"]
    with pytest.raises(DatiNonValidi, match="altra revisione"):
        s.registra_diagnostico_controllo(pid, dgn=dgn_simulato(f"successione_rev{rev + 7}.xml"), log_schema=LOG_VALIDO,
                                         conferma_associazione=True)
    assert s.stato_elaborati(pid)["controllo_ufficiale"]["stato_job"] == "attesa_diagnostico"


# ------------------------------------------------------------------ 4. abbinamento per impronta/nome
def test_4_nomi_noti_del_file_controllato(arch):
    ctl = C.ControlloManuale(arch)
    r = ctl.esegui(FIX / "frontespizio.xml", revisione=3)
    j = ctl.job.leggi(r.job_id)
    sha16 = j["input"]["xml_sha256"][:16]
    for n in (f"{sha16}.xml", "successione_rev3.xml", f"{r.job_id}.dcm", "frontespizio.xml", f"C:\\a\\{sha16.upper()}.XML"):
        assert C.confronta_nome(n, j, ctl.job)[0] == "coincide", n
    for n in ("0123456789abcdef.xml", "successione_rev2.xml"):
        assert C.confronta_nome(n, j, ctl.job)[0] == "diverso", n
    assert C.confronta_nome("altro.xml", j, ctl.job)[0] == "sconosciuto"
    assert C.confronta_nome("ctl_" + "0" * 24 + ".dcm", j, ctl.job)[0] == "sconosciuto"   # non in questo archivio
    altro = tmp = arch.base / "altro.xml"
    tmp.write_bytes(b"<x/>")
    k = ctl.esegui(altro)
    assert C.confronta_nome(f"{k.job_id}.dcm", j, ctl.job)[0] == "diverso"           # controllo su altro file


def test_4_dgn_di_altra_impronta_rifiutato_anche_con_conferma(arch):
    ctl = C.ControlloManuale(arch)
    r = ctl.esegui(FIX / "frontespizio.xml")
    with pytest.raises(DatiNonValidi, match="altro file"):
        ctl.registra_diagnostico(r.job_id, dgn=dgn_simulato("in/0123456789abcdef.xml"), log_schema=LOG_VALIDO,
                                 conferma_associazione=True)
    sha16 = ctl.job.leggi(r.job_id)["input"]["xml_sha256"][:16]
    assert ctl.registra_diagnostico(r.job_id, dgn=dgn_simulato(f"in/{sha16}.xml"),
                                    log_schema=LOG_VALIDO).esito is Esito.PASSATO


def _tentativo_manuale(ctx):
    reale, cid = _copia_reale_confermata(ctx)
    return reale, reale.trasmetti(cid, chiave_richiesta="m").job_id


def _esi(nome, quando, protocollo="26110117344816257"):
    return ('{"tipoOperazione":"INVIO","resultCode":"00","startDate":"%s","fileName":"%s","protocollo":"%s"}'
            % (quando, nome, protocollo))


def test_4_esi_vecchio_o_di_altro_file_non_abbinato(ctx):
    reale, tid = _tentativo_manuale(ctx)
    ieri = (datetime.now() - timedelta(days=1)).strftime("%d%m%Y%H%M%S")
    r = reale.riconcilia(tid, evidenze={"esi": _esi("copia_congelata.ccf", ieri)})
    assert r.stato == I.ATTESA_INVIO_MANUALE and r.dettaglio["candidati"][0]["motivo_scarto"].startswith("invio precedente")
    r = reale.riconcilia(tid, evidenze={"esi": _esi("0123456789abcdef.ccf", adesso_esi())})
    assert r.stato == I.ATTESA_INVIO_MANUALE and "non riferibile" in r.dettaglio["candidati"][0]["motivo_scarto"]
    r = reale.riconcilia(tid, evidenze={"esi": _esi("copia_congelata.ccf", "")})
    assert r.stato == I.ATTESA_INVIO_MANUALE
    nome = reale.leggi_tentativo(tid).dettaglio
    sha16 = reale.job.leggi(tid)["input"]["sha256"][:16]
    r = reale.riconcilia(tid, evidenze={"esi": _esi(sha16 + ".dcm", adesso_esi())})
    assert r.stato == I.TRASMESSO and r.dettaglio["protocollo"] == "26110117344816257" and nome


def test_4_protocollo_gia_associato_non_riusato(ctx):
    reale, tid = _tentativo_manuale(ctx)
    reale.riconcilia(tid, evidenze={"protocollo": "P1", "verificato_su": "Ricerca ricevute"})
    t2, _ = reale.job.crea(I.TIPO_TENTATIVO, ctx["pid"], {"copia_id": "x", "nome": "y.xml", "sha256": "0" * 64,
                                                          "modalita": "manuale"}, stato=I.ESITO_INCERTO)
    with pytest.raises(DatiNonValidi, match="altro tentativo"):
        reale.riconcilia(t2["job_id"], evidenze={"protocollo": "P1", "verificato_su": "x"})


# ------------------------------------------------------------------ 5. valuta: righe non riconosciute
def test_5_valuta_da_verificare_con_righe_non_riconosciute_o_gravita_illeggibile(arch, tmp_path):
    d = C.leggi_dgn(DGN_POSITIVO_SIMULATO + "Xriga sconosciuta\n")
    assert C.valuta(d, None)[0] == "da_verificare"
    riga = "1" + "RSSMRA40A01H501K" + "  " + "3345" + "XXX01".ljust(16) + " " * 61 + "00001"
    d = C.leggi_dgn(DGN_POSITIVO_SIMULATO + riga + "\n")
    assert d["diagnostici"][0]["gravita"] is None and C.valuta(d, None)[0] == "da_verificare"
    assert C.valuta(C.leggi_dgn(DGN_POSITIVO_SIMULATO), None)[0] == "positivo"
    # positivo reale locale A10 (registrazione 2026-11-01): resta positivo
    a10 = RADICE / "tests" / "fixture_telematico" / "controllo_20261101" / "a10_positivo.dgn"
    assert C.valuta(C.leggi_dgn(C.decodifica(a10.read_bytes())), None)[0] == "positivo"
    ctl = C.ControlloManuale(arch)
    r = ctl.esegui(FIX / "frontespizio.xml")
    out = ctl.registra_diagnostico(r.job_id, dgn=(DGN_POSITIVO_SIMULATO.replace("in/x.xml", "in/frontespizio.xml")
                                                  + "Xriga\n").encode(), log_schema=LOG_VALIDO)
    assert out.dettaglio["stato_controllo"] == "da_verificare" and out.esito is Esito.DA_COLLAUDARE


# ------------------------------------------------------------------ 6. documentazione allineata
def test_6_documenti_non_dichiarano_assente_il_positivo_locale():
    coll = (RADICE / "docs" / "COLLEGAMENTI.md").read_text(encoding="utf-8")
    assert "manca un caso positivo" not in coll and "non ancora osservato" not in coll
    assert "non ancora osservato su un caso positivo" not in (RADICE / "src" / "successioni" / "collegamenti"
                                                             / "controllo.py").read_text(encoding="utf-8")
    matr = (RADICE / "docs" / "MATRICE_COPERTURA.md").read_text(encoding="utf-8")
    assert "estero non coperto" not in matr
