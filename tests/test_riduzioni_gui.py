"""Maschere GUI per le riduzioni dell'art. 25 e i codici L, Q, R, F (docs/regole/riduzioni_art25.md): i dati sono inseriti
come li scrive la GUI (salvaTutto: un'unica operazione ``set`` su opzioni.telematico, valori testo dei menu) e l'esportazione
li accetta senza errori. Dati sintetici."""
import copy
from pathlib import Path

from lxml import etree

from successioni import schema as S
from successioni.archivio import Archivio
from successioni.servizio import Servizio
from successioni.telematico import riduzioni_art25 as RA
from successioni.telematico.esporta import esporta_xml
from test_elaborati import ops_da_caso
from test_telematico_controllo import NS
from test_telematico_riduzioni_art25 import CTX, D, base, con_eg

JS = (Path(__file__).parent.parent / "src" / "successioni" / "static" / "app.js").read_text(encoding="utf-8")


def _pratica(tmp_path, d):
    s = Servizio(Archivio(tmp_path / "dati"))
    return s, s.crea_pratica("Caso sintetico", iniziali=ops_da_caso(d))["pratica_id"]


def _salva_gui(s, pid, modifica):
    cur = s.leggi(pid)
    tel = copy.deepcopy(cur["dati"]["opzioni"].get("telematico") or {})
    modifica(tel)
    return s.aggiorna(pid, cur["revisione"], [{"op": "set", "sezione": "opzioni", "campi": {"telematico": tel}}],
                      canale="gui", chiave="k" + str(len(str(tel))))


def _es(s, pid):
    return esporta_xml(s.leggi(pid)["dati"], CTX)


def _x(es, xp):
    return etree.fromstring(es.xml).xpath(xp, namespaces=NS)


def _senza_riduzioni():
    d = base()
    con_eg(d)
    tel = d["opzioni"]["telematico"]
    tel.pop("devoluzioni", None)
    tel["beni"]["b_casa0001"].pop("valore_prec_succ", None)
    tel["dichiarazione"].pop("riduzioni_art25", None)
    return d


def test_riduzione_art25_inserita_come_la_gui_si_esporta(tmp_path):
    s, pid = _pratica(tmp_path, _senza_riduzioni())
    es = _es(s, pid)
    assert es.errori == [] and _x(es, D + "/suc:QuadroEC//suc:Devoluzione/suc:Riduzioni") == []     # base senza riduzione

    def gui(tel):
        for did in ("d_casaanna", "d_casaluca"):
            tel.setdefault("devoluzioni", {}).setdefault(did, {})["riduzioni"] = "2"          # menu «devoluzioni.riduzioni»
        tel.setdefault("beni", {}).setdefault("b_casa0001", {})["valore_prec_succ"] = "600000"  # campo del pannello del bene
        tel["dichiarazione"]["riduzioni_art25"] = {                                               # sezione del frontespizio
            "dichiara_requisiti": True,
            "successione_precedente": {"ufficio": "795", "anno": "2024", "volume": "88888", "numero": "123"}}
    _salva_gui(s, pid, gui)
    es = _es(s, pid)
    assert es.errori == [] and es.non_supportato == [], (es.errori, es.non_supportato)
    assert _x(es, D + "/suc:QuadroEC//suc:Devoluzione/suc:Riduzioni/text()") == ["2", "2"]
    assert _x(es, D + "/suc:QuadroEC/suc:Modulo/suc:Fabbricati[1]/suc:ValorePrecSucc/text()") == ["600000"]
    iv = D + "/suc:QuadroEH/suc:PrimoModulo/suc:SezioneIV_AltreAgevRiduz/suc:Riduzioni"
    assert _x(es, iv + "/suc:UfficioTerritoriale/text()") == ["795"]
    assert _x(es, iv + "/suc:EstremiDichiarazionePrecedente/*/text()") == ["2024", "88888", "123"]
    # svuotando i campi (la GUI toglie le chiavi vuote e gli oggetti rimasti vuoti) la riduzione sparisce
    _salva_gui(s, pid, lambda tel: (tel["devoluzioni"].pop("d_casaanna"), tel["devoluzioni"].pop("d_casaluca"),
                                    tel["beni"]["b_casa0001"].pop("valore_prec_succ"), tel["dichiarazione"].pop("riduzioni_art25")))
    assert _x(_es(s, pid), D + "/suc:QuadroEC//suc:Devoluzione/suc:Riduzioni") == []


def test_codice_l_del_dichiarante_con_data_convertita_dalla_gui(tmp_path):
    s, pid = _pratica(tmp_path, _senza_riduzioni())

    def gui(tel):
        tel.setdefault("devoluzioni", {})["d_casaanna"] = {"agevolazioni": "L"}                 # menu «devoluzioni.agevolazioni»
        tel["dichiarazione"]["riduzioni_art25"] = {"dichiara_requisiti": True,
                                                   "l": {"num_protocollo": "PROT-001", "data": "2025-09-01"}}  # 01/09/2025 -> ISO
    _salva_gui(s, pid, gui)
    es = _es(s, pid)
    assert es.errori == [] and es.non_supportato == [], (es.errori, es.non_supportato)
    assert _x(es, "//suc:DevoluzioneEC//suc:Agevolazioni/text()") == ["L"]
    l = D + "/suc:QuadroEH/suc:PrimoModulo/suc:SezioneIV_AltreAgevRiduz/suc:EsenzioneImpostaSuccessione/suc:AgevolazTipoL"
    assert _x(es, l + "/suc:NumProtocollo/text()") == ["PROT-001"]


def test_le_maschere_coprono_tutti_i_codici_e_le_chiavi_lette_dall_esportazione():
    st = S.STRUTTURATI
    assert [o["valore"] for o in st["devoluzioni.agevolazioni"]["opzioni"]][-4:] == list(RA.CODICI_AGEV) == ["L", "Q", "R", "F"]
    assert [o["valore"] for o in st["devoluzioni.riduzioni"]["opzioni"]] == list(RA.CODICI_RID)
    for o in st["devoluzioni.agevolazioni"]["opzioni"] + st["devoluzioni.riduzioni"]["opzioni"]:
        assert o["etichetta"].strip() and o["aiuto"].strip()
    assert "valore_prec_succ" in S.STRUTTURATI["beni.valore_prec_succ"]["aiuto"] or st["beni.valore_prec_succ"]["tipo"] == "importo"
    pref = "dichiarazione.riduzioni_art25."
    chiavi = {k[len(pref):] for k in st if k.startswith(pref)}
    attese = {"dichiara_requisiti"} | {f"l.{k}" for k in RA.CHIAVI_L} | {f"successione_precedente.{k}" for k in RA.CHIAVI_SUCC} \
        | {f"donazione_precedente.{k}" for k in RA.CHIAVI_DON}
    assert chiavi == attese
    # ogni coefficiente citato nell'aiuto e' quello usato dal calcolo
    for o in st["devoluzioni.riduzioni"]["opzioni"]:
        coeff = float(RA.COEFF_ART25[o["valore"]])
        assert f"{coeff:.1f}".replace(".", ",") in o["aiuto"], o
    assert "sezioneRiduzioni" in JS and "riduzioni_art25" in JS and "valore_prec_succ" in JS and "pota(d)" in JS
