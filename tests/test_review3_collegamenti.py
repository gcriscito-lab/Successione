"""Review 3 dei collegamenti (7/11/2026 sera): regressioni sui difetti di controllo ufficiale manuale, invio, catasto.

Nessun invio reale. I diagnostici di partenza sono le registrazioni del componente ufficiale (controllo LOCALE su dati
sintetici, tests/fixture_telematico/controllo_20261101); le varianti costruite qui (CF sostituito, record 9 alterato)
sono SIMULAZIONI del tracciato.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import successioni.collegamenti.catasto as K  # noqa: E402
import successioni.collegamenti.controllo as C  # noqa: E402
import successioni.collegamenti.invio as I  # noqa: E402
from successioni.archivio import Archivio  # noqa: E402
from successioni.collegamenti.base import Esito, ReinvioNonAmmesso, RegistroJob  # noqa: E402
from successioni.errori import DatiNonValidi  # noqa: E402
from test_collegamenti_invio import ctx, prepara  # noqa: E402,F401

A10 = Path(__file__).parent / "fixture_telematico" / "controllo_20261101"


def a10(nome: str) -> bytes:
    return (A10 / nome).read_bytes()


@pytest.fixture
def arch(tmp_path):
    return Archivio(tmp_path / "dati")


# ------------------------------------------------------------------ 1. .dgn di un altro file accettato come «passato»
def _file_corrente(tmp_path, nome="successione_rev5.xml") -> Path:
    """Un XML DIVERSO da quello controllato in a10_positivo (importo da versare cambiato), stesso defunto e stesso
    identificativo 00001: e' la situazione di una revisione successiva della stessa pratica."""
    p = tmp_path / nome
    p.write_bytes(a10("neg_importo_da_versare.xml"))
    assert p.read_bytes() != a10("a10_positivo.xml")
    return p


def test_1_dgn_di_altro_file_non_passa_senza_conferma(arch, tmp_path):
    ctl = C.ControlloManuale(arch)
    r = ctl.esegui(_file_corrente(tmp_path), revisione=5)
    # il .dgn positivo di a10_positivo.xml (nome nell'intestazione: in/a10_positivo.xml), CF e identificativo uguali
    with pytest.raises(DatiNonValidi, match="conferma") as e:
        ctl.registra_diagnostico(r.job_id, dgn=a10("a10_positivo.dgn"), log_schema=a10("a10_positivo_logSchema.xml"))
    assert e.value.dettagli["contenuto_coerente"] is True and e.value.dettagli["serve_conferma"] is True
    assert "a10_positivo.xml" in e.value.messaggio and "successione_rev5.xml" in e.value.dettagli["nomi_attesi"]
    assert ctl.leggi(r.job_id).stato == "attesa_diagnostico"          # niente «passato», niente sblocco dell'invio


def test_1_dgn_rinominato_con_wri_precedente_rifiutato_anche_con_conferma(arch, tmp_path):
    ctl = C.ControlloManuale(arch)
    r = ctl.esegui(_file_corrente(tmp_path), revisione=5)
    # SIMULAZIONE: stesso .dgn con il nome del file corrente nell'intestazione (file rinominato prima del controllo
    # vecchio); il rapporto .wri originale e' del 1/11/2026, prima dell'esportazione del file corrente (oggi)
    dgn = C.decodifica(a10("a10_positivo.dgn")).replace("in/a10_positivo.xml", "in/successione_rev5.xml")
    for conferma in (False, True):
        with pytest.raises(DatiNonValidi, match="prima dell'esportazione"):
            ctl.registra_diagnostico(r.job_id, dgn=dgn.encode(), log_schema=a10("a10_positivo_logSchema.xml"),
                                     wri=a10("a10_positivo.wri"), conferma_associazione=conferma)
    assert ctl.leggi(r.job_id).stato == "attesa_diagnostico"
    # senza .wri (facoltativo) e con il nome noto l'associazione e' verificata dal nome: limite documentato
    out = ctl.registra_diagnostico(r.job_id, dgn=dgn.encode(), log_schema=a10("a10_positivo_logSchema.xml"))
    assert out.esito is Esito.PASSATO


def test_1_conferma_esplicita_registrata_come_tale(arch, tmp_path):
    ctl = C.ControlloManuale(arch)
    r = ctl.esegui(_file_corrente(tmp_path), revisione=5)
    out = ctl.registra_diagnostico(r.job_id, dgn=a10("a10_positivo.dgn"), log_schema=a10("a10_positivo_logSchema.xml"),
                                   conferma_associazione=True)
    reg = ctl.job.leggi(r.job_id)["risultato"]
    assert out.esito is Esito.PASSATO and reg["associazione"]["conferma_utente"] is True
    assert "confermata esplicitamente dall'utente" in reg["associazione"]["metodo"]
    assert any("confermata dall'utente" in a for a in reg["avvertenze"])


def test_1_wri_datato_dopo_l_esportazione_accettato(arch, tmp_path):
    xml = tmp_path / "a10_positivo.xml"
    xml.write_bytes(a10("a10_positivo.xml"))
    ctl = C.ControlloManuale(arch)
    r = ctl.esegui(xml)
    out = ctl.registra_diagnostico(r.job_id, dgn=a10("a10_positivo.dgn"), log_schema=a10("a10_positivo_logSchema.xml"),
                                   wri=a10("a10_positivo.wri"), non_prima_di="2026-11-01T08:00:00+00:00")
    assert out.esito is Esito.PASSATO
    assert ctl.job.leggi(r.job_id)["risultato"]["associazione"]["data_rapporto_wri"] == "2026-11-01"


def test_1_servizio_dgn_della_revisione_precedente_non_sblocca_l_invio(tmp_path, monkeypatch):
    from test_review2_collegamenti import _servizio_con_export
    monkeypatch.setattr(C, "controllo_ufficiale", lambda arch, config=None: C.ControlloManuale(arch))
    s, pid, e = _servizio_con_export(tmp_path)
    s.controllo_ufficiale_pratica(pid)
    xml, _ = s.file_export(pid, e["job_id"])
    cf = C._cf_defunto(xml)
    # SIMULAZIONE: .dgn positivo reale con il CF del defunto di questa pratica e il nome di un file rinominato
    dgn = (C.decodifica(a10("a10_positivo.dgn")).replace("RSSMRA40A01H501K", cf.ljust(16)[:16])
           .replace("in/a10_positivo.xml", "C:\\Users\\x\\dichiarazione_mario.xml")).encode()
    with pytest.raises(DatiNonValidi, match="conferma"):
        s.registra_diagnostico_controllo(pid, dgn=dgn, log_schema=a10("a10_positivo_logSchema.xml"))
    ctl = s.stato_elaborati(pid)["controllo_ufficiale"]
    assert ctl["stato_job"] == "attesa_diagnostico" and ctl["stato"] != "positivo"
    copia = s.invio_prepara(pid)
    assert "controllo ufficiale non positivo" in copia["azione_richiesta"]


# ------------------------------------------------------------------ 2. nuova copia con un invio aperto o trasmesso
def _reale_confermata(ctx, **kw):
    reale = I.InvioAdattatore(ctx["arch"])
    c = prepara(ctx, reale, **kw)
    reale.conferma(c.job_id, impronta_mostrata=c.dettaglio["impronta_conferma"], utente="professionista")
    return reale, c.job_id


def test_2_prepara_rifiuta_con_invio_in_corso_e_lo_mostra(ctx):
    reale, cid = _reale_confermata(ctx, chiave="a")
    t = reale.trasmetti(cid, chiave_richiesta="m")
    assert t.stato == I.ATTESA_INVIO_MANUALE
    with pytest.raises(ReinvioNonAmmesso, match="registra prima l'esito") as e:
        prepara(ctx, reale, chiave="b")
    assert e.value.dettagli["tentativo"] == t.job_id and e.value.dettagli["stato_tentativo"] == I.ATTESA_INVIO_MANUALE
    ctl_a = reale.job.leggi(cid)["input"]["controllo_job_id"]
    assert prepara(ctx, reale, chiave="a", controllo_job_id=ctl_a).job_id == cid   # stessa richiesta: stessa copia
    assert reale.leggi_copia(cid).stato == I.IN_INVIO                    # la copia in invio non e' stata toccata
    st = ctx["sv"].invio_stato(ctx["pid"])
    assert st["copia_attiva"] == cid and st["tentativo_aperto"]["job_id"] == t.job_id
    assert st["tentativo_aperto"]["da_riconciliare"] is True
    assert [x["stato"] for x in st["elenco_copie"]] == [I.IN_INVIO]
    tr = ctx["sv"].stato_elaborati(ctx["pid"])["trasmissione"]
    assert tr["copia_id"] == cid and tr["tentativo_stato"] == I.ATTESA_INVIO_MANUALE and "riconciliare" in tr["nota"]
    # esito incerto (consultazione senza esito): sempre bloccato
    r = reale.riconcilia(t.job_id, evidenze={"stato_invii": '{"ricevuteList":[],"result":{"esito":"OK"}}'})
    assert r.stato == I.ATTESA_INVIO_MANUALE
    with pytest.raises(ReinvioNonAmmesso):
        prepara(ctx, reale, chiave="c")
    # dopo il protocollo: copia trasmessa, nuova copia rifiutata con un altro motivo
    reale.riconcilia(t.job_id, evidenze={"protocollo": "26110714062316102", "verificato_su": "Ricerca ricevute"})
    with pytest.raises(ReinvioNonAmmesso, match="gia' trasmessa.*26110714062316102"):
        prepara(ctx, reale, chiave="d")
    tr = ctx["sv"].stato_elaborati(ctx["pid"])["trasmissione"]
    assert tr["stato"] == I.TRASMESSA and tr["protocollo"] == "26110714062316102" and tr["tentativo_aperto"] is None


def test_2_dopo_invio_non_avvenuto_si_prepara_di_nuovo(ctx):
    reale, cid = _reale_confermata(ctx, chiave="a")
    t = reale.trasmetti(cid, chiave_richiesta="m")
    reale.riconcilia(t.job_id, evidenze={"non_trasmesso": True, "verificato_su": "Ricerca ricevute: nessun invio"})
    assert reale.leggi_copia(cid).stato == I.CONFERMATA
    nuova = prepara(ctx, reale, chiave="b")
    assert nuova.stato == I.PREPARATA and reale.leggi_copia(cid).stato == I.OBSOLETA


def test_2_prova_simulata_aperta_non_blocca_la_copia_reale(ctx):
    reale, cid = _reale_confermata(ctx, chiave="a")
    p = I.InvioAdattatore(ctx["arch"], I.TrasportoSimulato(guasto="timeout_dopo_ricezione")).trasmetti(
        cid, chiave_richiesta="prova")
    assert p.stato == I.ESITO_INCERTO and p.dettaglio["prova_simulata"] is True
    assert reale.invio_aperto(ctx["pid"]) == (None, None)
    assert prepara(ctx, reale, chiave="b").stato == I.PREPARATA


def test_2_archivio_precedente_con_copia_piu_recente_mostra_il_tentativo_aperto(ctx, monkeypatch):
    """Archivio creato prima della correzione: una copia piu' recente preparata mentre la precedente era in invio.
    La vista deve mostrare la copia con il tentativo aperto, non copie[0]."""
    reale, cid = _reale_confermata(ctx, chiave="a")
    t = reale.trasmetti(cid, chiave_richiesta="m")
    monkeypatch.setattr(reale, "_blocco_nuova_copia", lambda *a, **k: None)
    nuova = prepara(ctx, reale, chiave="b")
    st = ctx["sv"].invio_stato(ctx["pid"])
    assert st["copie"][0]["job_id"] == nuova.job_id                    # la piu' recente resta la prima dell'elenco
    assert st["copia_attiva"] == cid and st["tentativo_aperto"]["job_id"] == t.job_id
    assert {x["copia_id"]: x["stato"] for x in st["elenco_copie"]} == {nuova.job_id: I.PREPARATA, cid: I.IN_INVIO}
    assert [x["attiva"] for x in st["elenco_copie"]] == [False, True]
    tr = ctx["sv"].stato_elaborati(ctx["pid"])["trasmissione"]
    assert tr["copia_id"] == cid and tr["stato"] == I.IN_INVIO and tr["copie"] == 2


def test_2_stati_pratica_rimossa_e_documento_allineato():
    assert not hasattr(I, "stati_pratica")
    doc = (Path(__file__).resolve().parents[1] / "docs" / "COLLEGAMENTI.md").read_text(encoding="utf-8")
    assert "stati_pratica" not in doc and "tentativo_aperto" in doc


def test_2_interfaccia_usa_la_copia_attiva():
    js = (Path(__file__).resolve().parents[1] / "src" / "successioni" / "static" / "app.js").read_text(encoding="utf-8")
    corpo = js[js.index("async function renderInvio("):js.index("async function renderRicevute(")]
    assert "const c = copie[0];" not in corpo
    assert "sti.copia_attiva" in corpo and "bloccoPrep" in corpo and "elenco_copie" in corpo
    assert "evidenze: { esi: testo }" in corpo and "Registra file .esi" in corpo       # .esi registrabile dalla GUI


def test_3_guida_prima_pratica_con_prepara_conferma_istruzioni():
    radice = Path(__file__).resolve().parents[1]
    guida = (radice / "docs" / "GUIDA_PRIMA_PRATICA_REALE.md").read_text(encoding="utf-8")
    pos = [guida.index(x) for x in ("Prepara invio", "Conferma questa copia", "Istruzioni per l'invio reale",
                                    "Desktop Telematico/Entratel *controllo SUC13")]
    assert pos == sorted(pos)                                  # il tentativo si crea PRIMA dell'invio con gli strumenti ufficiali
    assert min(guida.index("Registra protocollo"), guida.index("Registra file .esi")) > pos[-1]
    assert "(quadro EF) no" not in guida
    matr = (radice / "docs" / "MATRICE_COPERTURA.md").read_text(encoding="utf-8")
    assert "i legatari non sono esportabili" not in matr
    assert "| C `test_agevolazioni_nel_file_non_supportate` | non coperto |" not in matr


# ------------------------------------------------------------------ 4. valuta, ripiego del JAR, catasto, protocollo
def test_4_contatori_scartate_illeggibili_da_verificare():
    testo = C.decodifica(a10("a10_positivo.dgn"))
    riga9 = next(r for r in testo.splitlines() if r.startswith("9"))
    alterata = riga9[:37] + "  ??  " + riga9[43:]                      # scartate per errori bloccanti illeggibile
    d = C.leggi_dgn(testo.replace(riga9, alterata))
    assert d["riepilogo"]["scartate_errori_bloccanti"] is None
    stato, motivi = C.valuta(d, None)
    assert stato == "da_verificare" and any("scartate_errori_bloccanti" in m for m in motivi)
    vuota = riga9[:1] + " " * 6 + riga9[7:]                              # elaborate illeggibile: non e' «0 elaborate»
    assert C.valuta(C.leggi_dgn(testo.replace(riga9, vuota)), None)[0] == "da_verificare"
    assert C.valuta(C.leggi_dgn(testo), None)[0] == "positivo"


def test_4_ripiego_manuale_del_jar_riprende_lo_stesso_job_con_sha(arch, tmp_path):
    xml = tmp_path / "a10.xml"
    xml.write_bytes(a10("a10_positivo.xml"))
    ctl = C.ControlloJar(arch, C.ConfigControllo(java=None, cartella_jar=tmp_path / "manca"))
    a = ctl.esegui(xml, pratica_id="pr_1", revisione=2)
    b = ctl.esegui(xml, pratica_id="pr_1", revisione=2)
    assert a.job_id == b.job_id and a.stato == "attesa_diagnostico"
    assert len(RegistroJob(arch).elenca(C.TIPO_JOB, "pr_1")) == 1
    sha = RegistroJob(arch).leggi(a.job_id)["input"]["xml_sha256"]
    assert sha in a.azione_richiesta and "successione_rev2.xml" in a.azione_richiesta


def test_4_catasto_json_manuale_malformato_e_completo_dichiarato(arch):
    ad = K.CatastoEntratelAdattatore(arch)
    r = ad.avvia("pr_1", {"soggetto_cf": "RSSMRA40A01H501K"})
    for cattivo in (b"{non json", b"\xff\xfe", b"[1, 2]", json.dumps({"immobili": "x"}).encode(),
                    json.dumps({"immobili": [], "limiti": [1]}).encode()):
        with pytest.raises(DatiNonValidi):
            ad.registra_originale(r.job_id, cattivo, formato=K.FORMATO_INTERNO, fonte="a mano")
    assert ad.leggi(r.job_id).stato == K.ATTESA_UTENTE
    corpo = json.dumps({"completo": True, "immobili": [{"catasto": "F", "comune": "H501", "foglio": "1",
                                                        "particella": "2", "subalterno": "3"}]}).encode()
    r = ad.registra_originale(r.job_id, corpo, formato=K.FORMATO_INTERNO, fonte="a mano")
    assert r.stato == K.CARICATO_MANUALMENTE and r.stato != K.COMPLETATO
    assert r.dettaglio["completezza"]["completo"] is False
    prop = ad.proponi(r.job_id, {"beni": [], "persone": []})
    assert prop.dettaglio["proposta"]["segnalazioni"][0]["codice"] == "CARICATO_MANUALMENTE"
    assert ad.riprendi(r.job_id).stato == K.CARICATO_MANUALMENTE        # stato terminale


def test_4_protocollo_senza_evidenza_rifiutato(ctx):
    reale, cid = _reale_confermata(ctx)
    t = reale.trasmetti(cid, chiave_richiesta="m")
    for ev in ({"protocollo": "26110714062316102"}, {"protocollo": "26110714062316102", "verificato_su": "  "}):
        with pytest.raises(DatiNonValidi, match="verificato_su"):
            reale.riconcilia(t.job_id, evidenze=ev)
    assert reale.leggi_tentativo(t.job_id).stato == I.ATTESA_INVIO_MANUALE
