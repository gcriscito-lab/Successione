"""Esportazione XML SUC13 sul perimetro dichiarato (casi sintetici).

Esito: simulazione/controllo locale. Uno schema valido non prova la compatibilita' con il controllo ufficiale.
"""
from __future__ import annotations

import random

from lxml import etree

from successioni.schema import Errore
from successioni.telematico import fonti, xsd
from successioni.telematico.esporta import _riferisci, esporta_xml

from successioni.telematico.identificativi import genera_cf_sintetico

from telematico_casi import CF_ANNA, caso_completo, contesto, copia

NS = {"tm": fonti.NS_TM, "suc": fonti.NS_SUC, "reg": fonti.NS_REG}


def _bozza(dati):
    return esporta_xml(dati, contesto(scopo="bozza_tecnica"))


def test_caso_sintetico_completo_valido_ma_dichiaratamente_incompleto():
    es = _bozza(caso_completo())
    assert es.errori == [] and es.non_supportato == []
    assert es.xml is not None and xsd.valida_xsd(es.xml) == []
    # EF ed EH generati; EG senza allegati: albero genealogico (EA) e documenti delle passivita' (ED) mancanti
    assert sorted(e.percorso for e in es.quadri_mancanti) == ["quadro[EG].AlberoGenealogico",
                                                              "quadro[EG].DocumentiPassivita"]
    assert all("annotazione dell'elemento QuadroEG" in e.fonte for e in es.quadri_mancanti)
    assert es.completo is False
    # in modalita' 'completo' (predefinita) nessun XML parziale presentato come completo
    es2 = esporta_xml(caso_completo(), contesto())
    assert es2.xml is None and es2.completo is False and len(es2.quadri_mancanti) == 2
    assert es2.impronta_xml == es.impronta_xml  # lo stesso file e' stato prodotto e validato, ma non consegnato


def test_contenuto_e_totali_ee():
    es = _bozza(caso_completo())
    doc = etree.fromstring(es.xml)
    d = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione"
    assert doc.xpath("/tm:Messaggio/tm:Contenuto/@CodiceFornitura", namespaces=NS) == ["SUC13"]
    assert doc.xpath(f"{d}/suc:Frontespizio/suc:Beneficiari/suc:NumeroEredi/text()", namespaces=NS) == ["2"]
    ee = {e.tag.split("}")[1]: e.text for e in doc.xpath(f"{d}/suc:QuadroEE/*", namespaces=NS)}
    assert ee == {"TotaleValoreImmobili": "141000", "TotaleValoreAltriBeni": "20000", "TotaleAttivo": "161000",
                  "TotalePassivo": "32000", "TotaleValoreAsseEreditarioNetto": "129000"}
    # valore quota = valore x quota (Fascicolo I p. PDF 24)
    qv = doc.xpath(f"{d}/suc:QuadroER//suc:QuotaValore/text()", namespaces=NS)
    assert qv == ["10000,00", "10000,00"]
    # progressivo cespite del mutuo verso il fabbricato (quadro/rigo/modulo dalla mappa)
    prog = doc.xpath(f"{d}/suc:QuadroED//suc:ProgressivoCespite/*/text()", namespaces=NS)
    assert prog == ["EC", "1", "1"]
    # campi interni non esportati: visibili come avvisi, non persi in silenzio
    interni = {a.percorso for a in es.avvisi if a.codice == "DATO_INTERNO_NON_ESPORTATO"}
    assert {"beni[b_casa0001].provenienza", "persone[p_anna0001].relazione_con_defunto", "note"} <= interni


def test_mappa_xpath_risolvibili_e_coerenti():
    es = _bozza(caso_completo())
    doc = etree.fromstring(es.xml)
    for k, v in es.mappa.items():
        trovati = doc.xpath(v["xpath"], namespaces=NS)
        assert len(trovati) == 1, (k, v["xpath"])
    # la devoluzione punta al rigo/modulo EA della persona
    dev = es.mappa["d_contluca"]
    el = doc.xpath(dev["xpath"], namespaces=NS)[0]
    rigo = el.findtext(f"{{{fonti.NS_SUC}}}IdentificazioneSoggetto/{{{fonti.NS_SUC}}}Rigo")
    mod = el.findtext(f"{{{fonti.NS_SUC}}}IdentificazioneSoggetto/{{{fonti.NS_SUC}}}Modulo")
    assert (int(mod), int(rigo)) == (es.mappa["p_luca0001"]["modulo"], es.mappa["p_luca0001"]["rigo"])
    assert es.mappa["b_casa0001"]["quadro"] == "EC" and es.mappa["b_terr0001"]["quadro"] == "EB"
    assert es.mappa["p_defunto1"]["quadro"] == "Frontespizio"


def test_determinismo():
    a = _bozza(caso_completo())
    b = _bozza(caso_completo())
    assert a.xml == b.xml and a.mappa == b.mappa and a.impronta_xml == b.impronta_xml


def test_id_stabili_al_riordino_righe():
    base = _bozza(caso_completo())
    rnd = random.Random(7)
    for _ in range(5):
        d = caso_completo()
        for coll in ("persone", "beni", "devoluzioni", "passivita"):
            rnd.shuffle(d[coll])
        es = _bozza(d)
        assert es.xml == base.xml
        assert es.mappa == base.mappa


def _quattro_figli() -> dict:
    """Caso con quattro figli (CF sintetici validi): per legge 1/4 ciascuno su tutti i beni (Allegato 5)."""
    d = caso_completo()
    tel = d["opzioni"]["telematico"]
    for i, (nome, sesso) in enumerate((("Bruno", "M"), ("Carla", "F")), 3):
        pid = f"p_figlio00{i}"
        d["persone"].append({"id": pid, "_origine": {}, "cognome": "Rossi", "nome": nome,
                             "codice_fiscale": genera_cf_sintetico("Rossi", nome, sesso, "1975-01-01", "H501"),
                             "data_nascita": "1975-01-01", "luogo_nascita": "Roma", "ruolo": "erede"})
        tel["persone"][pid] = {"sesso": sesso, "provincia_nascita": "RM", "grado_parentela": "02"}
    d["devoluzioni"] = []
    for bid in ("b_casa0001", "b_terr0001", "b_conto001"):
        for pid in ("p_anna0001", "p_luca0001", "p_figlio003", "p_figlio004"):
            d["devoluzioni"].append({"id": f"d_{bid[2:6]}{pid[2:]}", "_origine": {}, "bene_id": bid,
                                     "persona_id": pid, "quota": "1/4", "diritto": "1"})
    d["passivita"] = []
    del tel["passivita"]
    return d


def test_continuazione_oltre_tre_devoluzioni_e_secondo_modulo_ea():
    d = _quattro_figli()
    es = _bozza(d)
    assert es.errori == [] and es.non_supportato == [], (es.errori, es.non_supportato)
    assert xsd.valida_xsd(es.xml) == []
    casa = es.mappa["b_casa0001"]
    assert len(casa["righi_continuazione"]) == 1
    doc = etree.fromstring(es.xml)
    righi = doc.xpath("//suc:QuadroEC/suc:Modulo/suc:Fabbricati", namespaces=NS)
    assert len(righi) == 2
    assert righi[0].xpath("suc:DevoluzioneEC/suc:Continuazione/text()", namespaces=NS) == ["1"]
    assert righi[1].find(f"{{{fonti.NS_SUC}}}Luogo") is None  # rigo di continuazione: solo devoluzione
    # quattro soggetti EA -> due moduli (3 righi per modulo)
    assert len(doc.xpath("//suc:QuadroEA/suc:Modulo", namespaces=NS)) == 2
    assert {es.mappa[p]["modulo"] for p in ("p_anna0001", "p_luca0001", "p_figlio003", "p_figlio004")} == {1, 2}


def test_casi_non_supportati_non_esportano():
    casi = {}
    d = caso_completo()
    d["documenti_ref"] = [{"id": "dr_aaaa0001", "_origine": {}, "allegato_id": "x", "tipo_eg": "Testamento"}]
    casi["EG testamento"] = d
    d = caso_completo()
    d["persone"][2]["ruolo"] = "legatario"
    casi["legatario"] = d
    d = caso_completo()
    d["devoluzioni"][0]["diritto"] = "8"  # usufrutto devoluto da piena proprieta'
    casi["diritto diverso"] = d
    d = caso_completo()
    d["opzioni"]["telematico"]["beni"]["b_casa0001"]["provincia"] = "BZ"
    casi["tavolare"] = d
    d = caso_completo()
    d["opzioni"]["telematico"]["persone"]["p_anna0001"]["chiave_ignota"] = 1
    casi["chiave ignota"] = d
    d = caso_completo()
    d["opzioni"]["telematico"]["dichiarazione"]["devoluzione_per_legge"] = False
    casi["testamento"] = d
    d = caso_completo()
    d["opzioni"]["quadri_attivi"] = ["EA", "EB", "EC", "ED", "ER", "EG", "EN"]
    casi["quadro EN attivo"] = d
    for nome, dati in casi.items():
        es = _bozza(dati)
        assert es.xml is None, nome
        assert es.non_supportato or es.errori and nome in ("EG testamento", "legatario"), nome  # errori di dato: EG2 e legatario senza testamento
    es = _bozza(casi["EG testamento"])
    assert any(e.codice == "DATI_INCOERENTI" for e in es.errori)


def test_errori_dati_leggibili_con_percorso_e_fonte():
    d = caso_completo()
    del d["opzioni"]["telematico"]["persone"]["p_anna0001"]["grado_parentela"]
    d["beni"][0]["valore"] = "126000.40"
    d["devoluzioni"][1]["quota"] = {"num": 1, "den": 3}
    d["opzioni"]["telematico"]["dichiarazione"]["firma_dichiarante"] = False
    es = _bozza(d)
    assert es.xml is None
    per = {e.percorso: e for e in es.errori}
    assert per["persone[p_anna0001].grado_parentela"].codice == "DATO_MANCANTE"
    assert per["beni[b_casa0001].valore"].codice == "VALORE_NON_VALIDO"
    assert "unita' di euro" in per["beni[b_casa0001].valore"].messaggio
    assert per["beni[b_casa0001].valore"].fonte.startswith("fornituraSUC13_v1.xsd (SUC13_20250702)")
    assert "opzioni.telematico.dichiarazione.firma_dichiarante" in per
    assert all(e.fonte for e in es.errori)


def test_quote_devoluzione_e_soggetto_senza_devoluzione():
    d = caso_completo()
    d["devoluzioni"] = [x for x in d["devoluzioni"] if x["id"] != "d_casaluca"]
    es = _bozza(d)
    codici = {e.codice for e in es.errori}
    assert "QUOTE_DEVOLUZIONE" in codici


def test_presentatore_e_impegno():
    d = caso_completo()
    es = esporta_xml(d, contesto(tipo_fornitore="10", cf_fornitore="12345678901", scopo="bozza_tecnica"))
    assert any(e.percorso == "contesto.impegno" for e in es.errori)
    es = esporta_xml(d, contesto(tipo_fornitore="10", cf_fornitore="12345678901", impegno_codice="2",
                                 data_impegno="2026-10-30", scopo="bozza_tecnica"))
    assert es.errori == [] and es.xml is not None
    doc = etree.fromstring(es.xml)
    # i figli ereditati da reg:ImpegnoATrasmettere_Type sono nel namespace reg
    assert doc.xpath("//suc:ImpegnoATrasmettere/reg:CFintermediario/text()", namespaces=NS) == ["12345678901"]
    assert doc.xpath("//suc:Frontespizio/suc:Presentatore/suc:CodiceFiscale/text()",
                     namespaces={"suc": fonti.NS_SUC}) == [CF_ANNA]


def test_riferimento_errori_xsd_alla_mappa():
    es = _bozza(caso_completo())
    xp = es.mappa["b_casa0001"]["xpath"].replace("suc:Modulo[1]", "suc:Modulo").replace("suc:Fabbricati[1]",
                                                                                       "suc:Fabbricati")
    err = _riferisci([Errore("XSD_FORMATO", xp + "/suc:Valore", "x", "y")], es.mappa)
    assert err[0].percorso.startswith("beni[b_casa0001] @ /tm:Messaggio")


def test_input_non_modificato():
    d = caso_completo()
    prima = copia(d)
    _bozza(d)
    assert d == prima


def test_regole_annotazioni_frontespizio_ea():
    d = caso_completo()
    d["persone"][0]["data_decesso"] = "2006-10-01"  # non successiva al 2 ottobre 2006
    d["opzioni"]["telematico"]["persone"]["p_anna0001"]["grado_parentela"] = "13"  # cognata: esclusa per legge
    d["persone"][2]["relazione_con_defunto"] = "01"  # coniuge con defunto vedovo (stato civile 4)
    es = _bozza(d)
    per = {(e.codice, e.percorso) for e in es.errori}
    assert ("REGOLA_DATA_DECESSO", "persone[p_defunto1].data_decesso") in per
    assert ("REGOLA_GRADO_LEGGE", "persone[p_anna0001].grado_parentela") in per
    assert ("REGOLA_GRADO_CONIUGE", "persone[p_luca0001].grado_parentela") in per
    assert es.xml is None
