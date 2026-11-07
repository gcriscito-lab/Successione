"""Lacune emerse importando le dichiarazioni reali dello studio (2026-11-06), riprodotte su dati SINTETICI.

- Fabbricato senza indirizzo: il controllo ufficiale SUC13 2.3.1 da' esito positivo senza segnalazioni sul file reale; il programma
  lo bloccava (annotazione di Fabbricati/Luogo). Ora: avviso, non blocco.
- Importazione: email e decorrenza del presentatore, immobili graffati, identificativo del software produttore, casella
  dell'attestazione (test_attestazione.py).
"""
import copy
from datetime import date

import pytest

import telematico_casi as T
from successioni.telematico.esporta import esporta_xml
from successioni.telematico.importa import importa_xml
from test_telematico_controllo import _esegui, _motivo_salto

SALTO = _motivo_salto()
CTX = T.contesto_caso_a10(data_riferimento=date(2025, 9, 1))


def _senza_indirizzo():
    d = copy.deepcopy(T.caso_a10())
    d["opzioni"]["telematico"]["beni"]["b_casa0001"].pop("indirizzo", None)
    next(b for b in d["beni"] if b["id"] == "b_casa0001").pop("indirizzo", None)
    return d


def test_fabbricato_senza_indirizzo_avviso_non_blocco():
    es = esporta_xml(_senza_indirizzo(), CTX)
    assert es.completo, ([e.messaggio for e in es.errori], es.non_supportato)
    assert any(a.codice == "INDIRIZZO_FABBRICATO_ASSENTE" for a in es.avvisi)
    assert b"VIA ESEMPIO 1" not in es.xml


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
@pytest.mark.java
def test_fabbricato_senza_indirizzo_controllo_ufficiale(tmp_path):
    stato, dgn, wri, _ = _esegui(esporta_xml(_senza_indirizzo(), CTX).xml, tmp_path)
    assert stato == "positivo", (dgn["diagnostici"], wri[:1200])


def test_importazione_email_decorrenza_graffati():
    d = copy.deepcopy(T.caso_a10())
    pres = d["opzioni"]["telematico"]["dichiarazione"]["presentatore"]
    pres["email"] = "studio@example.org"
    pres["data_decorrenza"] = "2025-03-20"
    d["opzioni"]["telematico"]["beni"]["b_casa0001"]["graffati"] = [{"foglio": "100", "particella": "201", "subalterno": "1"}]
    es = esporta_xml(d, CTX)
    assert es.completo, ([e.messaggio for e in es.errori], es.non_supportato, [m.messaggio for m in es.quadri_mancanti])
    testo = repr(importa_xml(es.xml))
    assert "'email': 'studio@example.org'" in testo and "'data_decorrenza': '2025-03-20'" in testo
    assert "'graffati': [{'foglio': '100', 'particella': '201', 'subalterno': '1'}]" in testo
