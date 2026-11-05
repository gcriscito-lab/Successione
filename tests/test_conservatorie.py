"""Immobili in piu' comuni: righi EF15/EF16 dalle circoscrizioni di pubblicita' immobiliare (telematico/conservatorie.py).
Richiede la tabella del componente di controllo SUC13 configurato; senza, l'export multi-comune resta bloccato."""
import copy

import pytest
from lxml import etree

from telematico_casi import caso_a10, contesto_caso_a10
from successioni.telematico import conservatorie as CO
from successioni.telematico.esporta import esporta_xml
from test_telematico_controllo import _esegui, _motivo_salto

D = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione"
SALTO = CO.tabella() is None


def caso_comuni(casa, terreno):
    """caso_a10 con la casa e il terreno nei comuni indicati (codice catastale, provincia)."""
    d = copy.deepcopy(caso_a10())
    for bid, (cod, prov) in (("b_casa0001", casa), ("b_terr0001", terreno)):
        b = d["opzioni"]["telematico"]["beni"][bid]
        b.update(codice_comune=cod, codice_comune_amministrativo=cod, provincia=prov)
        next(x for x in d["beni"] if x["id"] == bid)["comune"] = cod
    return d


def valori(es, xp):
    doc = etree.fromstring(es.xml)
    ns = {k: v for k, v in doc.nsmap.items() if k}
    return doc.xpath(f"{D}/suc:QuadroEF/{xp}/text()", namespaces=ns)


def test_senza_componente_piu_comuni_restano_bloccati(monkeypatch):
    monkeypatch.delenv("SUCCESSIONI_CONTROLLI_SUC13", raising=False)
    es = esporta_xml(caso_comuni(("H501", "RM"), ("F205", "MI")), contesto_caso_a10())
    assert es.xml is None and any("elenco delle conservatorie non disponibile" in m.messaggio for m in es.quadri_mancanti)


@pytest.mark.skipif(SALTO, reason="componente di controllo SUC13 non configurato")
def test_comuni_diversi_stessa_circoscrizione_contano_una():
    assert CO.circoscrizioni(["A024", "B963"])[0] == {"CE00"}        # Acerra (NA) e Caserta: stessa conservatoria
    es = esporta_xml(caso_comuni(("A024", "NA"), ("B963", "CE")), contesto_caso_a10())
    assert es.completo, [e.messaggio for e in es.errori] + es.non_supportato
    assert valori(es, "suc:SezioneIII_TassaIpotecaria/*") == ["1", "120"]
    assert valori(es, "suc:SezioneIV_ImpostaBollo/*") == ["1", "85"]


@pytest.mark.skipif(SALTO, reason="componente di controllo SUC13 non configurato")
def test_due_circoscrizioni_raddoppiano_tassa_e_bollo():
    es = esporta_xml(caso_comuni(("H501", "RM"), ("F205", "MI")), contesto_caso_a10())
    assert es.completo, [e.messaggio for e in es.errori] + es.non_supportato
    assert valori(es, "suc:SezioneIII_TassaIpotecaria/*") == ["2", "240"]
    assert valori(es, "suc:SezioneIV_ImpostaBollo/*") == ["2", "170"]
    assert valori(es, "suc:TotaleDaVersare") == ["4435,00".replace("4435", "4435") if False else valori(es, "suc:TotaleDaVersare")[0]]
    # totale = 4435 (un comune) + 120 + 85 per la circoscrizione in piu'
    assert valori(es, "suc:TotaleDaVersare") == ["4640,00"]


@pytest.mark.skipif(SALTO, reason="componente di controllo SUC13 non configurato")
def test_comune_sconosciuto_non_determinabile():
    es = esporta_xml(caso_comuni(("H501", "RM"), ("Z999", "MI")), contesto_caso_a10())
    assert es.xml is None and any("assenti dall'elenco" in m.messaggio for m in es.quadri_mancanti)


@pytest.mark.skipif(_motivo_salto() is not None or SALTO, reason=_motivo_salto() or "tabella conservatorie assente")
@pytest.mark.parametrize("casa,terreno", [(("A024", "NA"), ("B963", "CE")), (("H501", "RM"), ("F205", "MI"))])
def test_controllo_ufficiale_accetta_e_respinge(tmp_path, casa, terreno):
    es = esporta_xml(caso_comuni(casa, terreno), contesto_caso_a10())
    assert es.completo
    stato, dgn, wri, _ = _esegui(es.xml, tmp_path / "ok")
    assert stato == "positivo", (dgn["diagnostici"], wri[:800])
    # numero di circoscrizioni alterato (stesso totale): il controllo, che usa la sua tabella, deve respingerlo
    giusto = valori(es, "suc:SezioneIII_TassaIpotecaria/*")[0]
    sbagliato = "2" if giusto == "1" else "1"
    xml = es.xml.replace(f"<Circoscrizioni_Numero>{giusto}</Circoscrizioni_Numero>".encode(),
                         f"<Circoscrizioni_Numero>{sbagliato}</Circoscrizioni_Numero>".encode(), 1)
    if xml == es.xml:   # prefisso di namespace nei tag
        import re
        xml = re.sub(rb"(<(?:\w+:)?Circoscrizioni_Numero>)" + giusto.encode() + rb"(</)", rb"\g<1>" + sbagliato.encode() + rb"\2", es.xml, count=1)
    assert xml != es.xml
    stato2, dgn2, _, _ = _esegui(xml, tmp_path / "ko")
    assert stato2 == "negativo", dgn2["diagnostici"]


@pytest.mark.skipif(SALTO, reason="componente di controllo SUC13 non configurato")
def test_sostitutiva_codice1_circoscrizioni_nuove():
    d = caso_comuni(("H501", "RM"), ("F205", "MI"))
    d["opzioni"]["tipo_dichiarazione"] = "sostitutiva"
    d["opzioni"]["telematico"]["dichiarazione"].update(
        codice_sostitutiva="1", prima_anno="2026", prima_volume="88888", prima_numero="1", circoscrizioni_nuove="1")
    es = esporta_xml(d, contesto_caso_a10())
    assert es.completo, [e.messaggio for e in es.errori] + es.non_supportato
    assert valori(es, "suc:SezioneIII_TassaIpotecaria/*") == ["1", "120"]
    d["opzioni"]["telematico"]["dichiarazione"]["codice_sostitutiva"] = "2"          # il campo non e' ammesso col codice 2
    es = esporta_xml(d, contesto_caso_a10())
    assert es.xml is None and any(e.percorso.endswith("circoscrizioni_nuove") for e in es.errori)
