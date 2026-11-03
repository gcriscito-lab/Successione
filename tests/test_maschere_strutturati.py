"""Maschere dell'interfaccia per dati strutturati (prima casa P/X/Z, dichiarazioni del dichiarante, titolo esente EO):
coerenza di ``schema.STRUTTURATI`` con il codice di esportazione e percorso di scrittura GUI -> Servizio.aggiorna -> XML.
Dati SINTETICI. Le operazioni passate ad ``aggiorna`` hanno la stessa forma di quelle inviate da ``salvaTutto`` (app.js)."""
import copy
import re
import sys
from datetime import date
from pathlib import Path

import pytest
from lxml import etree
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent))
from successioni import codici
from successioni import schema as S  # noqa: E402
from successioni.archivio import Archivio  # noqa: E402
from successioni.servizio import Servizio  # noqa: E402
from successioni.telematico import prima_casa as PC  # noqa: E402
from successioni.telematico import supplemento as SUP  # noqa: E402
from successioni.telematico.esporta import esporta_xml  # noqa: E402
from successioni.web import crea_app  # noqa: E402
from telematico_casi import (ALLEGATI_A10, FIXTURE, aggiungi_fabbricato, caso_prima_casa, contesto)  # noqa: E402
from test_elaborati import ops_da_caso  # noqa: E402
from test_telematico_controllo import NS  # noqa: E402
from test_telematico_eo_esenti import caso_esente  # noqa: E402

XSD = next((Path(__file__).parent.parent / "fonti" / "Specifiche tecniche").rglob("fornituraSUC13_v1.xsd"))
D = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione"
EH2 = D + "/suc:QuadroEH/suc:PrimoModulo/suc:SezioneII_AgevPrimaCasa"
CTX = contesto(allegati=ALLEGATI_A10, data_riferimento=date(2025, 9, 1))
PREFISSO = "dichiarazione.prima_casa."


def _valori(chiave):
    return [o["valore"] for o in S.STRUTTURATI[chiave]["opzioni"]]


# ------------------------------------------------------------------ coerenza con il codice di esportazione
def test_le_chiavi_prima_casa_della_maschera_sono_quelle_lette_dall_esportazione():
    chiavi = {k[len(PREFISSO):] for k in S.STRUTTURATI if k.startswith(PREFISSO)}
    assert chiavi == PC.CHIAVI_PRIMA_CASA


def test_i_valori_ammessi_della_maschera_sono_quelli_dell_esportazione():
    assert _valori(PREFISSO + "requisito_comune") == list(PC.REQUISITO_COMUNE)
    assert _valori(PREFISSO + "altra_casa") == list(PC.ALTRA_CASA)
    assert _valori("devoluzioni.agevolazioni") == list(PC.CODICI) == ["P", "X", "Z"]


def test_la_chiave_agevolazioni_e_gestita_dal_supplemento():
    coll, campo = "devoluzioni", "agevolazioni"
    assert campo in SUP.CHIAVI[coll]
    assert "prima_casa" in SUP.CHIAVI_DICHIARAZIONE
    assert "beni.tipo_titolo" in S.STRUTTURATI and "tipo_titolo" in S.COLLEZIONI["beni"]


def test_i_tipi_di_titolo_sono_quelli_dello_schema_xsd():
    testo = XSD.read_text(encoding="utf-8")
    blocco = testo[testo.index('<xs:simpleType name="Titoli_Type">'):]
    blocco = blocco[:blocco.index("</xs:simpleType>")]
    assert re.findall(r'<xs:enumeration value="(\d)"', blocco) == _valori("beni.tipo_titolo") == ["1", "2", "3", "4"]


def test_ogni_voce_ha_etichetta_e_aiuto_e_il_titolo_esente_spiega_valore_esente():
    for chiave, d in S.STRUTTURATI.items():
        assert d["etichetta"].strip() and d["aiuto"].strip() and d["tipo"] in ("enum", "bool"), chiave
        for o in d.get("opzioni", []):
            assert o["valore"] and o["etichetta"].strip() and o["aiuto"].strip(), (chiave, o)
    esente = next(o for o in S.STRUTTURATI["beni.tipo_titolo"]["opzioni"] if o["valore"] == "3")
    assert "ValoreEsente" in esente["aiuto"] and "mai in Valore" in esente["aiuto"]
    assert "ValoreEsente" in S.AIUTI["beni.tipo_titolo"]
    assert "EC" in S.AIUTI["devoluzioni.agevolazioni"]


def test_gli_aiuti_non_citano_regole_fuori_dalle_fonti():
    """Le uniche pagine citate sono quelle di docs/regole/prima_casa.md (Fascicolo I p. 26, 26-27, 57, 60)."""
    testo = " ".join(o["aiuto"] for d in S.STRUTTURATI.values() for o in d.get("opzioni", [])) + " ".join(
        d["aiuto"] for d in S.STRUTTURATI.values())
    assert set(re.findall(r"p\. (\d+(?:-\d+)?)", testo)) <= {"26", "26-27", "57", "60"}


def test_lo_schema_web_espone_le_maschere(tmp_path):
    with TestClient(crea_app(Servizio(Archivio(tmp_path / "d")), token="sintetico", ammetti_host_di_prova=True)) as cl:
        r = cl.get("/api/schema?t=sintetico").json()
    # le voci scritte a mano arrivano invariate; in piu' ci sono solo i menu dei codici ufficiali generati dagli XSD (codici.py)
    assert {k: v for k, v in r["strutturati"].items() if k in S.STRUTTURATI} == S.STRUTTURATI
    assert "devoluzioni.agevolazioni" in r["strutturati"]
    assert set(r["strutturati"]) - set(S.STRUTTURATI) <= set(codici.REGOLE)


def test_la_gui_ha_una_maschera_per_ogni_chiave_di_supplemento():
    """Chiavi di ``opzioni.telematico`` lette dall'esportazione e raggiungibili dalla GUI (campi del modello comune,
    maschere dedicate o sezione dichiarazione). Unica eccezione dichiarata: pagamento_rateale (non supportato)."""
    campi_modello = {"persone": set(S.COLLEZIONI["persone"]), "beni": set(S.COLLEZIONI["beni"]),
                     "passivita": set(S.COLLEZIONI["passivita"])}
    senza_maschera = []
    for coll, chiavi in SUP.CHIAVI.items():
        for k in chiavi:
            ok = (coll in campi_modello and k in campi_modello[coll]) or f"{coll}.{k}" in S.STRUTTURATI
            if not ok:
                senza_maschera.append(f"{coll}.{k}")
    js = (Path(__file__).parent.parent / "src" / "successioni" / "static" / "app.js").read_text(encoding="utf-8")
    # dati strutturati con maschera propria in app.js (renderStrutturati)
    gestiti_js = {"persone.portatore_handicap", "beni.superficie", "beni.estremi_trascrizione", "beni.estremi_registrazione",
                  "passivita.ripartizione"}
    for k in gestiti_js:
        assert k.split(".")[1] in js, k
    assert set(senza_maschera) - gestiti_js == set(), senza_maschera
    dich_js = [k for k in SUP.CHIAVI_DICHIARAZIONE if k not in ("pagamento_rateale", "prima_casa") and k not in js]
    assert dich_js == []


# ------------------------------------------------------------------ percorso di scrittura GUI -> XML
def _base():
    """caso_prima_casa senza i dati che la GUI deve poter inserire (codice P e dichiarazioni)."""
    d = copy.deepcopy(caso_prima_casa())
    d["opzioni"]["telematico"].pop("devoluzioni")
    d["opzioni"]["telematico"]["dichiarazione"].pop("prima_casa")
    return d


def _pratica(tmp_path, d):
    s = Servizio(Archivio(tmp_path / "dati"))
    pid = s.crea_pratica("Caso sintetico", iniziali=ops_da_caso(d))["pratica_id"]
    return s, pid


def _salva_come_la_gui(s, pid, *, agevolazioni=None, prima_casa=None):
    """Replica di salvaTutto(): legge opzioni.telematico, modifica le chiavi toccate, un'unica operazione ``set``."""
    cur = s.leggi(pid)
    tel = copy.deepcopy(cur["dati"]["opzioni"].get("telematico") or {})
    for did, v in (agevolazioni or {}).items():
        tel.setdefault("devoluzioni", {}).setdefault(did, {})["agevolazioni"] = v
    if prima_casa is not None:
        tel["dichiarazione"]["prima_casa"] = prima_casa
    return s.aggiorna(pid, cur["revisione"], [{"op": "set", "sezione": "opzioni", "campi": {"telematico": tel}}],
                      canale="gui", chiave="k" + str(len(str(tel))))


def _es(s, pid):
    return esporta_xml(s.leggi(pid)["dati"], CTX)


def _x(es, xp):
    return etree.fromstring(es.xml).xpath(xp, namespaces=NS)


GUI_PC = {"dichiara_requisiti": True, "requisito_comune": "residenza", "nessuna_altra_casa_comune": True,
          "altra_casa": "nessuna"}


def test_senza_i_dati_della_maschera_la_prima_casa_non_c_e(tmp_path):
    s, pid = _pratica(tmp_path, _base())
    es = _es(s, pid)
    assert es.errori == [] and _x(es, EH2) == []


def test_codice_p_e_dichiarazioni_inseriti_dalla_gui_producono_la_sezione_ii(tmp_path):
    s, pid = _pratica(tmp_path, _base())
    _salva_come_la_gui(s, pid, agevolazioni={"d_casaanna": "P"}, prima_casa=dict(GUI_PC))
    es = _es(s, pid)
    assert es.errori == [] and es.non_supportato == [], (es.errori, es.non_supportato)
    assert len(_x(es, EH2)) == 1
    assert _x(es, EH2 + "/suc:Opzioni/suc:FlagComuneResidenza/text()") == ["1"]
    assert _x(es, EH2 + "/suc:AltraCasa/suc:FlagNessunaAltraCasa/text()") == ["1"]
    assert _x(es, EH2 + "/suc:FlagNessunaAltraCasaComune/text()") == ["1"]
    assert _x(es, EH2 + "/suc:FirmaDichiarante/text()") == ["1"]
    assert _x(es, D + "/suc:QuadroEF//suc:PrimaCasa_Numero/text()") == ["1"]
    # la riga di devoluzione porta il codice P
    assert _x(es, "//suc:DevoluzioneEC//suc:Agevolazioni/text()") == ["P"]


@pytest.mark.parametrize("scelta,elemento", [("residenza", "FlagComuneResidenza"), ("attivita", "FlagComuneAttivita"),
                                             ("stabilire_residenza", "FlagCambioResidenza")])
def test_ogni_requisito_del_comune_offerto_dalla_gui_arriva_nell_elemento_giusto(tmp_path, scelta, elemento):
    s, pid = _pratica(tmp_path, _base())
    _salva_come_la_gui(s, pid, agevolazioni={"d_casaanna": "P"}, prima_casa={**GUI_PC, "requisito_comune": scelta})
    es = _es(s, pid)
    assert es.errori == [], es.errori
    assert _x(es, EH2 + "/suc:Opzioni/suc:" + elemento + "/text()") == ["1"]
    assert len(_x(es, EH2 + "/suc:Opzioni/*")) == 1


def test_altra_casa_vendita_arriva_nell_elemento_giusto(tmp_path):
    s, pid = _pratica(tmp_path, _base())
    _salva_come_la_gui(s, pid, agevolazioni={"d_casaanna": "P"}, prima_casa={**GUI_PC, "altra_casa": "vendita"})
    es = _es(s, pid)
    assert es.errori == [], es.errori
    assert _x(es, EH2 + "/suc:AltraCasa/suc:FlagVenditaAltraCasa/text()") == ["1"]
    assert _x(es, EH2 + "/suc:AltraCasa/suc:FlagNessunaAltraCasa") == []


def test_dichiarazioni_mancanti_o_negative_bloccano_con_il_percorso_della_maschera(tmp_path):
    s, pid = _pratica(tmp_path, _base())
    _salva_come_la_gui(s, pid, agevolazioni={"d_casaanna": "P"}, prima_casa={"nessuna_altra_casa_comune": False})
    es = _es(s, pid)
    perc = {(e.codice, e.percorso) for e in es.errori}
    base = "opzioni.telematico.dichiarazione.prima_casa"
    assert ("DATO_MANCANTE", base + ".dichiara_requisiti") in perc
    assert ("DATO_MANCANTE", base + ".requisito_comune") in perc
    assert ("DATO_MANCANTE", base + ".altra_casa") in perc
    assert ("REGOLA_PRIMA_CASA_REQUISITO", base + ".nessuna_altra_casa_comune") in perc


def test_codice_p_senza_dichiarazioni_chiede_i_dati_della_sezione_ii(tmp_path):
    s, pid = _pratica(tmp_path, _base())
    _salva_come_la_gui(s, pid, agevolazioni={"d_casaanna": "P"})
    es = _es(s, pid)
    assert [e.percorso for e in es.errori if e.codice == "DATO_MANCANTE"] == ["opzioni.telematico.dichiarazione.prima_casa"]


def test_codice_x_e_z_dalla_gui(tmp_path):
    d = _base()
    aggiungi_fabbricato(d, "b_garage01", "C/6", "10000", "7")
    aggiungi_fabbricato(d, "b_casa0002", "A/3", "40000", "8")
    for v in d["devoluzioni"]:                          # l'archivio ammette solo id del tipo prefisso_alfanumerico
        v["id"] = v["id"].replace("_garage01_", "_garage01").replace("_casa0002_", "_casa0002")
    s, pid = _pratica(tmp_path, d)
    _salva_come_la_gui(s, pid, agevolazioni={"d_casaanna": "P", "d_garage01anna": "X", "d_casa0002anna": "Z"},
                       prima_casa=dict(GUI_PC))
    es = _es(s, pid)                                   # Z senza impegno all'unione catastale
    assert [e.percorso for e in es.errori] == ["opzioni.telematico.dichiarazione.prima_casa.impegno_unione_catastale"]
    _salva_come_la_gui(s, pid, prima_casa={**GUI_PC, "impegno_unione_catastale": True})
    es = _es(s, pid)
    assert es.errori == [], es.errori
    assert _x(es, EH2 + "/suc:FlagContigui/text()") == ["1"]
    assert len(_x(es, EH2 + "/suc:ImmobileContiguo")) == 1 and len(_x(es, EH2 + "/suc:Pertinenza")) == 1


def test_rimuovere_il_codice_dalla_gui_riporta_all_assenza_di_agevolazione(tmp_path):
    s, pid = _pratica(tmp_path, _base())
    _salva_come_la_gui(s, pid, agevolazioni={"d_casaanna": "P"}, prima_casa=dict(GUI_PC))
    cur = s.leggi(pid)
    tel = copy.deepcopy(cur["dati"]["opzioni"]["telematico"])
    del tel["devoluzioni"]["d_casaanna"]                # come salvaTutto con valore null: la chiave sparisce
    del tel["devoluzioni"]
    s.aggiorna(pid, cur["revisione"], [{"op": "set", "sezione": "opzioni", "campi": {"telematico": tel}}])
    es = _es(s, pid)                                    # dichiarazioni rimaste senza codice P: incoerenza segnalata
    assert [e.codice for e in es.errori] == ["DATI_INCOERENTI"]
    assert es.errori[0].percorso == "opzioni.telematico.dichiarazione.prima_casa"
    cur = s.leggi(pid)
    del tel["dichiarazione"]["prima_casa"]
    s.aggiorna(pid, cur["revisione"], [{"op": "set", "sezione": "opzioni", "campi": {"telematico": tel}}])
    es = _es(s, pid)
    assert es.errori == [] and _x(es, EH2) == [] and _x(es, "//suc:DevoluzioneEC//suc:Agevolazioni") == []


def test_codice_su_bene_non_ec_e_segnalato_dall_esportazione(tmp_path):
    d = _base()
    s, pid = _pratica(tmp_path, d)
    terr = next(x["id"] for x in d["devoluzioni"] if x["bene_id"] == "b_terr0001")
    _salva_come_la_gui(s, pid, agevolazioni={terr: "P"})
    es = _es(s, pid)
    assert any(e.codice == "REGOLA_AGEVOLAZIONE_QUADRO" for e in es.errori), es.errori


# ------------------------------------------------------------------ titolo esente (EO, tipo 3)
Q = D + "/suc:QuadroEO/suc:Modulo/suc:Titoli"


def test_titolo_impostato_esente_dalla_gui_va_in_valore_esente(tmp_path):
    d = caso_esente()
    bot = next(b for b in d["beni"] if b["id"] == "b_bot00001")
    bot["tipo_titolo"] = "2"                            # prima come titolo non quotato
    s, pid = _pratica(tmp_path, d)
    es = _es(s, pid)
    riga = lambda e: etree.fromstring(e.xml).xpath(Q + "[suc:Descrizione='BOT SINTETICO']", namespaces=NS)[0]  # noqa: E731
    assert es.errori == [] and riga(es).xpath("suc:Possesso/suc:Valore/text()", namespaces=NS) == ["8000"]
    cur = s.leggi(pid)
    s.aggiorna(pid, cur["revisione"], [{"op": "upsert", "coll": "beni", "id": "b_bot00001", "campi": {"tipo_titolo": "3"}}])
    es = _es(s, pid)
    r = riga(es)
    assert es.errori == [] and es.non_supportato == [], (es.errori, es.non_supportato)
    assert r.xpath("suc:TipoTitolo/text()", namespaces=NS) == ["3"]
    assert r.xpath("suc:Possesso/suc:ValoreEsente/text()", namespaces=NS) == ["8000"]
    assert r.xpath("suc:Possesso/suc:Valore", namespaces=NS) == []
