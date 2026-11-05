"""Quadri EG ed EH (src/successioni/telematico/quadri_efgh.py): separazione, unione civile, disabili e interdetti, reintegro dei diritti
di legittima, inventario/prospetto (EG3), richieste di agevolazioni ipocatastali (EG10). Dati sintetici.

Regole dalle annotazioni XSD di QuadroEH/.../Separazione, FlagNoScioglimentoUnioneCivile, Interdetti, ReintegroDiritti, FlagProspetto e di
QuadroEG; Fascicolo I pp. PDF 18 e 51-52 (lettere d, e, g, h, l). Ogni caso positivo e' stato accettato dal controllo ufficiale SUC13
2.3.1 eseguito in locale il 2026-11-05 (dati sintetici, nessun invio)."""
import copy

import pytest
from lxml import etree

from telematico_casi import caso_a10, contesto_caso_a10
from successioni.telematico.esporta import esporta_xml
from test_telematico_controllo import _esegui, _motivo_salto

SALTO = _motivo_salto()
D = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione"
EH = f"{D}/suc:QuadroEH"
SEZ = f"{EH}/suc:PrimoModulo/suc:SezioneI_DichSost"
MOD = f"{EH}/suc:Modulo/suc:SezioneI_DichSost"
REG1 = {"ufficio_registrazione": "795", "serie": "1T", "numero_registrazione": "321", "data_registrazione": "2025-05-20"}
REG2 = {"ufficio_registrazione": "795", "serie": "1T", "numero_registrazione": "322", "data_registrazione": "2025-05-21"}
REG3 = {"ufficio_registrazione": "795", "serie": "1T", "numero_registrazione": "323", "data_registrazione": "2025-05-22"}


def caso(stato_civile=None, dich=None, coniuge=False, disabili=(), cert=None, modif=None):
    d = copy.deepcopy(caso_a10())
    tel = d["opzioni"]["telematico"]
    if stato_civile:
        tel["dichiarazione"]["stato_civile"] = stato_civile
    if coniuge:                                           # Luca diventa il coniuge: coniuge + un figlio = 1/2 e 1/2, come due figli
        d["persone"][2]["relazione_con_defunto"] = "01"
        tel["persone"]["p_luca0001"]["grado_parentela"] = "01"
    for pid in disabili:
        tel["persone"][pid]["portatore_handicap"] = True
        if cert:
            tel["persone"][pid]["certificatore_disabilita"] = cert + pid[-2:]
    if dich:
        tel["dichiarazione"].update(dich)
    if modif:
        modif(d)
    return d


def esporta(d, completo=True):
    es = esporta_xml(d, contesto_caso_a10())
    if completo:
        assert es.completo, [e.messaggio for e in es.errori] + es.non_supportato + [m.messaggio for m in es.quadri_mancanti]
    return es


def v(es, xp):
    doc = etree.fromstring(es.xml)
    return doc.xpath(xp, namespaces={k: x for k, x in doc.nsmap.items() if k})


def errori(es):
    return {(e.codice, e.percorso) for e in es.errori}


def controllo_positivo(es, tmp_path):
    stato, dgn, wri, _ = _esegui(es.xml, tmp_path)
    assert stato == "positivo", (dgn["diagnostici"], wri[:900])
    assert [x["codice"] for x in dgn["diagnostici"]] == ["3345"]       # solo l'avviso sull'attestazione


def documento(d, did, tipo, allegato="al_albero"):
    d["documenti_ref"].append({"id": did, "_origine": {}, "allegato_id": allegato, "tipo_eg": tipo, "finalita": "documento (sintetico)"})


# ------------------------------------------------------------------------------------------------ separazione (lettera g)
def test_separato_senza_colpa_con_coniuge():
    es = esporta(caso("5", {"separazione_con_colpa": False}, coniuge=True))
    assert v(es, f"{SEZ}/suc:Separazione/suc:FlagAssenzaSeparazione/text()") == ["1"]
    assert v(es, f"{D}/suc:Frontespizio/suc:DatiDefunto/suc:UlterioriDati/suc:StatoCivile/text()") == ["5"]


def test_separato_con_colpa_il_coniuge_non_e_beneficiario():
    es = esporta(caso("5", {"separazione_con_colpa": True}))                      # due figli, nessun coniuge
    assert v(es, f"{SEZ}/suc:Separazione/suc:FlagSeparazione/text()") == ["1"]
    es = esporta(caso("5", {"separazione_con_colpa": True}, coniuge=True), completo=False)
    assert es.xml is None and ("REGOLA_SEPARAZIONE", "opzioni.telematico.dichiarazione.separazione_con_colpa") in errori(es)


def test_separazione_dati_mancanti_o_incoerenti():
    es = esporta(caso("5"), completo=False)
    assert ("DATO_MANCANTE", "opzioni.telematico.dichiarazione.separazione_con_colpa") in errori(es)
    es = esporta(caso("4", {"separazione_con_colpa": True}), completo=False)     # vedovo
    assert ("DATI_INCOERENTI", "opzioni.telematico.dichiarazione.separazione_con_colpa") in errori(es)


# ------------------------------------------------------------------------------------------- unione civile (lettera h)
def test_unione_civile_nessuno_scioglimento():
    es = esporta(caso("7", {"no_scioglimento_unione_civile": True}, coniuge=True))
    assert v(es, f"{SEZ}/suc:FlagNoScioglimentoUnioneCivile/text()") == ["1"]


def test_unione_civile_richiede_la_dichiarazione():
    es = esporta(caso("7", coniuge=True), completo=False)
    assert es.xml is None and ("DATO_MANCANTE", "opzioni.telematico.dichiarazione.no_scioglimento_unione_civile") in errori(es)
    es = esporta(caso("2", {"no_scioglimento_unione_civile": True}, coniuge=True), completo=False)
    assert ("DATI_INCOERENTI", "opzioni.telematico.dichiarazione.no_scioglimento_unione_civile") in errori(es)


# ------------------------------------------------------------------------------------- disabili e interdetti (lettera e)
def test_un_soggetto_con_disabilita():
    es = esporta(caso(disabili=("p_anna0001",), cert="VERBALE ASL RM1 N 1"))
    assert v(es, f"{SEZ}/suc:Interdetti/suc:PresenzaInterdetti/suc:FlagInterdetti/text()") == ["1"]
    assert v(es, f"{SEZ}/suc:Interdetti/suc:PresenzaInterdetti/suc:IdentificazioneSoggetto/*/text()") == ["1", "1"]
    assert v(es, f"{SEZ}/suc:Interdetti/suc:PresenzaInterdetti/suc:Certificatore/text()") == ["VERBALE ASL RM1 N 101"]


def test_due_soggetti_con_disabilita_il_secondo_nel_modulo_successivo():
    es = esporta(caso(disabili=("p_anna0001", "p_luca0001"), cert="VERBALE ASL RM1 N 1"))
    assert v(es, f"{SEZ}/suc:Interdetti/suc:PresenzaInterdetti/suc:Certificatore/text()") == ["VERBALE ASL RM1 N 101"]
    assert v(es, f"{MOD}/suc:PresenzaInterdetti/suc:Certificatore/text()") == ["VERBALE ASL RM1 N 101"]
    assert v(es, f"{MOD}/suc:PresenzaInterdetti/suc:IdentificazioneSoggetto/*/text()") == ["2", "1"]


def test_disabilita_senza_certificatore_o_troppo_lungo():
    es = esporta(caso(disabili=("p_anna0001",)), completo=False)
    assert es.xml is None and ("DATO_MANCANTE", "persone[p_anna0001].certificatore_disabilita") in errori(es)
    es = esporta(caso(disabili=("p_anna0001",), cert="X" * 40), completo=False)
    assert es.xml is None and ("VALORE_NON_VALIDO", "persone[p_anna0001].certificatore_disabilita") in errori(es)


# -------------------------------------------------------------------------- reintegro dei diritti di legittima (lettera d)
def test_un_accordo_di_reintegro():
    es = esporta(caso(dich={"reintegro_1": REG1}))
    assert v(es, f"{SEZ}/suc:ReintegroDiritti/suc:FlagReintegro/text()") == ["1"]
    assert v(es, f"{SEZ}/suc:ReintegroDiritti/suc:RegistrazioneReintegroDiritti/*/text()")[:3] == ["795", "1T", "321"]


def test_tre_accordi_di_reintegro_i_successivi_nei_moduli():
    es = esporta(caso(dich={"reintegro_1": REG1, "reintegro_2": REG2, "reintegro_3": REG3}))
    assert len(v(es, f"{MOD}/suc:ReintegroDiritti")) == 2


def test_reintegro_dati_non_validi():
    es = esporta(caso(dich={"reintegro_1": REG1, "reintegro_2": dict(REG1)}), completo=False)      # duplicato
    assert es.xml is None and ("DATI_INCOERENTI", "opzioni.telematico.dichiarazione.reintegro_2") in errori(es)
    parziale = {k: v_ for k, v_ in REG1.items() if k != "serie"}
    es = esporta(caso(dich={"reintegro_1": parziale}), completo=False)
    assert es.xml is None and ("DATO_MANCANTE", "opzioni.telematico.dichiarazione.reintegro_1.serie") in errori(es)


# ------------------------------------------------------------------------------------------- EG3 inventario / prospetto
def test_inventario_con_attestazione_copie_conformi():
    es = esporta(caso(modif=lambda d: documento(d, "dr_invent1", "Inventario", "al_passiv"),
                      dich={"dichiara_copie_conformi": True}))
    assert v(es, f"{D}/suc:QuadroEG/suc:Inventario/suc:InventarioNum/text()") == ["1"]
    assert v(es, f"{SEZ}/suc:FlagProspetto/text()") == ["1"]


def test_inventario_senza_attestazione_e_respinto():
    es = esporta(caso(modif=lambda d: (documento(d, "dr_invent1", "Inventario", "al_passiv"),
                                       d["opzioni"]["telematico"]["dichiarazione"].pop("dichiara_copie_conformi", None))),
                 completo=False)
    assert es.xml is None and ("DATO_MANCANTE", "opzioni.telematico.dichiarazione.dichiara_copie_conformi") in errori(es)


# -------------------------------------------------------------------------- EG10 richiesta agevolazioni di un altro beneficiario
def _c_per_luca(d):
    d["opzioni"]["telematico"].setdefault("devoluzioni", {}).setdefault("d_terrluca", {})["agevolazioni"] = "C"
    documento(d, "dr_agev10", "AgevolazioniImposteIpocatastali")
    documento(d, "dr_ident7", "DocumentiIdentita", "al_testam")


def test_eg10_per_agevolazione_c_di_un_altro_beneficiario():
    es = esporta(caso(modif=_c_per_luca))
    assert v(es, f"{D}/suc:QuadroEG/suc:AgevolazioniImposteIpocatastali/suc:AgevolazioniImposteIpocatastaliNum/text()") == ["1"]


# ----------------------------------------------------------------------------------------- controllo ufficiale locale
@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
@pytest.mark.parametrize("nome,costruisci", [
    ("separato_senza_colpa", lambda: caso("5", {"separazione_con_colpa": False}, coniuge=True)),
    ("separato_con_colpa_senza_coniuge", lambda: caso("5", {"separazione_con_colpa": True})),
    ("unione_civile", lambda: caso("7", {"no_scioglimento_unione_civile": True}, coniuge=True)),
    ("un_disabile", lambda: caso(disabili=("p_anna0001",), cert="VERBALE ASL RM1 N 1")),
    ("due_disabili", lambda: caso(disabili=("p_anna0001", "p_luca0001"), cert="VERBALE ASL RM1 N 1")),
    ("reintegro", lambda: caso(dich={"reintegro_1": REG1})),
    ("tre_reintegri", lambda: caso(dich={"reintegro_1": REG1, "reintegro_2": REG2, "reintegro_3": REG3})),
    ("inventario", lambda: caso(modif=lambda d: documento(d, "dr_invent1", "Inventario", "al_passiv"),
                                dich={"dichiara_copie_conformi": True})),
    ("eg10_agevolazione_c", lambda: caso(modif=_c_per_luca)),
])
def test_controllo_ufficiale_locale(tmp_path, nome, costruisci):
    controllo_positivo(esporta(costruisci()), tmp_path)


def _negativo(tmp_path, es, cerca, sostituisci, codice, flags=0):
    import re
    xml = re.sub(cerca, sostituisci, es.xml, count=1, flags=flags)
    assert xml != es.xml
    stato, dgn, _, _ = _esegui(xml, tmp_path)
    assert stato == "negativo" and codice in {x["codice"] for x in dgn["diagnostici"]}, dgn["diagnostici"]


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
def test_negativi_del_controllo_ufficiale(tmp_path):
    """Alterazioni dell'XML corretto respinte dal controllo: FlagSeparazione con stato civile 4 (3130), FlagNoScioglimentoUnioneCivile con
    stato civile 2 (3271), «assenza di interdetti» con una persona con disabilita' nel quadro EA (2097)."""
    _negativo(tmp_path / "a", esporta(caso("5", {"separazione_con_colpa": True})),
              rb"(<(?:\w+:)?StatoCivile>)5(</)", rb"\g<1>4\2", "3130")
    _negativo(tmp_path / "b", esporta(caso("7", {"no_scioglimento_unione_civile": True}, coniuge=True)),
              rb"(<(?:\w+:)?StatoCivile>)7(</)", rb"\g<1>2\2", "3271")
    _negativo(tmp_path / "c", esporta(caso(disabili=("p_anna0001",), cert="VERBALE ASL RM1 N 1")),
              rb"<suc:PresenzaInterdetti>.*?</suc:PresenzaInterdetti>", b"<suc:FlagAssenzaInterdetti>1</suc:FlagAssenzaInterdetti>", "2097",
              flags=16)
