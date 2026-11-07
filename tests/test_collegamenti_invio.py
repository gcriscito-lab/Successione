"""Preparazione, conferma, invio incerto, riconciliazione, ricevute ed esiti separati (area 3, A16-A19).

Nessun invio reale: `TrasportoSimulato` (esito 'simulazione') e `TrasportoManualeTracciato` (non trasmette nulla,
esito 'da_collaudare'). La prova A18 qui e' la simulazione locale di rete interrotta richiesta dalla specifica.
"""
from pathlib import Path

import pytest

import successioni.collegamenti.invio as I
from successioni.archivio import Archivio
from successioni.collegamenti.base import (ConfermaNonValida, Esito, RegistroJob, ReinvioNonAmmesso,
                                           TransizioneNonAmmessa)
from successioni.errori import DatiNonValidi
from successioni.servizio import Servizio

FIX = Path(I.__file__).parent / "fixture" / "controllo_reale_20261101"


@pytest.fixture
def ctx(tmp_path):
    arch = Archivio(tmp_path / "dati")
    sv = Servizio(arch)
    pid = sv.crea_pratica("Invio", iniziali=[
        {"op": "upsert", "coll": "persone", "id": "p_def00001", "campi": {"cognome": "ROSSI", "ruolo": "defunto"}},
        {"op": "upsert", "coll": "beni", "id": "b_casa0001", "campi": {"tipo": "fabbricato", "foglio": "1",
                                                                       "particella": "2", "rendita": "100.00"}}])[
        "pratica_id"]
    xml = tmp_path / "SUC13_prova.xml"
    xml.write_bytes((FIX / "frontespizio.xml").read_bytes())
    pdf = tmp_path / "stampa.pdf"
    pdf.write_bytes(b"%PDF-1.4 stampa sintetica")
    return {"arch": arch, "sv": sv, "pid": pid, "xml": xml, "pdf": pdf, "tmp": tmp_path}


def controllo_finto(ctx, *, esito="passato", stato="positivo", sha=None) -> str:
    """DOPPIO DI TEST: riga di controllo creata direttamente nel registro per provare le regole di conferma.
    Non e' il risultato di un controllo ufficiale."""
    from successioni.collegamenti.base import sha256_file
    d = ctx["sv"].leggi(ctx["pid"])
    j, _ = RegistroJob(ctx["arch"]).crea("controllo_ufficiale", ctx["pid"], {
        "xml_sha256": sha or sha256_file(ctx["xml"]), "impronta_dichiarativa": d["impronta_dichiarativa"],
        "doppio_di_test": True}, stato="completato", risultato={"esito": esito, "stato_controllo": stato})
    return j["job_id"]


def adesso_esi() -> str:
    """startDate del .esi (GGMMAAAAhhmmss, ora locale) al momento del test."""
    from datetime import datetime
    return datetime.now().strftime("%d%m%Y%H%M%S")


def prepara(ctx, ad, **kw):
    kw.setdefault("controllo_job_id", controllo_finto(ctx))
    return ad.prepara(ctx["pid"], elaborati=[{"percorso": ctx["xml"], "ruolo": "telematico"},
                                             {"percorso": ctx["pdf"], "ruolo": "stampa"}],
                      importi={"imposte_dovute": "1234.00"}, profilo={"intermediario_cf": "AAAAAA00A00A000A",
                                                                       "canale": "entratel"},
                      aspettative={"addebito": True, "voltura_automatica": True, "attestazione_richiesta": False},
                      **kw)


def confermata(ctx, ad, **kw):
    c = prepara(ctx, ad, **kw)
    return ad.conferma(c.job_id, impronta_mostrata=c.dettaglio["impronta_conferma"], utente="professionista")


# ------------------------------------------------------------------------- A17 / A16 conferma
def test_a17_copia_congelata_e_conferma_solo_dall_app(ctx):
    ad = I.InvioAdattatore(ctx["arch"], I.TrasportoSimulato())
    c = prepara(ctx, ad)
    assert c.stato == I.PREPARATA and c.esito is Esito.SIMULAZIONE
    assert [m["ruolo"] for m in c.dettaglio["manifest"]] == ["telematico", "stampa"]
    assert c.dettaglio["importi"] == {"imposte_dovute": "1234.00"} and c.dettaglio["revisione"] == 1
    with pytest.raises(ConfermaNonValida):
        ad.conferma(c.job_id, impronta_mostrata=c.dettaglio["impronta_conferma"], utente="claude", canale="mcp")
    with pytest.raises(ConfermaNonValida):
        ad.conferma(c.job_id, impronta_mostrata="0" * 64, utente="professionista")
    r = ad.conferma(c.job_id, impronta_mostrata=c.dettaglio["impronta_conferma"], utente="professionista")
    assert r.stato == I.CONFERMATA and r.dettaglio["conferma"]["utente"] == "professionista"
    # gli elaborati congelati restano leggibili e integri anche se il file originale cambia
    ctx["xml"].write_bytes(b"<modificato/>")
    assert ad.deposito.leggi(r.artefatti[0]).startswith(b"<?xml")


def test_a16_nota_interna_non_invalida_modifica_dichiarativa_si(ctx):
    ad = I.InvioAdattatore(ctx["arch"], I.TrasportoSimulato())
    c = confermata(ctx, ad)
    sv, pid = ctx["sv"], ctx["pid"]
    sv.aggiorna(pid, sv.leggi(pid)["revisione"], [{"op": "set", "sezione": "note", "campi": {"promemoria": "x"}}])
    assert ad.verifica_validita(c.job_id).stato == I.CONFERMATA
    sv.aggiorna(pid, sv.leggi(pid)["revisione"], [{"op": "upsert", "coll": "beni", "id": "b_casa0001",
                                                   "campi": {"rendita": "150.00"}}])
    r = ad.verifica_validita(c.job_id)
    assert r.stato == I.OBSOLETA and r.azione_richiesta.startswith("Pratica modificata")
    with pytest.raises(ConfermaNonValida):
        ad.trasmetti(c.job_id, chiave_richiesta="t1")


def test_requisiti_controllo_simulazione_non_sblocca_la_conferma(ctx):
    ad = I.InvioAdattatore(ctx["arch"], I.TrasportoSimulato())
    for ctl in (controllo_finto(ctx, esito="simulazione", stato="positivo"),
                controllo_finto(ctx, esito="fallito", stato="negativo"),
                controllo_finto(ctx, sha="f" * 64), None):
        c = prepara(ctx, ad, controllo_job_id=ctl)
        assert c.dettaglio["stato"] == I.PREPARATA and c.azione_richiesta.startswith("Requisiti")
        with pytest.raises(ConfermaNonValida):
            ad.conferma(c.job_id, impronta_mostrata=c.dettaglio["impronta_conferma"], utente="professionista")


def test_importi_e_ruoli_validati(ctx):
    ad = I.InvioAdattatore(ctx["arch"], I.TrasportoSimulato())
    with pytest.raises(DatiNonValidi):
        ad.prepara(ctx["pid"], elaborati=[{"percorso": ctx["xml"], "ruolo": "telematico"}],
                   importi={"imposte": "1.234,00"}, profilo={})
    with pytest.raises(DatiNonValidi):
        ad.prepara(ctx["pid"], elaborati=[{"percorso": ctx["pdf"], "ruolo": "stampa"}], importi={}, profilo={})


def test_nuova_copia_sostituisce_la_precedente(ctx):
    ad = I.InvioAdattatore(ctx["arch"], I.TrasportoSimulato())
    a = confermata(ctx, ad, chiave="copia-a")
    b = prepara(ctx, ad, chiave="copia-b")
    assert ad.leggi_copia(a.job_id).stato == I.OBSOLETA and b.stato == I.PREPARATA


# --------------------------------------------------------------------------------- A18 invio incerto
def test_a18_rete_interrotta_dopo_la_ricezione_nessun_reinvio_cieco(ctx):
    tr = I.TrasportoSimulato(guasto="timeout_dopo_ricezione")
    ad = I.InvioAdattatore(ctx["arch"], tr)
    c = confermata(ctx, ad)
    t = ad.trasmetti(c.job_id, chiave_richiesta="invio-1")
    assert t.stato == I.ESITO_INCERTO and t.esito is Esito.SIMULAZIONE and "NON reinviare" in t.azione_richiesta
    assert "TimeoutError" in t.dettaglio["errore_rete"] and tr.chiamate_trasmetti == 1
    # stessa richiesta ripetuta (es. il client riprova): stesso tentativo, nessuna chiamata al servizio
    assert ad.trasmetti(c.job_id, chiave_richiesta="invio-1").job_id == t.job_id and tr.chiamate_trasmetti == 1
    # nuova richiesta con altra chiave: rifiutata finche' l'esito e' incerto
    with pytest.raises(ReinvioNonAmmesso):
        ad.trasmetti(c.job_id, chiave_richiesta="invio-2")
    assert tr.chiamate_trasmetti == 1
    # anche un nuovo processo (client chiuso e riaperto) vede lo stesso stato e non reinvia
    ad2 = I.InvioAdattatore(Archivio(ctx["arch"].base), tr)
    with pytest.raises(ReinvioNonAmmesso):
        ad2.trasmetti(c.job_id, chiave_richiesta="invio-3")
    r = ad2.riconcilia(t.job_id)
    assert r.stato == I.TRASMESSO and r.dettaglio["protocollo"].startswith("SIM")
    assert r.dettaglio["prova"]["metodo"] == "consultazione del trasporto"
    assert ad2.leggi_copia(c.job_id).stato == I.TRASMESSA and tr.chiamate_trasmetti == 1
    # un errore successivo di consultazione non sovrascrive l'esito finale
    tr.consultazione_guasta = True
    assert ad2.riconcilia(t.job_id).stato == I.TRASMESSO
    with pytest.raises(ReinvioNonAmmesso):
        ad2.trasmetti(c.job_id, chiave_richiesta="invio-4")


def test_a18_richiesta_mai_arrivata_nuovo_tentativo_solo_esplicito(ctx):
    tr = I.TrasportoSimulato(guasto="timeout_prima")
    ad = I.InvioAdattatore(ctx["arch"], tr)
    c = confermata(ctx, ad)
    t = ad.trasmetti(c.job_id, chiave_richiesta="a")
    assert t.stato == I.ESITO_INCERTO
    assert ad.riconcilia(t.job_id).stato == I.ESITO_INCERTO  # la consultazione non permette di concludere
    with pytest.raises(DatiNonValidi):
        ad.riconcilia(t.job_id, evidenze={"non_trasmesso": True})  # serve indicare dove si e' verificato
    r = ad.riconcilia(t.job_id, evidenze={"non_trasmesso": True, "verificato_su": "Ricerca ricevute, 01/11/2026"})
    assert r.stato == I.NON_TRASMESSO and ad.leggi_copia(c.job_id).stato == I.CONFERMATA
    tr.guasto = None
    t2 = ad.trasmetti(c.job_id, chiave_richiesta="b")
    assert t2.stato == I.TRASMESSO and tr.chiamate_trasmetti == 2
    assert ad.leggi_copia(c.job_id).dettaglio["tentativi"] == [t.job_id, t2.job_id]


class TrasportoCheCade(I.TrasportoSimulato):
    def trasmetti(self, file, nome, metadati):
        self.chiamate_trasmetti += 1
        raise RuntimeError("processo interrotto durante la chiamata")


def test_a18_processo_interrotto_durante_la_chiamata_riconciliazione_con_esi(ctx):
    ad = I.InvioAdattatore(ctx["arch"], TrasportoCheCade())
    c = confermata(ctx, ad)
    with pytest.raises(RuntimeError):
        ad.trasmetti(c.job_id, chiave_richiesta="x")
    tid = ad.job.id_da_chiave(I.TIPO_TENTATIVO, "x")
    assert ad.leggi_tentativo(tid).stato == I.IN_TRASMISSIONE  # scritto prima della chiamata
    ad2 = I.InvioAdattatore(Archivio(ctx["arch"].base), I.TrasportoSimulato())
    with pytest.raises(ReinvioNonAmmesso):
        ad2.trasmetti(c.job_id, chiave_richiesta="y")
    # nome realistico: la copia scaricata dall'app si chiama copia_congelata.xml (web.py), Multifile riporta il .ccf;
    # startDate (ora locale) successiva alla creazione del tentativo
    esi = ('{"tipoOperazione":"INVIO","resultCode":"00","startDate":"' + adesso_esi() + '","endDate":"' + adesso_esi()
           + '","fileName":"copia_congelata.ccf","versioneApplicazione":"1.7.6 ","protocollo":"26110117344816257"}\n')
    r = ad2.riconcilia(tid, evidenze={"esi": esi})
    assert r.stato == I.TRASMESSO and r.dettaglio["protocollo"] == "26110117344816257"
    assert r.dettaglio["prova"]["metodo"].startswith("file .esi")


def test_rifiuto_definitivo_conservato(ctx):
    ad = I.InvioAdattatore(ctx["arch"], I.TrasportoSimulato(guasto="rifiuto", motivo_rifiuto="file scartato: X"))
    c = confermata(ctx, ad)
    t = ad.trasmetti(c.job_id, chiave_richiesta="r")
    assert t.stato == I.RIFIUTATO and t.dettaglio["motivazione"] == "file scartato: X"
    assert ad.riconcilia(t.job_id).dettaglio["motivazione"] == "file scartato: X"  # non sovrascritto
    assert ad.leggi_copia(c.job_id).stato == I.RIFIUTATA
    with pytest.raises(ConfermaNonValida):
        ad.trasmetti(c.job_id, chiave_richiesta="r2")


def test_seconda_copia_della_stessa_pratica_non_si_invia(ctx, monkeypatch):
    ad = I.InvioAdattatore(ctx["arch"], I.TrasportoSimulato())
    a = confermata(ctx, ad, chiave="a")
    assert ad.trasmetti(a.job_id, chiave_richiesta="ta").stato == I.TRASMESSO
    with pytest.raises(ReinvioNonAmmesso, match="gia' trasmessa"):     # review 3: rifiutata gia' alla preparazione
        confermata(ctx, ad, chiave="b")
    # seconda difesa (preparazione concorrente che ha superato il controllo): l'invio resta comunque bloccato
    monkeypatch.setattr(ad, "_blocco_nuova_copia", lambda *a, **k: None)
    b = confermata(ctx, ad, chiave="b")
    with pytest.raises(ReinvioNonAmmesso):
        ad.trasmetti(b.job_id, chiave_richiesta="tb")
    assert ad.leggi_tentativo(ad.job.id_da_chiave(I.TIPO_TENTATIVO, "tb")).stato == I.ANNULLATO


def test_invio_manuale_tracciato_non_trasmette(ctx):
    ad = I.InvioAdattatore(ctx["arch"])  # predefinito: TrasportoManualeTracciato
    c = confermata(ctx, ad)
    t = ad.trasmetti(c.job_id, chiave_richiesta="m")
    assert t.stato == I.ATTESA_INVIO_MANUALE and t.esito is Esito.DA_COLLAUDARE
    assert "NON trasmette" in t.azione_richiesta
    with pytest.raises(ReinvioNonAmmesso):
        ad.trasmetti(c.job_id, chiave_richiesta="m2")
    stato = ('{"ricevuteList":[{"tipoFornitura":"SUC13","nomeFile":"26110114062316102_x.rcc","data":"01/11/2026",'
             '"stato":"Ricevuto","protocollo":"26110114062316102","idRichiesta":"570"}],'
             '"result":{"esito":"OK","resultCode":"00"}}')
    r = ad.riconcilia(t.job_id, evidenze={"stato_invii": stato})
    assert r.stato == I.ATTESA_INVIO_MANUALE and r.dettaglio["candidati"][0]["protocollo"] == "26110114062316102"
    r = ad.riconcilia(t.job_id, evidenze={"protocollo": "26110114062316102", "verificato_su": "Ricerca ricevute"})
    assert r.stato == I.TRASMESSO and r.esito is Esito.DA_COLLAUDARE  # collegamento non automatico: da collaudare
    with pytest.raises(TransizioneNonAmmessa):
        ad.riconcilia(ad.job.crea(I.TIPO_TENTATIVO, None, {"copia_id": "x"}, stato=I.CREATO)[0]["job_id"])


# ----------------------------------------------------------------------------- A19 ricevute ed esiti
def test_a19_ricevute_ed_esiti_separati_associati_al_protocollo(ctx):
    ad = I.InvioAdattatore(ctx["arch"], I.TrasportoSimulato())
    c = confermata(ctx, ad)
    prot = ad.trasmetti(c.job_id, chiave_richiesta="p").dettaglio["protocollo"]
    st = ad.stato_esiti(prot)
    assert st["registrazione"] == "attesa" and st["pagamento"] == "atteso" and st["volture"] == "attese"
    assert st["attestazione"] == "non_applicabile" and st["fonte"].startswith("Succ_FASCICOLO_I")
    r1 = ad.associa(protocollo=prot, tipo="registrazione", esito="registrata", contenuto=b"ricevuta 2 (sintetica)",
                    nome="ric2.rel")
    assert r1.dettaglio["pratica_id"] == ctx["pid"]
    ad.associa(protocollo=prot, tipo="pagamento", esito="negativo", contenuto=b"ricevuta 3", nome="ric3.rel")
    ad.associa(protocollo=prot, tipo="volture", esito="parziali", contenuto=b"ricevuta 5", nome="ric5.rel",
               dettagli={"immobili_non_volturati": ["b_casa0001"]})
    ripetuta = ad.associa(protocollo=prot, tipo="volture", esito="parziali", contenuto=b"ricevuta 5", nome="ric5.rel",
                          dettagli={"immobili_non_volturati": ["b_casa0001"]})
    assert ripetuta.dettaglio["ripetuta"] is True
    st = ad.stato_esiti(prot)
    assert st["registrazione"] == "registrata"  # il pagamento negativo non cancella la registrazione
    assert st["pagamento"] == "negativo" and st["volture"] == "parziali" and st["copia_semplice"] == "attesa"
    assert len(st["documenti"]) == 3
    assert ad.deposito.leggi(ripetuta.artefatti[0]) == b"ricevuta 5"  # originale conservato
    ad.associa(protocollo=prot, tipo="registrazione", esito="scartata", contenuto=b"altra", nome="x.rel")
    assert ad.stato_esiti(prot)["registrazione"].startswith("contraddittorio")
    with pytest.raises(DatiNonValidi):
        ad.associa(protocollo=prot, tipo="registrazione", contenuto=b"y", nome="y")  # esito obbligatorio
    with pytest.raises(DatiNonValidi):
        ad.associa(protocollo=prot, tipo="seconda", contenuto=b"y", nome="y")  # tipo mai dedotto dall'ordine
    orfano = ad.associa(protocollo="999", tipo="da_classificare", contenuto=b"z", nome="z.pdf", pratica_id="pr_x")
    assert ad.job.leggi(orfano.job_id)["risultato"]["associazione"].startswith("solo protocollo")
    s = ctx["sv"].stato_elaborati(ctx["pid"])           # stato della pratica (stati_pratica rimossa, review 3)
    assert s["trasmissione"]["stato"] == I.TRASMESSA and s["trasmissione"]["protocollo"] == prot


# --------------------------------------------------------------------------------- Entratel-Multifile
def test_formati_multifile_dal_manuale():
    # esempi dell'allegato 3 e dell'allegato 2 del manuale (v1.1.1), anche spezzati su piu' righe
    esi = I.leggi_esi('{"tipoOperazione":"INVIO","resultCode":"00","startDate":"02032018173448",\n"endDate":'
                      '"02032018173448","fileName":"IVA_DATEVIT.ccf","versioneApplicazione":"1.0.9 ",'
                      '"protocollo":"18030217344816257"}\nriga non json\n{"tipoOperazione":"AUTENTICA",'
                      '"resultCode":"00","fileName":"IVA_DATEVIT.dcm"}')
    assert [e["tipoOperazione"] for e in esi] == ["INVIO", "AUTENTICA"] and esi[0]["versioneApplicazione"] == "1.0.9"
    st = I.leggi_stato_invii('{"ricevuteList":[{"codScartoFornitura":"03","tipoFornitura":"ASI00","nomeFile":'
                             '"x.rcc","data":"14/02/2018","stato":"Scartato","protocollo":"18021415455616001",'
                             '"idRichiesta":"null"}],"result":{"esito":"OK","resultCode":"00"}}')
    assert st["ricevute"][0]["stato"] == "Scartato"
    with pytest.raises(DatiNonValidi):
        I.leggi_stato_invii('{"x": 1}')
    assert I.richiesta_download("R01", "T1000400", protocollo="1")["numeroProtocollo"] == "1"
    with pytest.raises(DatiNonValidi):
        I.richiesta_download("R02", "T1000400")
    assert "runInvio.bat|.sh" in I.MULTIFILE["comandi"]["invio"]


def test_r12_esi_con_esito_negativo_non_sblocca_un_nuovo_invio(ctx):
    """Un .esi con resultCode diverso da 00 non prova il mancato ricevimento: l'esito resta incerto, niente doppio invio."""
    ad = I.InvioAdattatore(ctx["arch"], TrasportoCheCade())
    c = confermata(ctx, ad)
    with pytest.raises(RuntimeError):
        ad.trasmetti(c.job_id, chiave_richiesta="x")
    tid = ad.job.id_da_chiave(I.TIPO_TENTATIVO, "x")
    ad2 = I.InvioAdattatore(Archivio(ctx["arch"].base), I.TrasportoSimulato())
    esi = ('{"tipoOperazione":"INVIO","resultCode":"05","startDate":"' + adesso_esi() + '","endDate":"' + adesso_esi()
           + '","fileName":"copia_congelata.ccf","versioneApplicazione":"1.7.6 "}\n')
    r = ad2.riconcilia(tid, evidenze={"esi": esi})
    assert r.stato == I.ESITO_INCERTO and "non prova" in (r.azione_richiesta or "") and "NON reinviare" in r.azione_richiesta
    with pytest.raises(ReinvioNonAmmesso):                   # nessun nuovo tentativo finche' non c'e' una verifica esplicita
        ad2.trasmetti(c.job_id, chiave_richiesta="y")
    r2 = ad2.riconcilia(tid, evidenze={"non_trasmesso": True, "verificato_su": "Ricerca ricevute, 02/11/2026"})
    assert r2.stato == I.NON_TRASMESSO                       # solo la dichiarazione esplicita sblocca
