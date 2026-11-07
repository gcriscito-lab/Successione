"""Risultanze catastali via Entratel (area 3): macchina a stati, ripresa, duplicati, importazione selettiva (A13-A15).

Tutto cio' che usa `TrasportoSimulato` e' SIMULAZIONE (esito 'simulazione'): non prova l'interoperabilita'.
"""
import json
from pathlib import Path

import pytest

import successioni.collegamenti.catasto as K
from successioni.archivio import Archivio
from successioni.collegamenti.base import Esito
from successioni.errori import DatiNonValidi
from successioni.servizio import Servizio

FIXTURE = json.loads((Path(K.__file__).parent / "fixture" / "catasto_simulazione_v1.json").read_text("utf-8"))
CF = FIXTURE["cf_defunto"]


@pytest.fixture
def arch(tmp_path):
    return Archivio(tmp_path / "dati")


def avvia_scenario(arch, passi=None):
    tr = K.TrasportoSimulato(passi or FIXTURE["passi"])
    ad = K.CatastoEntratelAdattatore(arch, tr)
    r = ad.avvia("pr_1", {"soggetto_cf": CF, "catasto": "entrambi"}, chiave="cat-1")
    return ad, tr, r


def test_a15_stati_autenticazione_sessione_scaduta_e_ripresa_dopo_chiusura(arch):
    ad, tr, r = avvia_scenario(arch)
    assert r.esito is Esito.SIMULAZIONE and r.stato == K.ATTESA_UTENTE and "Autenticarsi" in r.azione_richiesta
    r = ad.riprendi(r.job_id, autenticazione_confermata=True)
    assert r.stato == K.SESSIONE_SCADUTA and r.dettaglio["pagine"] == 1 and r.dettaglio["immobili"] == 2
    # chiusura del client: nuovo adattatore sullo stesso archivio; la sessione (in memoria) e' persa
    ad2 = K.CatastoEntratelAdattatore(Archivio(arch.base), tr)
    letto = ad2.leggi(r.job_id)
    assert letto.stato == K.SESSIONE_SCADUTA and letto.dettaglio["pagine"] == 1  # nulla di inventato o perso
    r = ad2.riprendi(r.job_id, autenticazione_confermata=True)
    assert r.dettaglio["pagine"] == 2
    assert tr.chiamate[-1]["pagina"] == "p2"  # ripresa dalla pagina registrata, non dall'inizio
    # l'ultima pagina dichiara un limite (graffati): risultato PARZIALE, non completato
    assert r.stato == K.PARZIALE and "graffate" in r.dettaglio["completezza"]["motivo"]
    assert ad2.riprendi(r.job_id).stato == K.PARZIALE  # stato terminale: nessuna nuova interrogazione
    stati = [c["stato"] for c in ad2.job.leggi(r.job_id)["risultato"]["cronologia"]]
    assert stati == [K.AVVIATO, K.ATTESA_UTENTE, K.AVVIATO, K.SESSIONE_SCADUTA, K.PARZIALE]


def test_a13_risultati_con_provenienza_ambito_e_segnalazioni(arch):
    ad, tr, r = avvia_scenario(arch)
    ad.riprendi(r.job_id, autenticazione_confermata=True)
    res = ad.leggi_risultati(ad.riprendi(r.job_id, autenticazione_confermata=True).job_id)
    d = res.dettaglio
    assert d["ambito"] == {"soggetto_cf": CF, "catasto": "entrambi", "territorio": "nazionale", "note": None}
    assert d["provenienza"]["servizio"] == "simulazione" and d["provenienza"]["acquisito_il"]
    assert len(res.artefatti) == 2 and all(a["ruolo"] == "risultanze_originali" for a in res.artefatti)
    chiavi = [im["chiave"] for im in d["immobili"]]
    assert len(chiavi) == len(set(chiavi)) == 4  # il C/6 restituito su due pagine compare una sola volta
    a2 = next(im for im in d["immobili"] if im.get("categoria") == "A/2")
    assert a2["altri_campi"] == {"codice_sconosciuto_servizio": "XK-9"}  # campo ignoto conservato
    codici = {s["codice"] for s in d["segnalazioni"]}
    assert {"CAMPI_NON_RICONOSCIUTI", "GRAFFATI", "PORZIONE"} <= codici


def test_chiave_duplicati_normalizza_zeri_e_distingue_catasto():
    assert K.chiave_immobile("F", "h501", "", "0012", "345", "07") == K.chiave_immobile("fabbricato", "H501", None,
                                                                                         "12", "345", "7")
    assert K.chiave_immobile("T", "H501", "", "12", "345", "") != K.chiave_immobile("F", "H501", "", "12", "345", "")
    assert K.id_bene(K.chiave_immobile("F", "H501", "", "12", "345", "7")).startswith("b_")


def _pratica(sv):
    p = sv.crea_pratica("Prova catasto", iniziali=[
        {"op": "upsert", "coll": "persone", "campi": {"cognome": "ROSSI", "nome": "MARIO", "ruolo": "defunto",
                                                      "codice_fiscale": CF}},
        {"op": "upsert", "coll": "beni", "id": "b_manuale01", "campi": {
            "tipo": "fabbricato", "comune": "ROMA", "codice_comune": "H501", "foglio": "12", "particella": "345",
            "subalterno": "7",
            "rendita": "800.00"}}])
    return p["pratica_id"]


def test_a14_importazione_selettiva_ripetuta_senza_doppioni(arch):
    sv = Servizio(arch)
    pid = _pratica(sv)
    ad, tr, r = avvia_scenario(arch)
    ad.riprendi(r.job_id, autenticazione_confermata=True)
    ad.riprendi(r.job_id, autenticazione_confermata=True)
    prop = ad.proponi(r.job_id, sv.leggi(pid)["dati"]).dettaglio["proposta"]
    assert prop["origine"] == "acquisito"
    # bene gia' inserito a mano: la rendita diversa e' un conflitto, non una sovrascrittura
    conf = prop["conflitti"][0]
    assert conf["bene_id"] == "b_manuale01" and conf["campi"][0]["campo"] == "rendita"
    upd = next(o for o in prop["operazioni"] if o["id"] == "b_manuale01")
    assert "rendita" not in upd["campi"] and "foglio" not in upd["campi"]  # identificativi non toccati
    assert upd["campi"]["quota_defunto"] == {"num": 1, "den": 2} and upd["campi"]["categoria"] == "A/2"
    codici = [s["codice"] for s in prop["segnalazioni"]]
    assert "DEFUNTO_NON_TITOLARE" in codici and "IMPORTO_NON_VALIDO" in codici
    assert "SITUAZIONE_AL_DECESSO" in codici and "LIMITE_DEL_SERVIZIO" in codici
    assert "ACQUISIZIONE_NON_COMPLETA" in codici  # stato parziale
    terreno = next(o for o in prop["operazioni"] if o["campi"].get("tipo") == "terreno")
    assert "rendita" not in terreno["campi"]  # i redditi dei terreni non hanno destinazione nel modello
    rev = sv.leggi(pid)["revisione"]
    sv.aggiorna(pid, rev, prop["operazioni"], origine="acquisito", chiave="imp-1")
    dati = sv.leggi(pid)["dati"]
    n_beni = len(dati["beni"])
    assert n_beni == 4 and sv.verifica(pid)  # schema rispettato
    assert dati["beni"][0]["_origine"]["rendita"] == "inserito"  # il dato manuale e' rimasto
    # seconda importazione delle stesse risultanze: nessuna operazione, nessun doppione
    prop2 = ad.proponi(r.job_id, dati).dettaglio["proposta"]
    assert prop2["operazioni"] == [] and len(prop2["invariati"]) == 3 and len(prop2["conflitti"]) == 1
    # nuova acquisizione con una rendita aggiornata: una sola modifica, sullo stesso bene
    passi = [{"tipo": "risultati", "completo": True, "immobili": [
        {"catasto": "F", "codice_comune": "H501", "foglio": "12", "particella": "345", "subalterno": "8",
         "categoria": "C/6", "rendita": "99.00", "titolarita": [{"cf": CF, "diritto": "proprieta",
                                                                 "quota": {"num": 1, "den": 1}}]}]}]
    ad3 = K.CatastoEntratelAdattatore(arch, K.TrasportoSimulato(passi))
    r3 = ad3.avvia(pid, {"soggetto_cf": CF})
    assert r3.stato == K.COMPLETATO
    prop3 = ad3.proponi(r3.job_id, dati).dettaglio["proposta"]
    assert prop3["operazioni"] == [{"op": "upsert", "coll": "beni", "id": K.id_bene(
        K.chiave_immobile("F", "H501", "", "12", "345", "8")), "campi": {"rendita": "99.00"}}]
    sv.aggiorna(pid, sv.leggi(pid)["revisione"], prop3["operazioni"], origine="acquisito")
    assert len(sv.leggi(pid)["dati"]["beni"]) == n_beni


def _im(**kw):
    base = {"catasto": "F", "foglio": "12", "particella": "345", "subalterno": "7", "categoria": "A/2",
            "titolarita": [{"cf": CF, "diritto": "proprieta", "quota": {"num": 1, "den": 1}}]}
    imm, _ = K.normalizza([{**base, **kw}])
    return imm


def _bene(**kw):
    return {"id": "b_x", "tipo": "fabbricato", "foglio": "12", "particella": "345", "subalterno": "7",
            "categoria": "A/2", "quota_defunto": {"num": 1, "den": 1}, "diritto": "proprieta", **kw}


def test_bene_con_nome_e_codice_riconosciuto_per_codice():
    dati = {"beni": [_bene(comune="ROMA", codice_comune="h501")], "persone": []}
    prop = K.proponi_importazione(_im(codice_comune="H501"), dati, cf_defunto=CF)
    assert prop["nuovi"] == [] and prop["invariati"] and prop["operazioni"] == []
    # codici diversi: nessuna corrispondenza anche se il nome coincidesse
    prop = K.proponi_importazione(_im(codice_comune="F205", comune="ROMA"), dati, cf_defunto=CF)
    assert len(prop["nuovi"]) == 1


def test_bene_solo_nome_riconosciuto_da_visura_con_nome():
    dati = {"beni": [_bene(comune="Roma")], "persone": []}
    prop = K.proponi_importazione(_im(comune="ROMA"), dati, cf_defunto=CF)
    assert prop["nuovi"] == [] and prop["invariati"]
    # visura con codice e nome: riconosciuto per nome, il codice mancante viene proposto sul bene esistente
    prop = K.proponi_importazione(_im(comune="ROMA", codice_comune="H501"), dati, cf_defunto=CF)
    assert prop["nuovi"] == [] and prop["operazioni"] == [
        {"op": "upsert", "coll": "beni", "id": "b_x", "campi": {"codice_comune": "H501"}}]
    # nome diverso: nessuna corrispondenza
    assert len(K.proponi_importazione(_im(comune="MILANO"), dati, cf_defunto=CF)["nuovi"]) == 1


def test_bene_con_codice_nel_campo_comune_dati_precedenti():
    dati = {"beni": [_bene(comune="H501")], "persone": []}
    prop = K.proponi_importazione(_im(codice_comune="H501"), dati, cf_defunto=CF)
    assert prop["nuovi"] == []


def test_proposta_codice_in_codice_comune_e_nome_in_comune():
    prop = K.proponi_importazione(_im(codice_comune="H501", comune="San Giovanni Rotondo"), {"beni": []},
                                  cf_defunto=CF)
    campi = prop["operazioni"][0]["campi"]
    assert campi["codice_comune"] == "H501" and campi["comune"] == "San Giovanni Rotondo"
    campi = K.proponi_importazione(_im(codice_comune="H501"), {"beni": []}, cf_defunto=CF)["operazioni"][0]["campi"]
    assert campi["codice_comune"] == "H501" and "comune" not in campi
    # codice restituito nel campo comune: riconosciuto dalla forma e messo in codice_comune
    campi = K.proponi_importazione(_im(comune="h501"), {"beni": []}, cf_defunto=CF)["operazioni"][0]["campi"]
    assert campi["codice_comune"] == "H501" and "comune" not in campi


def test_selezione_parziale(arch):
    ad, tr, r = avvia_scenario(arch, [{"tipo": "risultati", "completo": True, "immobili": FIXTURE["passi"][1][
        "immobili"]}])
    tutte = [im["chiave"] for im in ad.leggi_risultati(r.job_id).dettaglio["immobili"]]
    prop = ad.proponi(r.job_id, {"beni": [], "persone": []}, selezione=tutte[:1], cf_defunto=CF)
    assert len(prop.dettaglio["proposta"]["operazioni"]) == 1


def test_trasporto_reale_da_collaudare_e_registrazione_originale(arch):
    ad = K.CatastoEntratelAdattatore(arch)  # predefinito: TrasportoEntratelDaCollaudare, nessuna rete
    r = ad.avvia("pr_1", {"soggetto_cf": CF})
    assert r.esito is Esito.DA_COLLAUDARE and r.stato == K.ATTESA_UTENTE
    assert "Entratel" in r.azione_richiesta and "registra_originale" in r.azione_richiesta
    r = ad.registra_originale(r.job_id, b"%PDF-1.4 risultanze", formato="pdf", fonte="download Entratel")
    assert r.stato == K.ATTESA_UTENTE and len(r.artefatti) == 1 and "convertitore" in r.azione_richiesta
    corpo = json.dumps({"formato": K.FORMATO_INTERNO, "completo": True,
                        "immobili": FIXTURE["passi"][1]["immobili"]}).encode()
    r = ad.registra_originale(r.job_id, corpo, formato=K.FORMATO_INTERNO, fonte="conversione manuale")
    assert r.esito is Esito.DA_COLLAUDARE and r.stato == K.COMPLETATO and r.dettaglio["immobili"] == 2


def test_errori_ambito_e_servizio(arch):
    ad = K.CatastoEntratelAdattatore(arch, K.TrasportoSimulato([{"tipo": "errore", "messaggio": "servizio giu'"}]))
    with pytest.raises(DatiNonValidi):
        ad.avvia("pr_1", {"catasto": "F"})
    with pytest.raises(DatiNonValidi):
        ad.avvia("pr_1", {"soggetto_cf": CF, "catasto": "X"})
    r = ad.avvia("pr_1", {"soggetto_cf": CF})
    assert r.stato == K.ERRORE


def test_chiusura_parziale_da_utente(arch):
    ad, tr, r = avvia_scenario(arch)
    r = ad.chiudi_parziale(r.job_id, "ricerca interrotta dall'utente")
    assert r.stato == K.PARZIALE and r.dettaglio["completezza"]["completo"] is False
