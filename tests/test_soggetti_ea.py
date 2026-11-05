"""Soggetti del quadro EA: rinunciatari (tipo 3 con rinuncia, tipo 4), enti (gradi 37-39) e denominazione, residenza estera, soggetto
su piu' righi (erede + legatario). Regole: XSD fornituraSUC13_v1.xsd (annotazioni di QuadroEA/Soggetto, QuadroEH/.../Rinuncia),
Fascicolo I pp. PDF 17-18, Guida di calcolo p. 3. I casi positivi sono stati accettati dal controllo ufficiale SUC13 2.3.1 eseguito
in locale il 2026-11-05 (dati sintetici, non e' una verifica con l'Agenzia)."""
import copy
import re
from datetime import date

import pytest

from telematico_casi import caso_a10, caso_testamento, contesto_caso_a10
from successioni.telematico.esporta import esporta_xml
from successioni.telematico.identificativi import genera_cf_sintetico
from successioni.telematico import stati_esteri as SE
from test_telematico_controllo import _esegui, _motivo_salto

ESTREMI = {"ufficio_registrazione": "795", "serie": "1T", "numero_registrazione": "321", "data_registrazione": "2025-05-20"}
SALTO = _motivo_salto()


def esporta(d, **ctx):
    return esporta_xml(d, contesto_caso_a10(**ctx))


def codici(es):
    return {e.codice for e in es.errori}


def aggiungi(d, pid, nome, cognome, sesso, nascita, grado, tipo, *, rinuncia=True, numero="321", ruolo="erede", extra=None):
    cf = genera_cf_sintetico(cognome, nome, sesso, nascita, "H501")
    d["persone"].append({"id": pid, "_origine": {}, "cognome": cognome, "nome": nome, "codice_fiscale": cf,
                         "data_nascita": nascita, "luogo_nascita": "Roma", "ruolo": ruolo, "relazione_con_defunto": grado})
    t = {"sesso": sesso, "provincia_nascita": "RM", "tipo_soggetto": tipo}
    if rinuncia:
        t.update(rinuncia=True, rinuncia_estremi={**ESTREMI, "numero_registrazione": numero})
    t.update(extra or {})
    d["opzioni"]["telematico"]["persone"][pid] = t
    return cf


# ------------------------------------------------------------------------------------------------ casi
def caso_chiamato_rinunciatario():
    d = copy.deepcopy(caso_a10())
    aggiungi(d, "p_paolo001", "Paolo", "Rossi", "M", "1975-05-05", "02", "3")
    return d


def caso_coniuge_rinunciatario():
    d = copy.deepcopy(caso_a10())
    aggiungi(d, "p_marta001", "Marta", "Bianchi", "F", "1948-03-03", "01", "4")
    d["opzioni"]["telematico"]["dichiarazione"]["stato_civile"] = "2"
    return d


def caso_due_rinunciatari():
    d = caso_chiamato_rinunciatario()
    aggiungi(d, "p_giulia01", "Giulia", "Rossi", "F", "1978-06-06", "02", "3", numero="322")
    return d


def caso_estero(codice, stato, extra=None):
    d = copy.deepcopy(caso_a10())
    d["opzioni"]["telematico"]["persone"]["p_luca0001"]["residenza_estera"] = {
        "codice_stato": codice, "stato": stato, "localita": "Parigi", "indirizzo": "Rue de Test 1", **(extra or {})}
    return d


def caso_erede_e_legatario(valore="10000"):
    d = copy.deepcopy(caso_testamento())
    anna = next(p for p in d["persone"] if p["id"] == "p_anna0001")
    d["persone"].append({**copy.deepcopy(anna), "id": "p_leg0001", "ruolo": "legatario"})
    d["beni"].append({"id": "b_terr0002", "_origine": {}, "tipo": "terreno", "comune": "Roma", "foglio": "11", "particella": "21",
                      "valore": valore, "diritto": "1", "quota_defunto": "1/1"})
    d["devoluzioni"].append({"id": "d_terrleg1", "_origine": {}, "bene_id": "b_terr0002", "persona_id": "p_leg0001",
                             "quota": "1/1", "diritto": "1"})
    tel = d["opzioni"]["telematico"]
    tel["dichiarazione"]["tempistica_pagamento"] = "1"
    tel["persone"]["p_leg0001"] = dict(tel["persone"]["p_anna0001"])
    tel["beni"]["b_terr0002"] = {"provincia": "RM", "codice_comune": "H501", "codice_comune_amministrativo": "H501", "natura": "T",
                                 "tipologia_terreno": "3", "reddito_dominicale": "5.00",
                                 "superficie": {"ettari": 0, "are": 50, "centiare": 0}}
    return d


def caso_ente(grado="37", ruolo="legatario", den="COMUNE DI ESEMPIO", valore="10000"):
    d = copy.deepcopy(caso_testamento())
    d["persone"].append({"id": "p_ente0001", "_origine": {}, "codice_fiscale": "00000000018", "ruolo": ruolo,
                         "relazione_con_defunto": grado})
    d["beni"].append({"id": "b_terr0002", "_origine": {}, "tipo": "terreno", "comune": "Roma", "foglio": "11", "particella": "21",
                      "valore": valore, "diritto": "1", "quota_defunto": "1/1"})
    d["devoluzioni"].append({"id": "d_terrente", "_origine": {}, "bene_id": "b_terr0002", "persona_id": "p_ente0001",
                             "quota": "1/1", "diritto": "1"})
    tel = d["opzioni"]["telematico"]
    tel["dichiarazione"]["tempistica_pagamento"] = "1"
    tel["persone"]["p_ente0001"] = {"grado_parentela": grado, "denominazione": den}
    tel["beni"]["b_terr0002"] = {"provincia": "RM", "codice_comune": "H501", "codice_comune_amministrativo": "H501", "natura": "T",
                                 "tipologia_terreno": "3", "reddito_dominicale": "5.00",
                                 "superficie": {"ettari": 0, "are": 50, "centiare": 0}}
    return d


# ------------------------------------------------------------------------------------------------ rinunce: regole
def test_rinuncia_estremi_obbligatori():
    d = caso_chiamato_rinunciatario()
    del d["opzioni"]["telematico"]["persone"]["p_paolo001"]["rinuncia_estremi"]
    es = esporta(d)
    assert es.xml is None and "DATO_MANCANTE" in codici(es)


def test_rinuncia_non_ammessa_per_l_erede():
    d = caso_chiamato_rinunciatario()
    d["opzioni"]["telematico"]["persone"]["p_paolo001"]["tipo_soggetto"] = "1"
    es = esporta(d)
    assert es.xml is None and "REGOLA_TIPO_SOGGETTO" in codici(es)


def test_tipo4_richiede_il_grado_coniuge():
    d = caso_coniuge_rinunciatario()
    d["opzioni"]["telematico"]["persone"]["p_marta001"]["grado_parentela"] = "02"
    es = esporta(d)
    assert es.xml is None and "REGOLA_TIPO_SOGGETTO" in codici(es)


def test_il_rinunciatario_non_puo_essere_beneficiario():
    d = caso_chiamato_rinunciatario()
    d["devoluzioni"].append({"id": "d_casapaol", "_origine": {}, "bene_id": "b_casa0001", "persona_id": "p_paolo001",
                             "quota": "1/3", "diritto": "1"})
    es = esporta(d)
    assert es.xml is None and "DEVOLUZIONE_RINUNCIATARIO" in codici(es)


def test_il_dichiarante_non_puo_essere_rinunciatario():
    d = caso_a10()
    d["opzioni"]["telematico"]["persone"]["p_anna0001"].update(tipo_soggetto="3", rinuncia=True, rinuncia_estremi=dict(ESTREMI))
    es = esporta(d)
    assert es.xml is None and "REGOLA_RINUNCIA" in codici(es)


def test_trust_stato_e_altro_restano_bloccati_con_motivo():
    d = caso_chiamato_rinunciatario()
    d["opzioni"]["telematico"]["persone"]["p_paolo001"].update(tipo_soggetto="5")
    es = esporta(d)
    assert es.xml is None and any("tipo soggetto 5 (trust) non supportato" in n for n in es.non_supportato)
    d = copy.deepcopy(caso_a10())
    d["opzioni"]["telematico"]["persone"]["p_luca0001"]["grado_parentela"] = "36"
    es = esporta(d)
    assert es.xml is None and any("grado 36 (Stato) non supportato" in n for n in es.non_supportato)


# ------------------------------------------------------------------------------------------------ residenza estera / enti / multi riga
def test_residenza_estera_validazioni():
    es = esporta(caso_estero("29", "FRANCIA"))                                   # codice non di tre caratteri
    assert es.xml is None and "VALORE_NON_VALIDO" in codici(es)
    d = caso_estero("029", "FRANCIA")
    del d["opzioni"]["telematico"]["persone"]["p_luca0001"]["residenza_estera"]["indirizzo"]
    assert "DATO_MANCANTE" in codici(esporta(d))
    d = caso_estero("029", "FRANCIA")
    d["opzioni"]["telematico"]["persone"]["p_luca0001"]["residenza_estera"]["sconosciuta"] = "x"
    assert "VALORE_NON_VALIDO" in codici(esporta(d))


@pytest.mark.skipif(SE.tabella() is None, reason="componente di controllo non configurato (tabella degli Stati esteri)")
def test_codice_stato_estero_assente_dalla_tabella():
    es = esporta(caso_estero("999", "NESSUNO"))
    assert es.xml is None and "VALORE_NON_VALIDO" in codici(es)


def test_denominazione_obbligatoria_per_gli_enti_e_non_con_la_legge():
    d = caso_ente("37")
    del d["opzioni"]["telematico"]["persone"]["p_ente0001"]["denominazione"]
    assert "DATO_MANCANTE" in codici(esporta(d))
    d = caso_ente("37")
    d["opzioni"]["telematico"]["persone"]["p_ente0001"]["grado_parentela"] = "02"
    assert "VALORE_NON_VALIDO" in codici(esporta(d))               # denominazione con grado di persona fisica
    d = copy.deepcopy(caso_a10())                                    # devoluzione per legge: gradi 37-39 non ammessi
    d["persone"].append({"id": "p_ente0001", "_origine": {}, "codice_fiscale": "00000000018", "ruolo": "erede",
                         "relazione_con_defunto": "37"})
    d["opzioni"]["telematico"]["persone"]["p_ente0001"] = {"grado_parentela": "37", "denominazione": "COMUNE DI ESEMPIO"}
    assert "REGOLA_GRADO_LEGGE" in codici(esporta(d))


def test_soggetto_su_piu_righi_regole():
    d = caso_erede_e_legatario()
    d["opzioni"]["telematico"]["persone"]["p_leg0001"]["grado_parentela"] = "03"     # grado diverso sui due righi
    assert "REGOLA_SOGGETTO_MULTI_RIGA" in codici(esporta(d))
    d = caso_erede_e_legatario()
    d["persone"][-1]["ruolo"] = "erede"                                              # stesso tipo su entrambi i righi
    assert "REGOLA_SOGGETTO_MULTI_RIGA" in codici(esporta(d))


def test_soggetto_su_piu_righi_ordine_dipendente_resta_bloccato():
    d = caso_erede_e_legatario("2000000")
    d["opzioni"]["telematico"]["dichiarazione"]["tempistica_pagamento"] = "2"
    es = esporta(d, data_riferimento=date(2026, 3, 9))
    assert es.xml is None
    assert any("dipende dall'ordine" in m.messaggio or "stesso soggetto" in m.messaggio for m in es.quadri_mancanti)


# ------------------------------------------------------------------------------------------------ controllo ufficiale locale
def _xml(d, **ctx):
    es = esporta(d, **ctx)
    assert es.completo, [e.messaggio for e in es.errori] + es.non_supportato + [m.messaggio for m in es.quadri_mancanti]
    return es.xml


def _positivo(xml, tmp_path):
    stato, dgn, wri, _ = _esegui(xml, tmp_path)
    assert stato == "positivo", (dgn["diagnostici"], wri[:1200])
    assert [x["codice"] for x in dgn["diagnostici"]] == ["3345"]       # solo l'avviso sull'attestazione, come nel caso A10


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
@pytest.mark.parametrize("fabbrica", [caso_chiamato_rinunciatario, caso_coniuge_rinunciatario, caso_due_rinunciatari],
                         ids=["chiamato_rinunciatario", "coniuge_rinunciatario_tipo4", "due_rinunciatari"])
def test_controllo_ufficiale_rinunciatari(tmp_path, fabbrica):
    xml = _xml(fabbrica())
    assert xml.count(b"RegistrazioneRinuncia") >= 2                     # apertura e chiusura dell'elemento
    _positivo(xml, tmp_path)


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
def test_controllo_ufficiale_respinge_rinuncia_non_dichiarata_nel_quadro_ea(tmp_path):
    xml = _xml(caso_chiamato_rinunciatario())
    senza = re.sub(rb"<suc:Rinuncia>1</suc:Rinuncia>", b"", xml, count=1)
    assert senza != xml
    stato, dgn, _, _ = _esegui(senza, tmp_path)
    assert stato == "negativo", dgn["diagnostici"]


@pytest.mark.skipif(SALTO is not None or SE.tabella() is None, reason=SALTO or "tabella Stati esteri assente")
@pytest.mark.parametrize("nome,stato,extra", [("FRANCIA", "FRANCIA", None),
                                              ("STATI UNITI", "STATI UNITI D'AMERICA", {"stato_federato": "CALIFORNIA", "localita": "San Francisco"}),
                                              ("GERMANIA", "GERMANIA", {"localita": "Berlino"})])
def test_controllo_ufficiale_residenza_estera(tmp_path, nome, stato, extra):
    codice = next(k for k, v in SE.tabella().items() if v == nome)
    xml = _xml(caso_estero(codice, stato, extra))
    assert b"ResidenzaEstera" in xml
    _positivo(xml, tmp_path)


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
def test_controllo_ufficiale_erede_e_legatario_sullo_stesso_soggetto(tmp_path):
    xml = _xml(caso_erede_e_legatario())
    assert xml.count(b"RSSNNA70A41H501J") >= 3                           # due righi EA + EH (un solo rigo) + dichiarante
    _positivo(xml, tmp_path)


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
@pytest.mark.parametrize("grado", ["37", "38", "39"])
def test_controllo_ufficiale_enti(tmp_path, grado):
    xml = _xml(caso_ente(grado))
    assert b"<suc:Denominazione>COMUNE DI ESEMPIO</suc:Denominazione>" in xml
    _positivo(xml, tmp_path)


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
def test_controllo_ufficiale_ente_co_erede_del_fabbricato_e_denominazione_grado_35(tmp_path):
    d = caso_ente("38", ruolo="erede")
    d["devoluzioni"] = [x for x in d["devoluzioni"] if x["id"] != "d_casaluca"]
    d["devoluzioni"].append({"id": "d_casaente", "_origine": {}, "bene_id": "b_casa0001", "persona_id": "p_ente0001",
                             "quota": "1/2", "diritto": "1"})
    _positivo(_xml(d), tmp_path / "a")
    d = caso_ente("35", den="ASSOCIAZIONE NON RICONOSCIUTA ESEMPIO", valore="500000")
    d["opzioni"]["telematico"]["dichiarazione"]["tempistica_pagamento"] = "2"
    _positivo(_xml(d, data_riferimento=date(2026, 3, 9)), tmp_path / "b")
