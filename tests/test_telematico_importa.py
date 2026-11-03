"""Importazione del file telematico SUC13: andata e ritorno con l'esportazione (dati sintetici) e rifiuto dei file non importabili."""
import copy
from datetime import date

import pytest
from starlette.testclient import TestClient

from successioni.archivio import Archivio
from successioni.errori import DatiNonValidi
from successioni.servizio import Servizio
from successioni.telematico.esporta import esporta_xml
from successioni.telematico.importa import XmlNonImportabile, importa_xml
from successioni.web import crea_app
from telematico_casi import caso_a10, caso_testamento, caso_testamento_legatario, contesto_caso_a10

CTX = contesto_caso_a10(data_riferimento=date(2025, 9, 1))


@pytest.fixture
def sv(tmp_path):
    return Servizio(Archivio(tmp_path / "dati"))


def _riesporta(sv, xml: bytes):
    """Importa, ricrea la pratica e la riesporta come farebbe l'utente dopo aver riacquisito gli allegati."""
    r = sv.importa_xml_telematico(xml)
    dati = sv.leggi(r["pratica_id"])["dati"]
    orig = caso_a10()
    dati["documenti_ref"] = orig["documenti_ref"]                      # gli allegati non si importano: si riacquisiscono
    dati["opzioni"]["telematico"]["dichiarazione"]["dichiara_copie_conformi"] = True
    return r, dati, esporta_xml(dati, CTX)


def test_andata_e_ritorno_identica(sv):
    originale = esporta_xml(caso_a10(), CTX)
    assert originale.xml is not None
    r, dati, nuovo = _riesporta(sv, originale.xml)
    assert nuovo.errori == [] and nuovo.xml == originale.xml
    assert r["importato"] == {"eredi": 2, "terreni": 1, "fabbricati": 1, "disponibilita_finanziarie": 1, "passivita": 2}


def test_dati_nel_modello(sv):
    r = sv.importa_xml_telematico(esporta_xml(caso_a10(), CTX).xml)
    dati = sv.leggi(r["pratica_id"])["dati"]
    per_ruolo = {}
    for p in dati["persone"]:
        per_ruolo.setdefault(p["ruolo"], []).append(p)
    d = per_ruolo["defunto"][0]
    assert (d["codice_fiscale"], d["data_nascita"], d["data_decesso"], d["comune_decesso"]) == ("RSSMRA40A01H501K", "1940-01-01", "2025-03-10", "ROMA")
    assert sorted(p["nome"] for p in per_ruolo["erede"]) == ["ANNA", "LUCA"]
    assert {(p["nome"], p["tipo_soggetto"], p["grado_parentela"], p["relazione_con_defunto"], p["sesso"]) for p in per_ruolo["erede"]} == {
        ("ANNA", "1", "02", "02", "F"), ("LUCA", "1", "02", "02", "M")}
    casa = next(b for b in dati["beni"] if b["tipo"] == "fabbricato")
    assert (casa["foglio"], casa["particella"], casa["subalterno"], casa["valore"], casa["rendita"]) == ("100", "200", "3", "126000", "1000.00")
    assert casa["quota_defunto"] == {"num": 1, "den": 1}
    terr = next(b for b in dati["beni"] if b["tipo"] == "terreno")
    assert terr["quota_defunto"] == {"num": 1, "den": 2}
    assert dati["opzioni"]["telematico"]["beni"][terr["id"]]["superficie"] == {"ettari": 1, "are": 20}
    assert len(dati["devoluzioni"]) == 6
    assert r["titolo"] == "Importata: ROSSI MARIO"


def test_presentatore_coincide_con_un_erede(sv):
    r = sv.importa_xml_telematico(esporta_xml(caso_a10(), CTX).xml)
    dati = sv.leggi(r["pratica_id"])["dati"]
    pres = dati["opzioni"]["telematico"]["dichiarazione"]["presentatore"]
    anna = next(p for p in dati["persone"] if p["nome"] == "ANNA")
    assert pres == {"persona_id": anna["id"], "codice_carica": "1", "telefono": "0612345678"}
    assert not [p for p in dati["persone"] if p["ruolo"] == "presentatore"]


def test_presentatore_estraneo_diventa_persona(sv):
    """L'esportazione non produce ancora presentatori estranei agli eredi (solo carica 1): il file e' modificato a mano."""
    t = _xml().decode()
    i = t.index("<suc:Presentatore>")
    f = t.index("</suc:Presentatore>")
    t = t[:i] + t[i:f].replace("RSSNNA70A41H501J", "VRDPLA80C03H501A") + t[f:]
    r = sv.importa_xml_telematico(t.encode())
    dati = sv.leggi(r["pratica_id"])["dati"]
    pres = [p for p in dati["persone"] if p["ruolo"] == "presentatore"]
    assert len(pres) == 1 and pres[0]["codice_fiscale"] == "VRDPLA80C03H501A" and pres[0]["cognome"] == "ROSSI"
    assert dati["opzioni"]["telematico"]["dichiarazione"]["presentatore"] == {"codice_carica": "1", "telefono": "0612345678"}


def test_quadri_non_importati_sono_dichiarati(sv):
    r = importa_xml(esporta_xml(caso_a10(), CTX).xml)
    assert r["non_importato"] == ["QuadroEE: totali ricalcolati dal programma", "QuadroEF: imposte ricalcolate dal programma",
                                  "QuadroEG: allegati: da riacquisire", "QuadroEH: dichiarazioni e testamento: da reinserire"]
    assert r["avvisi"] == []


def test_ripartizione_non_uguale_si_conserva(sv):
    d = caso_testamento()          # con la devoluzione per legge le quote non di legge sono rifiutate (QUOTA_DI_LEGGE)
    d["opzioni"]["telematico"]["passivita"]["ps_mutuo01"]["ripartizione"] = [
        {"persona_id": "p_anna0001", "quota": "1/4"}, {"persona_id": "p_luca0001", "quota": "3/4"}]
    es = esporta_xml(d, CTX)
    assert es.xml is not None, es.errori
    r = sv.importa_xml_telematico(es.xml)
    dati = sv.leggi(r["pratica_id"])["dati"]
    ps = next(p for p in dati["passivita"] if p["descrizione"].startswith("MUTUO"))
    rip = dati["opzioni"]["telematico"]["passivita"][ps["id"]]["ripartizione"]
    assert [x["quota"] for x in rip] == [{"num": 1, "den": 4}, {"num": 3, "den": 4}]
    assert dati["opzioni"]["telematico"]["passivita"][ps["id"]]["bene_id"].startswith("b_ec")


# ------------------------------------------------------------------------------------------------ file non importabili
def _xml():
    return esporta_xml(caso_a10(), CTX).xml


@pytest.mark.parametrize("xml,frammento", [
    (b"non e' xml", "non e' un XML valido"),
    (b"<a/>", "nessuna dichiarazione"),
])
def test_file_non_importabile(xml, frammento):
    with pytest.raises(XmlNonImportabile, match=frammento):
        importa_xml(xml)


def test_due_dichiarazioni_non_si_importano():
    testo = _xml().decode()
    i = testo.index("<suc:Dichiarazione ")
    f = testo.index("</suc:Dichiarazione>") + len("</suc:Dichiarazione>")
    doppio = testo[:f] + testo[i:f] + testo[f:]
    with pytest.raises(XmlNonImportabile, match="2 dichiarazioni"):
        importa_xml(doppio.encode())


def test_senza_frontespizio_o_defunto():
    t = _xml().decode()
    with pytest.raises(XmlNonImportabile, match="codice fiscale del defunto"):
        importa_xml(t.replace("<suc:CodiceFiscaleDefunto>RSSMRA40A01H501K</suc:CodiceFiscaleDefunto>", "").encode())
    with pytest.raises(XmlNonImportabile, match="frontespizio assente"):
        importa_xml(t.replace("suc:Frontespizio", "suc:Altro").encode())


def test_data_in_formato_errato():
    t = _xml().decode().replace("<suc:DataDecesso>10032025", "<suc:DataDecesso>2025-03-10")
    with pytest.raises(XmlNonImportabile, match="ggmmaaaa"):
        importa_xml(t.encode())


def test_data_inesistente():
    t = _xml().decode().replace("<suc:DataDecesso>10032025", "<suc:DataDecesso>31022025")
    with pytest.raises(ValueError):
        importa_xml(t.encode())


def test_devoluzione_verso_erede_inesistente():
    t = _xml().decode()
    i = t.index("<suc:DevoluzioneEB>")
    t = t[:i] + t[i:].replace("<suc:Rigo>2</suc:Rigo>", "<suc:Rigo>9</suc:Rigo>", 1)
    with pytest.raises(XmlNonImportabile, match="erede inesistente"):
        importa_xml(t.encode())


def test_numero_non_valido_e_quota_non_intera():
    t = _xml().decode()
    with pytest.raises(XmlNonImportabile, match="non valido"):
        importa_xml(t.replace("<reg:RenditaCatastale>1000,00", "<reg:RenditaCatastale>mille").encode())
    with pytest.raises(XmlNonImportabile, match="atteso un intero"):
        importa_xml(t.replace("<suc:PossessoDenominatore>2</suc:PossessoDenominatore>", "<suc:PossessoDenominatore>2,5</suc:PossessoDenominatore>", 1).encode())


def test_cespite_collegato_non_importato_e_avviso():
    t = _xml().decode().replace("<suc:Quadro>EC</suc:Quadro>", "<suc:Quadro>EO</suc:Quadro>")
    r = importa_xml(t.encode())
    assert any("cespite collegato" in a and "EO" in a for a in r["avvisi"])


def test_servizio_traduce_l_errore(sv):
    with pytest.raises(DatiNonValidi, match="file non importabile"):
        sv.importa_xml_telematico(b"niente")
    assert sv.elenca() == []


def test_titolo_esplicito(sv):
    r = sv.importa_xml_telematico(_xml(), titolo="Mia pratica")
    assert r["titolo"] == "Mia pratica" and r["revisione"] == 1


# ------------------------------------------------------------------------------------------------------------ API
def _client(tmp_path):
    return TestClient(crea_app(Servizio(Archivio(tmp_path / "web")), token="sintetico", ammetti_host_di_prova=True))


def test_api_importa(tmp_path):
    with _client(tmp_path) as cl:
        r = cl.post("/api/importa?t=sintetico", content=_xml(), headers={"Content-Type": "application/xml"})
        assert r.status_code == 200
        j = r.json()
        assert j["importato"]["eredi"] == 2 and j["pratica_id"].startswith("pr_")
        assert cl.get(f"/api/pratiche/{j['pratica_id']}?t=sintetico").status_code == 200


def test_api_importa_richiede_token_e_rifiuta_file_vuoto_o_errato(tmp_path):
    with _client(tmp_path) as cl:
        assert cl.post("/api/importa", content=_xml()).status_code == 401
        assert cl.post("/api/importa?t=sintetico", content=b"").status_code == 422
        r = cl.post("/api/importa?t=sintetico", content=b"<a/>")
        assert r.status_code == 422 and "nessuna dichiarazione" in r.json()["messaggio"]


def test_tipo_soggetto_2_importato_come_legatario():
    es = esporta_xml(caso_testamento_legatario(), CTX)
    assert es.xml is not None, [(e.percorso, e.codice) for e in es.errori]
    r = importa_xml(es.xml)
    assert any(o.get("coll") == "persone" and o["campi"].get("ruolo") == "legatario"
               and o["campi"].get("codice_fiscale") == "VRDPLA80C03H501A" for o in r["operazioni"])


def test_passivita_collegata_a_una_disponibilita_finanziaria(sv):
    t = _xml().decode().replace("<suc:Quadro>EC</suc:Quadro>", "<suc:Quadro>ER</suc:Quadro>")
    r = sv.importa_xml_telematico(t.encode())
    dati = sv.leggi(r["pratica_id"])["dati"]
    ps = next(p for p in dati["passivita"] if p["descrizione"].startswith("MUTUO"))
    bene = next(b for b in dati["beni"] if b["tipo"] == "disponibilita_finanziaria")
    assert dati["opzioni"]["telematico"]["passivita"][ps["id"]]["bene_id"] == bene["id"]
