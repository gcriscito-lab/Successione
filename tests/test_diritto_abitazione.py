"""Diritto di abitazione del coniuge superstite (art. 540 c.c., legato ex lege): casella DirittoAbitazione del quadro EC (codici
1-8), effetti su EF (prima casa estesa a tutti i beneficiari del bene) e sulla Sezione II del quadro EH, coniuge rinunciatario che
conserva il legato (codici 5-8), riga di devoluzione con il diritto di abitazione (codice diritto 3) e suo valore. Dati SINTETICI.

Fonti: Fascicolo I pp. PDF 17, 24-25, 30-32, 67; annotazioni XSD di QuadroEC/.../DirittoAbitazione, Quota, CodiceDiritto_Rip,
QuadroEF/PrimaCasa, QuadroEG/PrimaCasa, QuadroEH/SezioneII_AgevPrimaCasa. Scheda: docs/regole/diritto_abitazione.md.
Il controllo ufficiale SUC13 locale e' eseguito se configurato, altrimenti le prove sono saltate con il motivo."""
from __future__ import annotations

import copy
from datetime import date
from fractions import Fraction

import pytest
from lxml import etree

from successioni.servizio import Servizio, nuovi_dati
from successioni.telematico import diritto_abitazione as DA
from successioni.telematico import usufrutto as USU
from successioni.telematico.esporta import esporta_xml
from successioni.telematico.importa import importa_xml
from telematico_casi import ALLEGATI_A10, FIXTURE, PRIMA_CASA_DICH, caso_a10, caso_testamento, contesto
from test_soggetti_ea import caso_coniuge_rinunciatario
from test_telematico_controllo import NS, _esegui, _motivo_salto

SALTO = pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
D = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione"
EF1 = D + "/suc:QuadroEF/suc:SezioneI_ImpostaIpotecaria"
EH2 = D + "/suc:QuadroEH/suc:PrimoModulo/suc:SezioneII_AgevPrimaCasa"
ALLEGATI = {**ALLEGATI_A10,
            "al_prima": {"percorso": str(FIXTURE / "allegati" / "albero_genealogico.pdf"), "nome": "prima_casa.pdf"},
            "al_ident": {"percorso": str(FIXTURE / "allegati" / "albero_genealogico.pdf"), "nome": "identita.pdf"}}
CTX = contesto(allegati=ALLEGATI, data_riferimento=date(2025, 9, 1))


def _tel(d):
    return d["opzioni"]["telematico"]


def _casa(d):
    return next(b for b in d["beni"] if b["id"] == "b_casa0001")


def _x(es, xp):
    return etree.fromstring(es.xml).xpath(xp, namespaces=NS)


def _ok(es):
    assert es.completo and es.xml, ([e.codice + " " + e.percorso + " " + e.messaggio for e in es.errori], es.non_supportato,
                                    [m.messaggio for m in es.quadri_mancanti])
    return es


def _coniuge(d, pid="p_anna0001"):
    """Il soggetto ``pid`` diventa il coniuge (grado 01); stato civile 2 (coniugato in comunione). Con un figlio, per legge, la
    quota e' 1/2 ciascuno (Allegato 5), gia' quella dei casi base."""
    _tel(d)["dichiarazione"]["stato_civile"] = "2"
    next(p for p in d["persone"] if p["id"] == pid)["relazione_con_defunto"] = "01"
    _tel(d)["persone"][pid]["grado_parentela"] = "01"
    return d


def _documenti_prima_casa(d):
    d["documenti_ref"] += [
        {"id": "dr_prima01", "_origine": {}, "allegato_id": "al_prima", "tipo_eg": "PrimaCasa",
         "finalita": "Richiesta prima casa (sintetica)"},
        {"id": "dr_ident01", "_origine": {}, "allegato_id": "al_ident", "tipo_eg": "DocumentiIdentita",
         "finalita": "Documento d'identita' (sintetico)"}]


def caso_da(codice="1", dichiarante_coniuge=True):
    """Casa A/2 (126.000, 1/2 ciascuno) con la casella del diritto di abitazione; terreno a 30.000 perche' l'imposta proporzionale
    non sia inferiore alla fissa. Coniuge = Anna (dichiarante) oppure Luca (non dichiarante: richiesta EG9 + documento)."""
    d = _coniuge(caso_a10(), "p_anna0001" if dichiarante_coniuge else "p_luca0001")
    next(b for b in d["beni"] if b["id"] == "b_terr0001")["valore"] = "30000"
    _casa(d)["diritto_abitazione"] = codice
    if codice in DA.PRIMA_CASA:
        if dichiarante_coniuge:
            _tel(d)["dichiarazione"]["prima_casa"] = dict(PRIMA_CASA_DICH)
        else:
            _documenti_prima_casa(d)
    return d


def caso_rinunciatario(codice="8"):
    d = caso_coniuge_rinunciatario()
    next(b for b in d["beni"] if b["id"] == "b_terr0001")["valore"] = "30000"
    _casa(d)["diritto_abitazione"] = codice
    if codice in DA.PRIMA_CASA:
        _documenti_prima_casa(d)
    return d


def caso_riga_abitazione():
    """Testamento: casa in proprieta' 1/2 ad Anna e 1/2 a Luca, gravata dal diritto di abitazione (codice 3, 1/1) di Anna,
    coniuge nata il 1970-01-01 (55 anni al decesso 2025-03-10: coefficiente 26)."""
    d = _coniuge(caso_testamento())
    d["devoluzioni"].append({"id": "d_casaabit", "_origine": {}, "bene_id": "b_casa0001", "persona_id": "p_anna0001",
                             "quota": {"num": 1, "den": 1}, "diritto": "3"})
    return d


# ------------------------------------------------------------------------------------------------ casella: andata
def test_codice_1_coniuge_dichiarante_prima_casa_estesa():
    es = _ok(esporta_xml(caso_da("1"), CTX))
    assert _x(es, D + "/suc:QuadroEC//suc:Fabbricati/suc:DirittoAbitazione/text()") == ["1"]
    # righe invariate: proprieta' 1/2 + 1/2, valore quota = valore x quota (annotazione di Quota), nessuna agevolazione di riga
    qv = sorted(_x(es, D + "/suc:QuadroEC//suc:Fabbricati[suc:DirittoAbitazione]//suc:QuotaValore/text()"))
    assert qv == ["63000,00", "63000,00"]
    assert not _x(es, D + "/suc:QuadroEC//suc:Fabbricati[suc:DirittoAbitazione]//suc:Agevolazioni")
    # EF4: un immobile, valore dell'intero bene (estesa anche alla quota del figlio); EF1 solo il terreno
    assert _x(es, EF1 + "/suc:PrimaCasa/suc:PrimaCasa_Numero/text()") == ["1"]
    assert _x(es, EF1 + "/suc:PrimaCasa/suc:AgevolazionePX_Valore/text()") == ["126000"]
    assert _x(es, EF1 + "/suc:ImpostaProporzionale/suc:ImpostaProporzionale_Imponibile/text()") == ["30000"]
    # EH Sezione II del coniuge dichiarante, nessuna richiesta EG9
    assert _x(es, EH2 + "/suc:ImmobilePrincipale")
    assert not [m for m in es.quadri_mancanti if "PrimaCasa" in m.percorso]


def test_codice_4_senza_prima_casa():
    es = _ok(esporta_xml(caso_da("4"), CTX))
    assert _x(es, D + "/suc:QuadroEC//suc:DirittoAbitazione/text()") == ["4"]
    assert not _x(es, EF1 + "/suc:PrimaCasa") and not _x(es, EH2)
    assert _x(es, EF1 + "/suc:ImpostaProporzionale/suc:ImpostaProporzionale_Imponibile/text()") == ["156000"]


def test_coniuge_non_dichiarante_richiede_eg9():
    d = caso_da("1", dichiarante_coniuge=False)
    d["documenti_ref"] = [r for r in d["documenti_ref"] if r["tipo_eg"] not in ("PrimaCasa", "DocumentiIdentita")]
    es = esporta_xml(d, CTX)
    assert any(m.percorso == "quadro[EG].PrimaCasa" for m in es.quadri_mancanti), [m.percorso for m in es.quadri_mancanti]
    es = _ok(esporta_xml(caso_da("1", dichiarante_coniuge=False), CTX))
    assert not _x(es, EH2) and _x(es, EF1 + "/suc:PrimaCasa/suc:PrimaCasa_Numero/text()") == ["1"]


def test_coniuge_rinunciatario_conserva_il_legato():
    es = _ok(esporta_xml(caso_rinunciatario("8"), CTX))
    assert _x(es, D + "/suc:QuadroEC//suc:DirittoAbitazione/text()") == ["8"]
    es5 = _ok(esporta_xml(caso_rinunciatario("5"), CTX))
    assert _x(es5, EF1 + "/suc:PrimaCasa/suc:AgevolazionePX_Valore/text()") == ["126000"]


@pytest.mark.parametrize("modifica,atteso", [
    (lambda d: _casa(d).update(diritto_abitazione="1"), "grado di parentela 01"),            # nessun coniuge in EA
])
def test_senza_coniuge_errore(modifica, atteso):
    d = caso_a10()
    modifica(d)
    es = esporta_xml(d, CTX)
    assert any(e.codice == "REGOLA_DIRITTO_ABITAZIONE" and atteso in e.messaggio for e in es.errori)


def test_codici_5_8_solo_con_coniuge_rinunciatario_e_viceversa():
    es = esporta_xml(caso_da("8"), CTX)
    assert any(e.codice == "REGOLA_DIRITTO_ABITAZIONE" and "5-8" in e.messaggio for e in es.errori)
    es = esporta_xml(caso_rinunciatario("4"), CTX)
    assert any(e.codice == "REGOLA_DIRITTO_ABITAZIONE" and "rinunciatario" in e.messaggio for e in es.errori)


def test_agevolazione_di_riga_incoerente_e_categoria():
    d = caso_da("1")
    _tel(d)["devoluzioni"] = {"d_casaluca": {"agevolazioni": "A"}}
    assert any(e.codice == "REGOLA_DIRITTO_ABITAZIONE" and "agevolazione P" in e.messaggio
               for e in esporta_xml(d, CTX).errori)
    d = caso_da("3")
    es = esporta_xml(d, CTX)
    assert any(e.codice == "REGOLA_DIRITTO_ABITAZIONE" and "C/2, C/6 o C/7" in e.messaggio for e in es.errori)


def test_valore_non_ammesso():
    es = esporta_xml(caso_da("9"), CTX)
    assert any(e.codice == "VALORE_NON_VALIDO" and e.percorso.endswith("diritto_abitazione") for e in es.errori)


def test_andata_e_ritorno_importazione():
    d = caso_da("1")
    es = _ok(esporta_xml(d, CTX))
    r = importa_xml(es.xml, data_riferimento=CTX.data_riferimento)
    assert not [a for a in r["avvisi"] if "diverso" in a or "abitazione" in a], r["avvisi"]
    dati = nuovi_dati()
    for i, op in enumerate(r["operazioni"]):
        Servizio._applica(dati, op, "inserito", "gui", i)
    dati["documenti_ref"] = copy.deepcopy(d["documenti_ref"])
    dati["opzioni"]["telematico"]["dichiarazione"]["dichiara_copie_conformi"] = True
    es2 = _ok(esporta_xml(dati, CTX))
    assert _x(es2, D + "/suc:QuadroEC//suc:DirittoAbitazione/text()") == ["1"]
    assert _x(es2, D + "/suc:Frontespizio/suc:ImportoDaVersare/text()") == _x(es, D + "/suc:Frontespizio/suc:ImportoDaVersare/text()")


# ------------------------------------------------------------------------------------------------ riga con il diritto 3
def test_valori_abitazione_come_usufrutto():
    righe = [{"id": "a", "diritto": "3", "quota": Fraction(1), "coefficiente": 26},
             {"id": "p1", "diritto": "1", "quota": Fraction(1, 2), "coefficiente": None},
             {"id": "p2", "diritto": "1", "quota": Fraction(1, 2), "coefficiente": None}]
    r = DA.valori(126000, righe)
    assert r["valori"] == {"a": 81900, "p1": 22050, "p2": 22050}
    assert DA.valori(1000, righe[:2])["errori"]       # proprieta' gravata 1/2: le quote non coprono il bene


def test_riga_abitazione_valore_quota():
    es = _ok(esporta_xml(caso_riga_abitazione(), CTX))
    v = {}
    for dv in _x(es, D + "/suc:QuadroEC//suc:Devoluzione"):
        v.setdefault(dv.findtext("suc:CodiceDiritto_Rip", namespaces=NS), []).append(
            dv.findtext("suc:Quota/suc:QuotaValore", namespaces=NS))
    abit = Fraction(126000) * USU.SAGGIO * USU.coefficiente(55)
    assert v["3"] == ["81900,00"] and abit == 81900
    assert sorted(v["1"]) == ["22050,00", "22050,00"]


def test_riga_abitazione_per_legge_respinta():
    d = _coniuge(caso_a10())
    d["devoluzioni"].append({"id": "d_casaabit", "_origine": {}, "bene_id": "b_casa0001", "persona_id": "p_anna0001",
                             "quota": {"num": 1, "den": 1}, "diritto": "3"})
    es = esporta_xml(d, CTX)
    assert any(e.codice == "REGOLA_CODICE_DIRITTO" for e in es.errori)


# ------------------------------------------------------------------------------------------------ controllo ufficiale locale
@SALTO
@pytest.mark.parametrize("costruisci", [lambda: caso_da("1"), lambda: caso_da("4"), lambda: caso_da("1", False),
                                        lambda: caso_rinunciatario("8"), lambda: caso_rinunciatario("5"), caso_riga_abitazione],
                         ids=["codice1", "codice4", "codice1_non_dichiarante", "rinunciatario8", "rinunciatario5",
                              "riga_abitazione"])
def test_controllo_ufficiale_positivo(costruisci, tmp_path):
    stato, dgn, wri, _ = _esegui(esporta_xml(costruisci(), CTX).xml, tmp_path)
    assert stato == "positivo", (dgn["diagnostici"], wri[:1500])


@SALTO
def test_controllo_ufficiale_respinge_prima_casa_alterata(tmp_path):
    """Senza l'estensione al figlio (valore dell'intero bene nel rigo EF4) il controllo respinge il file."""
    xml = esporta_xml(caso_da("1"), CTX).xml
    alterato = xml.replace(b"<suc:DirittoAbitazione>1</suc:DirittoAbitazione>", b"<suc:DirittoAbitazione>4</suc:DirittoAbitazione>")
    assert alterato != xml
    stato, dgn, _, _ = _esegui(alterato, tmp_path)
    assert stato == "negativo", dgn["diagnostici"]


# ------------------------------------------------------------------------------------------------ imponibile EF1/EF9 non intero
def caso_tre_eredi_centesimi():
    """Testamento, casa da 126.001 a tre eredi per 1/3 (42.000,33 ciascuno: somma 126.000,99), come la dichiarazione reale DNZRME
    (immobile da 1.465 a tre eredi) che la riesportazione bloccava dopo il diritto di abitazione."""
    from test_soggetti_ea import aggiungi
    d = caso_testamento()
    aggiungi(d, "p_paolo001", "Paolo", "Rossi", "M", "1975-05-05", "02", "1", rinuncia=False)
    _casa(d)["valore"] = "126001"
    for dv in d["devoluzioni"]:
        if dv["bene_id"] == "b_casa0001":
            dv["quota"] = {"num": 1, "den": 3}
    d["devoluzioni"].append({"id": "d_casapaol", "_origine": {}, "bene_id": "b_casa0001", "persona_id": "p_paolo001",
                             "quota": {"num": 1, "den": 3}, "diritto": "1"})
    return d


def test_imponibile_non_intero_arrotondato_con_avviso():
    es = _ok(esporta_xml(caso_tre_eredi_centesimi(), CTX))
    assert any(a.codice == "ARROTONDAMENTO_IMPONIBILE_EF" for a in es.avvisi)
    assert _x(es, EF1 + "/suc:ImpostaProporzionale/suc:ImpostaProporzionale_Imponibile/text()") == ["141001"]


@SALTO
def test_imponibile_non_intero_controllo_ufficiale(tmp_path):
    """Riscontro sul componente: arrotondamento per eccesso (141.001) accettato, troncamento (141.000) respinto."""
    xml = esporta_xml(caso_tre_eredi_centesimi(), CTX).xml
    stato, dgn, wri, _ = _esegui(xml, tmp_path / "a")
    assert stato == "positivo", (dgn["diagnostici"], wri[:1500])
    troncato = xml.replace(b">141001<", b">141000<")
    assert troncato != xml
    stato, dgn, _, _ = _esegui(troncato, tmp_path / "b")
    assert stato == "negativo", dgn["diagnostici"]
