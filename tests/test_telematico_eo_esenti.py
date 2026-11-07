"""Titoli esenti (quadro EO, TipoTitolo 3 / ValoreEsente): XML, totali di EE, base imponibile e controllo SUC13 locale.

Fonti (citate anche nel codice): XSD fornituraSUC13_v1.xsd, annotazioni di PossessoEO_Type/Valore e /ValoreEsente,
QuadroEE/TotaleValoreTitoli («somma del valore e del valore esente»), QuadroEE/TotaleAttivo («somma da EE1 a EE5»),
DevoluzioneSingolaNonImmobili_Type/Quota («per il quadro EO la somma dei campi Valore e Valore esente»);
Fascicolo I p. PDF 3 (titoli esenti), p. PDF 39 (EE). Dati sintetici.
"""
from datetime import date

import pytest
from lxml import etree

from successioni.telematico import xsd
from successioni.telematico.calcolo import calcola_da_xml
from successioni.telematico.esporta import esporta_xml

from telematico_casi import _titolo, caso_a10, caso_titoli, contesto_caso_a10
from test_telematico_controllo import NS, _esegui, _motivo_salto

D = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione"
CTX = contesto_caso_a10(data_riferimento=date(2025, 9, 1))
P = "beni[b_bot00001]."
Q = D + "/suc:QuadroEO/suc:Modulo/suc:Titoli"


def caso_esente(valore="8000", **extra) -> dict:
    """``caso_titoli`` piu' un BOT (titolo esente, tipo 3) devoluto 1/2 ai due figli."""
    d = caso_titoli()
    d["beni"].append(_titolo("b_bot00001", "3", "BOT sintetico", valore, **extra))
    for pid in ("p_anna0001", "p_luca0001"):
        d["devoluzioni"].append({"id": f"d_bot{pid[2:6]}", "_origine": {}, "bene_id": "b_bot00001", "persona_id": pid,
                                 "quota": {"num": 1, "den": 2}, "diritto": "1"})
    return d


def _con(mod):
    d = caso_titoli()
    mod(next(b for b in d["beni"] if b["id"] == "b_azioni01"))
    return d


def _es(d=None):
    return esporta_xml(d or caso_esente(), CTX)


def _codici(es):
    return {(e.percorso, e.codice) for e in es.errori}


def _t(doc, xp):
    return doc.xpath(D + xp, namespaces=NS)


def test_xml_valore_esente_e_totali_ee():
    es = _es()
    assert es.errori == [] and es.non_supportato == [] and es.quadri_mancanti == [], (es.errori, es.non_supportato)
    assert xsd.valida_xsd(es.xml) == []
    doc = etree.fromstring(es.xml)
    assert _t(doc, "/suc:QuadroEO/suc:Modulo/suc:Titoli/suc:TipoTitolo/text()") == ["2", "3", "4"]
    # il BOT ha ValoreEsente e non Valore; gli altri titoli hanno Valore e non ValoreEsente
    assert _t(doc, "/suc:QuadroEO/suc:Modulo/suc:Titoli/suc:Possesso/suc:ValoreEsente/text()") == ["8000"]
    assert _t(doc, "/suc:QuadroEO/suc:Modulo/suc:Titoli/suc:Possesso/suc:Valore/text()") == ["10000", "6000"]
    assert _t(doc, "/suc:QuadroEO/suc:Modulo/suc:Titoli[suc:TipoTitolo='3']/suc:Possesso/suc:Valore") == []
    # EE3 = Valore + ValoreEsente (annotazione TotaleValoreTitoli)
    assert _t(doc, "/suc:QuadroEE/suc:TotaleValoreTitoli/text()") == ["24000"]
    imm = int(_t(doc, "/suc:QuadroEE/suc:TotaleValoreImmobili/text()")[0])
    altri = int((_t(doc, "/suc:QuadroEE/suc:TotaleValoreAltriBeni/text()") or ["0"])[0])
    assert int(_t(doc, "/suc:QuadroEE/suc:TotaleAttivo/text()")[0]) == imm + 24000 + altri
    passivo = int(_t(doc, "/suc:QuadroEE/suc:TotalePassivo/text()")[0])
    assert int(_t(doc, "/suc:QuadroEE/suc:TotaleValoreAsseEreditarioNetto/text()")[0]) == imm + 24000 + altri - passivo
    # Valore quota del BOT = (Valore esente) x quota (annotazione Quota): 8000 x 1/2
    assert _t(doc, "/suc:QuadroEO/suc:Modulo/suc:Titoli[suc:TipoTitolo='3']/suc:DevoluzioneEO/suc:Devoluzione/suc:Quota/"
                   "suc:QuotaValore/text()") == ["4000,00", "4000,00"]


def test_titolo_esente_non_entra_in_ipocatastali():
    """EF (ipotecaria/catastale) considera solo gli immobili: il BOT non cambia gli importi di EF."""
    con, senza = etree.fromstring(_es().xml), etree.fromstring(esporta_xml(caso_titoli(), CTX).xml)
    for xp in ("/suc:QuadroEF/suc:SezioneI_ImpostaIpotecaria", "/suc:QuadroEF/suc:SezioneII_ImpostaCatastale"):
        a = [etree.tostring(e) for e in _t(con, xp)]
        assert a and a == [etree.tostring(e) for e in _t(senza, xp)]


def _qe(d):
    es = esporta_xml(d, CTX)
    assert es.xml is not None, (es.errori, es.non_supportato)
    r = calcola_da_xml(es.xml)   # il calcolo legge il file dichiarato, come il componente ufficiale
    assert r.stato == "completato", r.motivi
    return r, [{p.sigla: p.valore for p in b.passaggi} for b in r.beneficiari]


def test_base_imponibile_non_comprende_il_titolo_esente():
    r0, v0 = _qe(caso_titoli())
    r1, v1 = _qe(caso_esente())
    r2, v2 = _qe(caso_esente(valore="3000000"))   # esente enorme: se entrasse in QE sfonderebbe la franchigia
    assert v1 == v0 == v2
    # per erede: immobili 7500 + 63000, titoli 5000 + 3000, conto 10000 (somme dei Valore quota): il BOT (4000) e' escluso
    assert all(v["QE"] == "88500" for v in v1), v1
    assert r1.imposta_ef18bis == r0.imposta_ef18bis == r2.imposta_ef18bis
    assert any("Titoli esenti" in n and "interpretazione da confermare" in n and "p. PDF 3" in n for n in r1.note)
    assert not any("Titoli esenti" in n for n in r0.note)


def test_continuazione_del_rigo_esente_resta_esente():
    """Piu' di tre devoluzioni sul BOT: il rigo di continuazione (senza TipoTitolo) eredita la natura esente."""
    from successioni.telematico.calcolo import _leggi
    xml = _es().xml
    doc = etree.fromstring(xml)
    riga = _t(doc, "/suc:QuadroEO/suc:Modulo/suc:Titoli[suc:TipoTitolo='3']")[0]
    # rigo di continuazione sintetico subito dopo il BOT: solo devoluzione, nessun TipoTitolo
    cont = etree.Element(riga.tag)
    riga.addnext(cont)
    cont.append(etree.fromstring(etree.tostring(riga.find("{*}DevoluzioneEO"))))
    dati, _ = _leggi(etree.tostring(doc))
    es = [t for t in dati["devoluzioni"] if t[1] == "EO" and t[2] == "ES"]
    assert len(es) == 4, dati["devoluzioni"]


def test_calcolo_riconosce_esente_da_tipo_o_da_valore_esente():
    """Il calcolo legge il file dichiarato: e' esente il rigo con TipoTitolo 3 oppure con Possesso/ValoreEsente."""
    from successioni.telematico.calcolo import _leggi

    def es_(doc):
        dati, _ = _leggi(etree.tostring(doc))
        return len([t for t in dati["devoluzioni"] if t[1] == "EO" and t[2] == "ES"])

    base = _es().xml
    assert es_(etree.fromstring(base)) == 2
    solo_tipo = etree.fromstring(base)   # TipoTitolo 3 senza ValoreEsente
    for e in solo_tipo.xpath(D + "/suc:QuadroEO//suc:ValoreEsente", namespaces=NS):
        e.getparent().remove(e)
    assert es_(solo_tipo) == 2
    solo_valore = etree.fromstring(base)   # ValoreEsente su un rigo di TipoTitolo 4
    for e in solo_valore.xpath(D + "/suc:QuadroEO//suc:Titoli[suc:TipoTitolo='3']/suc:TipoTitolo", namespaces=NS):
        e.text = "4"
    assert es_(solo_valore) == 2


def test_valore_mancante_o_zero_per_titolo_esente():
    d = caso_esente()
    next(b for b in d["beni"] if b["id"] == "b_bot00001")["valore"] = None
    assert (P + "valore", "DATO_MANCANTE") in _codici(_es(d)) or any(e.percorso == P + "valore" for e in _es(d).errori)
    es = _es(caso_esente(valore="0"))
    assert es.xml is None and any(e.percorso == P + "valore" for e in es.errori)
    # l'errore cita l'elemento giusto (ValoreEsente) per il tipo 3 e Valore per gli altri
    assert any("Possesso/ValoreEsente" in e.fonte for e in es.errori if e.percorso == P + "valore")
    altro = esporta_xml(_con(lambda b: b.update(valore="0")), CTX)
    assert any("Possesso/Valore" in e.fonte and "ValoreEsente" not in e.fonte for e in altro.errori)


def test_codice_titolo_non_ammesso_per_titolo_esente():
    assert (P + "codice_titolo", "DATI_INCOERENTI") in _codici(_es(caso_esente(codice_titolo="IT0000000019")))


def test_cf_emittente_titolo_esente_diverso_da_defunto():
    es = _es(caso_esente(codice_fiscale_emittente="RSSMRA40A01H501K"))
    assert (P + "codice_fiscale_emittente", "REGOLA_CF_EMITTENTE") in _codici(es)


def test_cf_emittente_facoltativo_per_titolo_esente():
    es = _es(caso_esente(codice_fiscale_emittente="00000000018"))
    assert es.errori == [] and es.xml is not None


def test_passivita_collegata_a_titolo_esente_non_supportata():
    d = caso_esente()
    d["passivita"].append({"id": "ps_botdebt", "_origine": {}, "descrizione": "Debito sul BOT", "importo": "500",
                           "persona_id": "p_anna0001", "bene_id": "b_bot00001"})
    d["opzioni"]["telematico"]["passivita"]["ps_botdebt"] = {"tipo": "4", "estremi_documento": "Atto sintetico",
                                                             "data_documento": "2024-12-01", "possesso": "1/1"}
    es = _es(d)
    assert es.xml is None and any("titolo esente" in s and "b_bot00001" in s for s in es.non_supportato), \
        (es.errori, es.non_supportato)


def test_senza_devoluzione_il_titolo_esente_e_un_errore():
    d = caso_esente()
    d["devoluzioni"] = [x for x in d["devoluzioni"] if x["bene_id"] != "b_bot00001"]
    assert any(e.codice == "DEVOLUZIONE_MANCANTE" for e in _es(d).errori)


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
@pytest.mark.java
def test_reale_controllo_ufficiale_positivo_con_titolo_esente(tmp_path):
    stato, dgn, wri, dcm = _esegui(_es().xml, tmp_path)
    assert stato == "positivo", (stato, dgn["diagnostici"])
    assert sorted((x["codice"], x["gravita"]) for x in dgn["diagnostici"]) == [("3345", 4)], dgn["diagnostici"]


def _muta(fn):
    doc = etree.fromstring(_es().xml)
    fn(doc)
    return etree.tostring(doc, xml_declaration=True, encoding="UTF-8")


def _ee3_senza_esente(doc):
    doc.xpath(D + "/suc:QuadroEE/suc:TotaleValoreTitoli", namespaces=NS)[0].text = "16000"


def _valore_al_posto_di_esente(doc):
    e = doc.xpath(D + "/suc:QuadroEO/suc:Modulo/suc:Titoli/suc:Possesso/suc:ValoreEsente", namespaces=NS)[0]
    e.tag = e.tag.replace("ValoreEsente", "Valore")


def _entrambi(doc):
    e = doc.xpath(D + "/suc:QuadroEO/suc:Modulo/suc:Titoli[suc:TipoTitolo='3']/suc:Possesso/suc:ValoreEsente",
                  namespaces=NS)[0]
    v = etree.Element(e.tag.replace("ValoreEsente", "Valore"))
    v.text = "100"
    e.addprevious(v)


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
@pytest.mark.parametrize("mut", [_ee3_senza_esente, _valore_al_posto_di_esente, _entrambi])
@pytest.mark.java
def test_reale_controllo_ufficiale_negativi(mut, tmp_path):
    stato, dgn, wri, dcm = _esegui(_muta(mut), tmp_path)
    assert stato != "positivo", (mut.__name__, dgn["diagnostici"])
    assert any(x["gravita"] >= 6 or x["codice"] != "3345" for x in dgn["diagnostici"]), dgn["diagnostici"]
