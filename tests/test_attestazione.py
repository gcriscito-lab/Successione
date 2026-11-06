"""Richiesta dell'attestazione di avvenuta presentazione (copia conforme) in dichiarazione: dati SINTETICI.

Fonti: Fascicolo I pp. PDF 16 (casella del frontespizio), 45-46 (rigo EF16 col. 1 = 32 euro, col. 3 = 85 x circoscrizioni + col. 1;
rigo EF18 = 16 euro); annotazioni XSD di CasiParticolari, ImpostaBollo_CopiaConforme, SezioneV_TributiSpeciali/CopiaConforme.
Motivo: 9 dichiarazioni reali su 10 dell'archivio del compilatore ufficiale dello studio la chiedono (prova del 2026-11-06).
"""
import copy
from datetime import date

import pytest
from lxml import etree

import telematico_casi as T
from successioni.telematico.esporta import esporta_xml
from successioni.telematico.importa import importa_xml
from test_confronto_compilatore_ufficiale import caso_fratelli_300k
from test_telematico_controllo import NS, _esegui, _motivo_salto

D = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione"
EF = D + "/suc:QuadroEF"
SALTO = _motivo_salto()


def _esporta(attestazione=True, caso=None):
    c = copy.deepcopy(caso or caso_fratelli_300k())
    if attestazione:
        c["opzioni"]["telematico"]["dichiarazione"]["richiesta_attestazione"] = True
    es = esporta_xml(c, T.contesto_caso_a10(data_riferimento=date(2026, 1, 15)))
    assert es.completo, ([e.messaggio for e in es.errori], es.non_supportato, [m.messaggio for m in es.quadri_mancanti])
    return es


def _v(es, xp):
    return [e.text for e in etree.fromstring(es.xml).xpath(xp, namespaces=NS)]


def test_righi_ef16_ef18_e_totale():
    senza, con = _esporta(False), _esporta(True)
    assert _v(con, D + "/suc:Frontespizio/suc:CasiParticolari/suc:CopiaConforme") == ["1"]
    assert _v(con, D + "/suc:Frontespizio/suc:CasiParticolari/suc:FirmaDichiarante") == ["1"]
    assert _v(con, EF + "/suc:SezioneIV_ImpostaBollo/suc:ImpostaBollo_CopiaConforme") == ["32"]
    assert _v(con, EF + "/suc:SezioneIV_ImpostaBollo/suc:Circoscrizioni_Imposta") == ["117"]       # 85 + 32
    assert _v(con, EF + "/suc:SezioneV_TributiSpeciali/suc:CopiaConforme/suc:CopiaConforme_Importo") == ["16,00"]
    assert _v(senza, EF + "/suc:TotaleDaVersare") == ["9205,00"] and _v(con, EF + "/suc:TotaleDaVersare") == ["9253,00"]
    assert _v(con, D + "/suc:Frontespizio/suc:ImportoDaVersare") == ["9253,00"]
    assert not _v(senza, D + "/suc:Frontespizio/suc:CasiParticolari/suc:CopiaConforme")
    assert not _v(senza, EF + "/suc:SezioneV_TributiSpeciali/suc:CopiaConforme/suc:CopiaConforme_Importo")


def test_importazione_conserva_la_richiesta():
    ops = importa_xml(_esporta(True).xml)
    testo = repr(ops)
    assert "'richiesta_attestazione': True" in testo


def test_integrativa_non_ammette_attestazione():
    c = caso_fratelli_300k()
    c["opzioni"]["telematico"]["dichiarazione"]["richiesta_attestazione"] = True
    c["opzioni"]["telematico"]["dichiarazione"]["codice_sostitutiva"] = "3"
    c["opzioni"]["tipo_dichiarazione"] = "sostitutiva"
    es = esporta_xml(c, T.contesto_caso_a10(data_riferimento=date(2026, 1, 15)))
    assert es.xml is None and any(e.codice == "REGOLA_ATTESTAZIONE" for e in es.errori)


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
def test_controllo_ufficiale_positivo_senza_avvisi(tmp_path):
    stato, dgn, wri, _ = _esegui(_esporta(True).xml, tmp_path)
    assert stato == "positivo", (dgn["diagnostici"], wri[:1200])
    assert dgn["diagnostici"] == [], dgn["diagnostici"]          # sparisce anche l'avviso 3345 (attestazione non richiesta)


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
def test_controllo_ufficiale_respinge_il_bollo_senza_32(tmp_path):
    xml = _esporta(True).xml.replace(b"<suc:Circoscrizioni_Imposta>117</suc:Circoscrizioni_Imposta>",
                                     b"<suc:Circoscrizioni_Imposta>85</suc:Circoscrizioni_Imposta>")
    assert b">85</suc:Circoscrizioni_Imposta>" in xml
    stato, dgn, _, _ = _esegui(xml, tmp_path)
    assert stato == "negativo", dgn["diagnostici"]
