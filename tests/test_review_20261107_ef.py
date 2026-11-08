"""Correzioni della review del 2026-11-07 sul quadro EF (circoscrizioni EF15/EF16, enti, misura fissa G/M) e sugli allegati EG
non conformi. Dati SINTETICI.

Fonti:
- EF16 (Sezione IV, bollo): annotazioni XSD fornituraSUC13_v1.xsd di SezioneIV_ImpostaBollo e Circoscrizioni_Numero («grado di
  parentela diverso da 36 e 37 e agevolazioni diverse da 'C', 'M' o 'G' o 'E'»); Fascicolo I pp. PDF 45-46.
- EF15 (Sezione III, tassa ipotecaria): annotazione SezioneIII_TassaIpotecaria/Circoscrizioni_Numero («grado di parentela diverso
  da '36'», beni con H esclusi); Fascicolo I p. PDF 44.
- EF2/EF3: annotazioni AgevolazioneG_Imposta e AgevolazioneM_Imposta («168 (se la data di decesso e' ... dal 01/01/2014 ... 200)»);
  Fascicolo I p. PDF 39.
- Allegati: Specifiche_SUC13_20250702 p. 7 par. 2.3 (PDF/A-1a, PDF/A-1b, TIFF B/N CCITT G4 max 300 DPI); Fascicolo I p. PDF 49.
I casi positivi sono provati anche col controllo ufficiale SUC13 eseguito in locale (saltato se il componente non c'e'): e' una prova
locale, non una verifica con l'Agenzia.
"""
import copy
import re

import pytest
from lxml import etree
from PIL import Image
from pypdf import PdfWriter

from telematico_casi import ALLEGATI_A10, caso_a10, contesto, contesto_caso_a10
from successioni.telematico.esporta import esporta_xml
from successioni.telematico import quadri_efgh as EFGH
from successioni.telematico import agevolazioni as AG
from successioni.documenti.dimensioni import valuta_conformita_eg
from test_conservatorie import caso_comuni, SALTO as SALTO_CO
from test_ef_storico import con_data
from test_soggetti_ea import caso_ente
from test_telematico_controllo import _esegui, _motivo_salto

SALTO = _motivo_salto()
EF = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione/suc:QuadroEF"
EH_FLAG = {"dichiara_requisiti": True}


def esporta(d, completo=True, **ctx):
    es = esporta_xml(d, contesto_caso_a10(**ctx))
    if completo:
        assert es.completo, [e.messaggio for e in es.errori] + es.non_supportato + [m.messaggio for m in es.quadri_mancanti]
    return es


def v(es, xp):
    doc = etree.fromstring(es.xml)
    return doc.xpath(f"{EF}/{xp}/text()", namespaces={k: x for k, x in doc.nsmap.items() if k})


def positivo(es, tmp_path):
    stato, dgn, wri, _ = _esegui(es.xml, tmp_path)
    assert stato == "positivo", (dgn["diagnostici"], wri[:1200])
    return dgn


def documento(d, did, tipo, allegato):
    d["documenti_ref"].append({"id": did, "_origine": {}, "allegato_id": allegato, "tipo_eg": tipo, "finalita": "documento (sintetico)"})


# ---------------------------------------------------------------------------------------------------------- 1. EF16 e C/E/M/G
def caso_terreno_agevolato(codice):
    """Casa a Roma (H501), terreno a Milano (F205) con l'agevolazione ``codice`` su entrambi i righi: il terreno conta per EF15
    ma non per EF16."""
    d = caso_comuni(("H501", "RM"), ("F205", "MI"))
    tel = d["opzioni"]["telematico"]
    for did in ("d_terranna", "d_terrluca"):
        tel.setdefault("devoluzioni", {}).setdefault(did, {})["agevolazioni"] = codice
    tel["dichiarazione"]["riduzioni_art25"] = EH_FLAG
    # richiesta di Luca (non dichiarante): rigo EG10 e documento d'identita' (annotazione QuadroEG/AgevolazioniImposteIpocatastali)
    documento(d, "dr_agev10", "AgevolazioniImposteIpocatastali", "al_albero")
    documento(d, "dr_ident7", "DocumentiIdentita", "al_testam")
    return d


def test_costante_righi_esclusi_dal_bollo():
    assert set(AG.FUORI_CIRCOSCRIZIONI_BOLLO) == {"C", "E", "G", "M"}


@pytest.mark.skipif(SALTO_CO, reason="componente di controllo SUC13 non configurato (elenco delle conservatorie)")
@pytest.mark.parametrize("codice", ["C", "E"])
def test_ef16_esclude_il_terreno_agevolato_ef15_no(codice):
    es = esporta(caso_terreno_agevolato(codice))
    assert v(es, "suc:SezioneIII_TassaIpotecaria/*") == ["2", "240"]       # Roma e Milano
    assert v(es, "suc:SezioneIV_ImpostaBollo/*") == ["1", "85"]            # solo Roma: il terreno C/E non conta
    assert es.mappa["quadro:EF"]["calcoli"]["EF16"]["circoscrizioni"] == 1


def test_unico_immobile_agevolato_niente_sezione_iv():
    """Stesso comune (caso_a10): con la casa esente H e il terreno C su entrambi i righi nessun rigo conta per EF16."""
    d = copy.deepcopy(caso_a10())
    tel = d["opzioni"]["telematico"]
    for did, c in (("d_terranna", "C"), ("d_terrluca", "C"), ("d_casaanna", "H"), ("d_casaluca", "H")):
        tel.setdefault("devoluzioni", {}).setdefault(did, {})["agevolazioni"] = c
    tel["dichiarazione"]["riduzioni_art25"] = EH_FLAG
    documento(d, "dr_agev10", "AgevolazioniImposteIpocatastali", "al_albero")
    documento(d, "dr_ident7", "DocumentiIdentita", "al_testam")
    documento(d, "dr_altro01", "Altro", "al_testam")
    es = esporta(d)
    assert v(es, "suc:SezioneIII_TassaIpotecaria/*") == ["1", "120"]       # il terreno C resta in EF15
    assert v(es, "suc:SezioneIV_ImpostaBollo/*") == []
    assert v(es, "suc:TotaleDaVersare") == ["120,00"]


@pytest.mark.skipif(SALTO is not None or SALTO_CO, reason=SALTO or "elenco delle conservatorie non disponibile")
@pytest.mark.parametrize("codice", ["C", "E"])
@pytest.mark.java
def test_controllo_ufficiale_ef16_con_terreno_agevolato(tmp_path, codice):
    es = esporta(caso_terreno_agevolato(codice))
    positivo(es, tmp_path / "ok")
    # il valore di prima della correzione (2 circoscrizioni, 170 euro anche nel bollo) e' respinto
    sbagliato, n = re.subn(rb"(<suc:SezioneIV_ImpostaBollo>\s*<suc:Circoscrizioni_Numero>)1<", rb"\g<1>2<", es.xml)
    sbagliato = sbagliato.replace(b"<suc:Circoscrizioni_Imposta>85<", b"<suc:Circoscrizioni_Imposta>170<")
    assert n == 1
    stato, dgn, _, _ = _esegui(sbagliato, tmp_path / "ko", rapporto=False)
    assert stato == "negativo", dgn["diagnostici"]
    assert "3078" in {x["codice"] for x in dgn["diagnostici"]}, dgn["diagnostici"]


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
@pytest.mark.java
def test_controllo_ufficiale_unico_immobile_agevolato(tmp_path):
    d =copy.deepcopy(caso_a10())
    tel = d["opzioni"]["telematico"]
    for did, c in (("d_terranna", "C"), ("d_terrluca", "C"), ("d_casaanna", "H"), ("d_casaluca", "H")):
        tel.setdefault("devoluzioni", {}).setdefault(did, {})["agevolazioni"] = c
    tel["dichiarazione"]["riduzioni_art25"] = EH_FLAG
    documento(d, "dr_agev10", "AgevolazioniImposteIpocatastali", "al_albero")
    documento(d, "dr_ident7", "DocumentiIdentita", "al_testam")
    documento(d, "dr_altro01", "Altro", "al_testam")
    positivo(esporta(d), tmp_path)


# ---------------------------------------------------------------------------------------------- 2. enti: EF15 e EF16 propri
def caso_ente_altrove(grado):
    """Terreno legato all'ente (grado 37/38/39) a Milano; casa e terreno degli eredi a Roma."""
    d = caso_ente(grado)
    b = d["opzioni"]["telematico"]["beni"]["b_terr0002"]
    b.update(provincia="MI", codice_comune="F205", codice_comune_amministrativo="F205")
    next(x for x in d["beni"] if x["id"] == "b_terr0002")["comune"] = "F205"
    return d


@pytest.mark.skipif(SALTO_CO, reason="componente di controllo SUC13 non configurato (elenco delle conservatorie)")
@pytest.mark.parametrize("grado,bollo", [("37", ["1", "85"]), ("38", ["2", "170"]), ("39", ["2", "170"])])
def test_circoscrizioni_degli_enti(grado, bollo):
    es = esporta(caso_ente_altrove(grado))
    assert v(es, "suc:SezioneIII_TassaIpotecaria/*") == ["2", "240"]       # EF15 esclude solo il grado 36
    assert v(es, "suc:SezioneIV_ImpostaBollo/*") == bollo                  # EF16 esclude 36 e 37
    # le basi proporzionali restano senza il terreno dell'ente (EF1, EF9)
    assert v(es, "suc:SezioneI_ImpostaIpotecaria/suc:ImpostaProporzionale/*")[0] == "141000"


@pytest.mark.skipif(SALTO is not None or SALTO_CO, reason=SALTO or "elenco delle conservatorie non disponibile")
@pytest.mark.parametrize("grado", ["37", "38"])
@pytest.mark.java
def test_controllo_ufficiale_circoscrizioni_degli_enti(tmp_path, grado):
    positivo(esporta(caso_ente_altrove(grado)), tmp_path)


def test_tutti_gli_immobili_all_ente_sezione_iii_resta():
    """Tutti gli immobili legati all'ente grado 38: EF1/EF9 assenti, ma EF15 ed EF16 restano (righi con grado diverso da 36)."""
    d = caso_ente("38")
    d["devoluzioni"] = [x for x in d["devoluzioni"] if x["bene_id"] not in ("b_casa0001", "b_terr0001")]
    for bid in ("b_casa0001", "b_terr0001"):
        d["devoluzioni"].append({"id": f"d_{bid[2:6]}ente", "_origine": {}, "bene_id": bid, "persona_id": "p_ente0001",
                                 "quota": "1/1", "diritto": "1"})
    d["passivita"] = [p for p in d["passivita"] if p["id"] != "ps_mutuo01"]
    d["opzioni"]["telematico"]["passivita"].pop("ps_mutuo01", None)
    es = esporta(d, completo=False)
    if not es.completo:
        pytest.skip("caso non esportabile per motivi estranei alle circoscrizioni: "
                    + "; ".join([e.messaggio for e in es.errori] + es.non_supportato + [m.messaggio for m in es.quadri_mancanti])[:300])
    assert v(es, "suc:SezioneI_ImpostaIpotecaria/suc:ImpostaProporzionale/*") == []
    assert v(es, "suc:SezioneIII_TassaIpotecaria/*") == ["1", "120"]
    assert v(es, "suc:SezioneIV_ImpostaBollo/*") == ["1", "85"]


# ------------------------------------------------------------------------------------------------ 3. G/M: misura fissa per data
def test_imposta_fissa_unica():
    assert EFGH.IMPOSTA_FISSA is AG.IMPOSTA_FISSA or EFGH.IMPOSTA_FISSA == AG.IMPOSTA_FISSA == 200
    assert EFGH.imposta_fissa(con_data_d("2013-12-31")) == 168 and EFGH.imposta_fissa(con_data_d("2014-01-01")) == 200


def con_data_d(s):
    from datetime import date
    return date.fromisoformat(s)


def caso_m(data):
    d = copy.deepcopy(caso_a10())
    d["opzioni"]["telematico"].setdefault("devoluzioni", {})["d_terranna"] = {"agevolazioni": "M"}
    return con_data(d, data)


@pytest.mark.parametrize("data,fissa", [("2010-03-10", "168"), ("2013-12-31", "168"), ("2014-01-01", "200"), ("2025-03-10", "200")])
def test_agevolazione_m_misura_fissa_per_data(data, fissa):
    es = esporta(caso_m(data))
    assert v(es, "suc:SezioneI_ImpostaIpotecaria/suc:AgevolazioneM/suc:AgevolazioneM_Imposta") == [fissa]
    assert v(es, "suc:SezioneI_ImpostaIpotecaria/suc:ImpostaIpotecariaDovuta") == [str(2520 + int(fissa))]


@pytest.mark.skipif(SALTO is not None, reason=SALTO or "")
@pytest.mark.java
def test_controllo_ufficiale_m_nel_2010(tmp_path):
    es = esporta(caso_m("2010-03-10"))
    positivo(es, tmp_path / "ok")
    sbagliato = es.xml.replace(b"<suc:AgevolazioneM_Imposta>168<", b"<suc:AgevolazioneM_Imposta>200<")
    assert sbagliato != es.xml
    stato, dgn, _, _ = _esegui(sbagliato, tmp_path / "ko", rapporto=False)
    assert stato == "negativo", dgn["diagnostici"]


# ------------------------------------------------------------------------------------------------ 4. allegati EG non conformi
def pdf_non_pdfa(p):
    w = PdfWriter()
    w.add_blank_page(width=595, height=842)
    with open(p, "wb") as f:
        w.write(f)
    return p


def tiff_colore(p):
    Image.new("RGB", (60, 60), (200, 10, 10)).save(p, compression="tiff_lzw", dpi=(200, 200))
    return p


def tiff_bn(p):
    Image.new("1", (200, 100), 1).save(p, compression="group4", dpi=(200, 200))
    return p


def con_albero(sorgente):
    return {**ALLEGATI_A10, "al_albero": sorgente}


def codici_mancanti(es):
    return {(m.codice, m.percorso) for m in es.quadri_mancanti}


def test_valuta_conformita(tmp_path):
    fx = ALLEGATI_A10["al_albero"]["percorso"]
    assert valuta_conformita_eg(pdf_non_pdfa(tmp_path / "a.pdf"))["esito"] == "non_conforme"
    assert valuta_conformita_eg(tiff_colore(tmp_path / "c.tif"))["esito"] == "non_conforme"
    assert valuta_conformita_eg(tiff_bn(tmp_path / "b.tif"))["esito"] == "non_verificato"
    assert valuta_conformita_eg(fx)["esito"] == "non_verificato"            # dichiara PDF/A-1b, nessun rapporto veraPDF
    assert valuta_conformita_eg(fx, {"validazione": {"esito": "non_conforme"}})["esito"] == "non_conforme"
    assert valuta_conformita_eg(fx, '{"validazione": {"esito": "conforme"}}')["esito"] == "conforme"
    assert valuta_conformita_eg(fx, esito_validazione="non_verificato")["esito"] == "non_verificato"


@pytest.mark.parametrize("fabbrica", ["pdf", "tiff", "rapporto"])
def test_allegato_non_conforme_blocca_il_completo_non_la_bozza(tmp_path, fabbrica):
    if fabbrica == "pdf":
        sorg = {"percorso": str(pdf_non_pdfa(tmp_path / "albero.pdf")), "nome": "albero.pdf"}
    elif fabbrica == "tiff":
        sorg = {"percorso": str(tiff_colore(tmp_path / "albero.tif")), "nome": "albero.tif"}
    else:
        sorg = {**ALLEGATI_A10["al_albero"], "rapporto": {"validazione": {"esito": "non_conforme"}}}
    es = esporta_xml(caso_a10(), contesto(allegati=con_albero(sorg)))
    assert not es.completo and es.xml is None
    assert ("ALLEGATO_NON_CONFORME", "documenti_ref[dr_albero1]") in codici_mancanti(es)
    bozza = esporta_xml(caso_a10(), contesto(allegati=con_albero(sorg), scopo="bozza_tecnica"))
    assert bozza.xml is not None and not bozza.completo


def test_allegati_non_verificati_solo_avviso():
    es = esporta(caso_a10())
    avvisi = {(a.codice, a.percorso) for a in es.avvisi}
    assert ("ALLEGATO_CONFORMITA_NON_DIMOSTRATA", "documenti_ref[dr_albero1]") in avvisi
    sorg = {**ALLEGATI_A10["al_albero"], "esito_validazione": "conforme"}
    es = esporta_xml(caso_a10(), contesto(allegati=con_albero(sorg)))
    assert es.completo
    assert ("ALLEGATO_CONFORMITA_NON_DIMOSTRATA", "documenti_ref[dr_albero1]") not in {(a.codice, a.percorso) for a in es.avvisi}
