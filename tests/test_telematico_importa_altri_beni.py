"""Importazione dei quadri EL, EM, EN, EO, EP, EQ ed EI: andata e ritorno identica con l'esportazione (dati sintetici), rifiuto dei
file troncati o incoerenti e prova «nessuna perdita silenziosa» (un campo significativo non letto e' un errore esplicito)."""
import copy
import re
from datetime import date

import pytest
from lxml import etree

from successioni.archivio import Archivio
from successioni.servizio import Servizio
from successioni.telematico.esporta import esporta_xml
from successioni.telematico.importa import XmlNonImportabile, importa_xml
from telematico_casi import (caso_a10, caso_azienda, caso_mezzi, caso_tavolare, caso_titoli, caso_voltura,
                             contesto, contesto_caso_a10)
from test_telematico_esporta import _quattro_figli

CTX = contesto_caso_a10(data_riferimento=date(2025, 9, 1))
CTX_BOZZA = contesto(scopo="bozza_tecnica")
SUC = "urn:www.agenziaentrate.gov.it:specificheTecniche:sco:suc:v1"
NS = {"suc": SUC}

CASI = {"EO": caso_titoli, "EP-EQ": caso_mezzi, "EN": caso_azienda, "EL-EM": caso_tavolare, "EI": caso_voltura}


@pytest.fixture
def sv(tmp_path):
    return Servizio(Archivio(tmp_path / "dati"))


def _xml(caso, ctx=CTX) -> bytes:
    es = esporta_xml(caso, ctx)
    assert es.xml is not None, (es.errori, es.non_supportato)
    return es.xml


def _giro(sv, originale: dict, ctx=CTX):
    """Esporta, importa, ricrea la pratica e riesporta (gli allegati EG si riacquisiscono a parte)."""
    xml = _xml(originale, ctx)
    r = sv.importa_xml_telematico(xml)
    dati = sv.leggi(r["pratica_id"])["dati"]
    dati["documenti_ref"] = originale["documenti_ref"]
    dati["opzioni"]["telematico"]["dichiarazione"]["dichiara_copie_conformi"] = True
    return xml, r, dati, esporta_xml(dati, ctx)


# ------------------------------------------------------------------------------------------------ andata e ritorno
@pytest.mark.parametrize("nome", list(CASI))
def test_andata_e_ritorno_identica(sv, nome):
    xml, r, dati, nuovo = _giro(sv, CASI[nome]())
    assert nuovo.errori == [] and nuovo.non_supportato == []
    assert nuovo.xml == xml, nome


def test_quadri_importati_non_sono_piu_tra_i_non_importati(sv):
    for nome, caso in CASI.items():
        r = importa_xml(_xml(caso()))
        assert [q for q in r["non_importato"] if q.split(":")[0] in
                {"QuadroEL", "QuadroEM", "QuadroEN", "QuadroEO", "QuadroEP", "QuadroEQ", "QuadroEI_new"}] == [], nome
        assert r["non_importato"][-2:] == ["QuadroEG: allegati: da riacquisire",
                                           "QuadroEH: dichiarazioni e testamento: da reinserire"]


def test_conteggi_e_quadri_attivi(sv):
    r = sv.importa_xml_telematico(_xml(caso_titoli()))
    assert r["importato"]["titoli"] == 2
    assert sv.leggi(r["pratica_id"])["dati"]["opzioni"]["quadri_attivi"] == ["EA", "EB", "EC", "ER", "ED", "EG", "EO"]
    r = sv.importa_xml_telematico(_xml(caso_mezzi()))
    assert (r["importato"]["aeromobili"], r["importato"]["navi"]) == (1, 1)
    assert sv.leggi(r["pratica_id"])["dati"]["opzioni"]["quadri_attivi"][-2:] == ["EP", "EQ"]
    r = sv.importa_xml_telematico(_xml(caso_tavolare()))
    assert (r["importato"]["terreni_tavolari"], r["importato"]["fabbricati_tavolari"]) == (1, 1)
    r = sv.importa_xml_telematico(_xml(caso_voltura()))
    assert r["importato"]["voltura"] == 1
    # senza quadri aggiuntivi la pratica resta con i quadri predefiniti
    r = sv.importa_xml_telematico(_xml(caso_a10()))
    assert "quadri_attivi" not in sv.leggi(r["pratica_id"])["dati"]["opzioni"]
    assert "titoli" not in r["importato"] and "voltura" not in r["importato"]


def test_dati_nel_modello_eo_ep_eq_en(sv):
    dati = sv.leggi(sv.importa_xml_telematico(_xml(caso_titoli()))["pratica_id"])["dati"]
    tit = sorted((b for b in dati["beni"] if b["tipo"] == "titolo"), key=lambda b: b["id"])
    assert [(b["tipo_titolo"], b["quantita"], b["tipo_documento"], b["valore"], b["diritto"], b["quota_defunto"])
            for b in tit] == [("2", "100", "3", "10000", "1", {"num": 1, "den": 1}),
                              ("4", "250", "3", "6000", "1", {"num": 1, "den": 1})]
    dati = sv.leggi(sv.importa_xml_telematico(_xml(caso_mezzi()))["pratica_id"])["dati"]
    aereo = next(b for b in dati["beni"] if b["tipo"] == "aeromobile")
    nave = next(b for b in dati["beni"] if b["tipo"] == "nave")
    assert (aereo["marca_modello"], aereo["anno_costruzione"], aereo["numero_immatricolazione"], aereo["valore"]) == (
        "AEROMOBILE SINTETICO X1", "1998", "123456", "30000")
    assert (nave["tipo_unita"], nave["sigla_ufficio_iscrizione"], nave["lunghezza"]) == ("1", "RM", "9")
    dati = sv.leggi(sv.importa_xml_telematico(_xml(caso_azienda()))["pratica_id"])["dati"]
    az = next(b for b in dati["beni"] if b["tipo"] == "azienda")
    assert (az["descrizione"], az["codice_fiscale_emittente"], az["valore"]) == (
        "ALFA IMPRESA INDIVIDUALE (SINTETICO)", "00000000018", "20000")
    assert dati["opzioni"]["telematico"]["dichiarazione"]["azienda_data_deposito"] == "2025-06-30"
    assert dati["opzioni"]["telematico"]["dichiarazione"]["azienda_camera_commercio"] == "ROMA"


def test_dati_nel_modello_tavolari_e_voltura(sv):
    dati = sv.leggi(sv.importa_xml_telematico(_xml(caso_tavolare()))["pratica_id"])["dati"]
    terr = next(b for b in dati["beni"] if b["tipo"] == "terreno")
    fabb = next(b for b in dati["beni"] if b["tipo"] == "fabbricato")
    assert (terr["provincia"], terr["partita_tavolare"], terr["corpo_tavolare"], terr["comune_catastale"],
            terr["codice_comune_catastale"]) == ("BZ", "1234", "1", "BOLZANO", "613")
    assert (fabb["partita_tavolare"], fabb["categoria"], fabb["indirizzo"]) == ("5678", "A2", "VIA ESEMPIO 3")
    assert dati["opzioni"]["telematico"]["beni"][terr["id"]]["superficie"] == {"are": 30}
    dati = sv.leggi(sv.importa_xml_telematico(_xml(caso_voltura()))["pratica_id"])["dati"]
    casa = next(b for b in dati["beni"] if b["tipo"] == "fabbricato")
    terr = next(b for b in dati["beni"] if b["tipo"] == "terreno")
    assert casa["discordanza_intestatario"] == "si" and terr["passaggi_senza_atti_legali"] == "si"
    tel = dati["opzioni"]["telematico"]["beni"][casa["id"]]
    assert tel["estremi_trascrizione"] == [{"ufficio": "RM10", "registro_particolare": "12345", "anno": "2010"}]
    assert tel["estremi_registrazione"] == [{"ufficio": "795", "anno": "2020", "volume": "88888", "numero": "123"}]


def test_azienda_senza_quota_nel_tracciato_e_un_avviso():
    """Il rigo EN non porta la quota di possesso del defunto: l'esportazione la richiede, l'importazione la assume 1/1 e lo dice."""
    r = importa_xml(_xml(caso_azienda()))
    assert len(r["avvisi"]) == 1 and "EN" in r["avvisi"][0] and "1/1" in r["avvisi"][0]
    az = next(o for o in r["operazioni"] if o.get("coll") == "beni" and o["campi"]["tipo"] == "azienda")
    assert az["campi"]["quota_defunto"] == {"num": 1, "den": 1}


# ------------------------------------------------------------------------------------ casi piu' ricchi (bozza tecnica)
def _aggiungi(d: dict, bene: dict, tel: dict | None = None):
    eredi = [p["id"] for p in d["persone"] if p["ruolo"] == "erede"]
    d["beni"].append({"_origine": {}, "diritto": "1", "quota_defunto": "1/1", **bene})
    if tel:
        d["opzioni"]["telematico"].setdefault("beni", {})[bene["id"]] = tel
    for pid in eredi:
        d["devoluzioni"].append({"id": f"d_{bene['id'][2:]}{pid[2:]}", "_origine": {}, "bene_id": bene["id"],
                                 "persona_id": pid, "quota": f"1/{len(eredi)}", "diritto": "1"})


def _caso_titoli_con_continuazioni() -> dict:
    d = _quattro_figli()
    d["opzioni"]["quadri_attivi"] = ["EA", "EB", "EC", "ER", "ED", "EG", "EO"]
    base = {"tipo": "titolo", "tipo_documento": "3", "quantita": "10"}
    _aggiungi(d, {**base, "id": "b_tit00001", "tipo_titolo": "2", "descrizione": "Azioni Beta (sintetico)", "valore": "4000"})
    _aggiungi(d, {**base, "id": "b_tit00002", "tipo_titolo": "4", "descrizione": "Fondo Gamma (sintetico)", "valore": "8000"})
    _aggiungi(d, {**base, "id": "b_tit00003", "tipo_titolo": "1", "descrizione": "Azioni quotate Delta (sintetico)",
                  "valore": "12000", "codice_fiscale_emittente": "00000000018", "codice_titolo": "IT0000000019",
                  "tipo_documento": "1", "data_documento": "2024-12-31"})
    _aggiungi(d, {**base, "id": "b_tit00004", "tipo_titolo": "2", "descrizione": "Quote Epsilon (sintetico)", "valore": "2000"})
    return d


def _caso_tavolare_ricco() -> dict:
    d = copy.deepcopy(caso_tavolare())
    comune = {"provincia": "BZ", "codice_comune": "A952", "codice_comune_amministrativo": "A952",
              "comune_catastale": "BOLZANO", "codice_comune_catastale": "613"}
    for i in (2, 3):
        _aggiungi(d, {"id": f"b_terrtav{i}", "tipo": "terreno", "comune": "Bolzano .Bozen.", "foglio": "12", "particella": f"34{i}",
                      "valore": "5000", "natura": "T", "tipologia_terreno": "3", "reddito_dominicale": "3.00",
                      "partita_tavolare": "1234", **comune}, {"superficie": {"ettari": 1, "are": 5, "centiare": 7}})
    _aggiungi(d, {"id": "b_fabbtav2", "tipo": "fabbricato", "comune": "Bolzano .Bozen.", "foglio": "12", "particella": "401",
                  "categoria": "C/2", "consistenza": "20", "rendita": "100.00", "valore": "30000", "indirizzo": "Via Esempio 4",
                  "partita_tavolare": "9999", "corpo_tavolare": "2", "porzione_materiale": "PM1", "zona_censuaria": "1", **comune})
    return d


def _caso_mezzi_con_stazza() -> dict:
    d = caso_mezzi()
    nave = next(b for b in d["beni"] if b["id"] == "b_barca001")
    nave.pop("lunghezza")
    nave["stazza"] = "15"
    nave["tipo_unita"] = "2"
    return d


def _caso_azienda_due() -> dict:
    d = caso_azienda()
    _aggiungi(d, {"id": "b_azien002", "tipo": "azienda", "descrizione": "Beta Snc (sintetico)", "valore": "5000",
                  "codice_fiscale_emittente": "00000000018"})
    return d


def _rinomina_bene(d: dict, vecchio: str, nuovo: str):
    for b in d["beni"]:
        if b["id"] == vecchio:
            b["id"] = nuovo
    for x in d["devoluzioni"]:
        if x["bene_id"] == vecchio:
            x["bene_id"] = nuovo
    tel = d["opzioni"]["telematico"]
    tel["beni"][nuovo] = tel["beni"].pop(vecchio, {})
    for p in tel["passivita"].values():
        if p.get("bene_id") == vecchio:
            p["bene_id"] = nuovo


def _caso_voltura_due(ordinato: bool) -> dict:
    d = caso_voltura()
    terr = next(b for b in d["beni"] if b["id"] == "b_terr0001")
    terr["discordanza_intestatario"] = "si"
    casa = next(b for b in d["beni"] if b["id"] == "b_casa0001")
    casa["sezione"], casa["zona_censuaria"] = "A", "2"        # SezioneUrbana e ZonaCensuaria di EC, SezioneUrbana nell'EI
    d["opzioni"]["telematico"]["beni"]["b_terr0001"]["estremi_trascrizione"] = [
        {"ufficio": "RM10", "registro_particolare": "777", "anno": "2001"},
        {"ufficio": "RM10", "registro_particolare": "888", "anno": "2002"}]
    if ordinato:     # l'esportazione scrive le sezioni EI nell'ordine degli id: il terreno (EB) deve precedere la casa
        _rinomina_bene(d, "b_terr0001", "b_aterr001")
    return d


@pytest.mark.parametrize("fabbrica,ctx", [
    (_caso_titoli_con_continuazioni, CTX_BOZZA), (_caso_tavolare_ricco, CTX_BOZZA), (_caso_mezzi_con_stazza, CTX),
    (_caso_azienda_due, CTX), (lambda: _caso_voltura_due(True), CTX)],
    ids=["EO-continuazioni", "EL-EM-ricchi", "EQ-stazza", "EN-due", "EI-due-sezioni"])
def test_andata_e_ritorno_casi_ricchi(sv, fabbrica, ctx):
    originale = fabbrica()
    if ctx is CTX_BOZZA:
        originale["documenti_ref"] = []
    xml, r, dati, nuovo = _giro(sv, originale, ctx)
    assert nuovo.errori == [] and nuovo.non_supportato == [] and nuovo.xml == xml


def test_continuazioni_eo_collegano_le_devoluzioni_al_titolo(sv):
    r = importa_xml(_xml(_caso_titoli_con_continuazioni(), CTX_BOZZA))
    titoli = [o for o in r["operazioni"] if o.get("coll") == "beni" and o["campi"]["tipo"] == "titolo"]
    dev = [o for o in r["operazioni"] if o.get("coll") == "devoluzioni"]
    assert len(titoli) == 4
    for t in titoli:
        assert sum(x["campi"]["bene_id"] == t["id"] for x in dev) == 4


# ---------------------------------------------------------------------------------------------------- file non importabili
def _testo(caso) -> str:
    return _xml(caso()).decode()


@pytest.mark.parametrize("nome,quadro", [("EO", "QuadroEO"), ("EP-EQ", "QuadroEP"), ("EP-EQ", "QuadroEQ"), ("EN", "QuadroEN"),
                                         ("EL-EM", "QuadroEL"), ("EL-EM", "QuadroEM"), ("EI", "QuadroEI_new")])
def test_file_troncato(nome, quadro):
    t = _testo(CASI[nome])
    taglio = t.index(f"<suc:{quadro}>") + 60
    for fine in (t[:taglio], t[:taglio] + f"</suc:{quadro}>"):     # troncato a meta' del quadro, anche con una sola chiusura
        with pytest.raises(XmlNonImportabile, match="non e' un XML valido"):
            importa_xml(fine.encode())


def test_righi_troncati_per_mancanza_della_continuazione():
    root = etree.fromstring(_xml(_caso_titoli_con_continuazioni(), CTX_BOZZA))
    righe = root.xpath("//suc:QuadroEO/suc:Modulo/suc:Titoli", namespaces=NS)
    assert len(righe) == 8
    righe[1].getparent().remove(righe[1])                                   # il rigo di continuazione del primo titolo
    with pytest.raises(XmlNonImportabile, match="continuazione|nuovo bene"):
        importa_xml(etree.tostring(root))
    root = etree.fromstring(_xml(_caso_titoli_con_continuazioni(), CTX_BOZZA))
    righe = root.xpath("//suc:QuadroEO/suc:Modulo/suc:Titoli", namespaces=NS)
    righe[-1].getparent().remove(righe[-1])                                 # troncato in fondo al quadro
    with pytest.raises(XmlNonImportabile, match="continuazione"):
        importa_xml(etree.tostring(root))


@pytest.mark.parametrize("nome,quadro", [("EO", "QuadroEO"), ("EP-EQ", "QuadroEP"), ("EP-EQ", "QuadroEQ"), ("EN", "QuadroEN"),
                                         ("EL-EM", "QuadroEL"), ("EL-EM", "QuadroEM")])
def test_riferimento_a_erede_inesistente(nome, quadro):
    t = _testo(CASI[nome])
    i = t.index(f"<suc:{quadro}>")
    f = t.index(f"</suc:{quadro}>")
    corpo = t[i:f].replace("<suc:Rigo>2</suc:Rigo>", "<suc:Rigo>9</suc:Rigo>", 1)
    with pytest.raises(XmlNonImportabile, match="erede inesistente"):
        importa_xml((t[:i] + corpo + t[f:]).encode())
    corpo = t[i:f].replace("<suc:Modulo>1</suc:Modulo>", "<suc:Modulo>4</suc:Modulo>", 1)   # primo "Modulo" con testo = modulo dell'erede
    with pytest.raises(XmlNonImportabile, match="erede inesistente"):
        importa_xml((t[:i] + corpo + t[f:]).encode())


@pytest.mark.parametrize("nome,vecchio,nuovo,match", [
    ("EO", "<suc:Valore>10000</suc:Valore>", "<suc:Valore>mille</suc:Valore>", "numero non valido"),
    ("EO", "<suc:Quantita>100</suc:Quantita>", "<suc:Quantita>1x0</suc:Quantita>", "attese solo cifre"),
    ("EO", "<suc:PossessoDenominatore>1</suc:PossessoDenominatore>", "<suc:PossessoDenominatore>1,5</suc:PossessoDenominatore>",
     "atteso un intero"),
    ("EO", "<suc:QuotaDenominatore>2</suc:QuotaDenominatore>", "<suc:QuotaDenominatore>due</suc:QuotaDenominatore>", "numero non valido"),
    ("EP-EQ", "<suc:AnnoCostruzione>1998</suc:AnnoCostruzione>", "<suc:AnnoCostruzione>19x8</suc:AnnoCostruzione>", "attese solo cifre"),
    ("EP-EQ", "<suc:NumeroImmatricolazione>123456</suc:NumeroImmatricolazione>",
     "<suc:NumeroImmatricolazione>12.5</suc:NumeroImmatricolazione>", "attese solo cifre"),
    ("EP-EQ", "<suc:Lunghezza>9</suc:Lunghezza>", "<suc:Lunghezza>nove</suc:Lunghezza>", "attese solo cifre"),
    ("EP-EQ", "<suc:NumeroIscrizione>98765</suc:NumeroIscrizione>", "<suc:NumeroIscrizione>9876a</suc:NumeroIscrizione>", "attese solo cifre"),
    ("EP-EQ", "<suc:Valore>30000</suc:Valore>", "<suc:Valore>NaN</suc:Valore>", "numero non valido"),
    ("EN", "<suc:Valore>20000</suc:Valore>", "<suc:Valore>venti</suc:Valore>", "numero non valido"),
    ("EL-EM", "<reg:RedditoDominicale>6,50</reg:RedditoDominicale>", "<reg:RedditoDominicale>abc</reg:RedditoDominicale>", "numero non valido"),
    ("EL-EM", "<reg:Consistenza>4,50</reg:Consistenza>", "<reg:Consistenza>4,5,0</reg:Consistenza>", "numero non valido"),
    ("EL-EM", "<reg:SuperficieAre>30</reg:SuperficieAre>", "<reg:SuperficieAre>3,5</reg:SuperficieAre>", "atteso un intero"),
    ("EI", "<suc:Anno>2010</suc:Anno>", "<suc:Anno>20x0</suc:Anno>", "attese solo cifre"),
    ("EI", "<suc:Volume>88888</suc:Volume>", "<suc:Volume>8v888</suc:Volume>", "attese solo cifre"),
    ("EI", "<suc:RegistroParticolare>12345</suc:RegistroParticolare>", "<suc:RegistroParticolare>1234 5</suc:RegistroParticolare>",
     "attese solo cifre"),
    ("EI", "<suc:DiscordanzaDatiIntestatario>1<", "<suc:DiscordanzaDatiIntestatario>2<", "atteso 1"),
])
def test_valori_non_numerici(nome, vecchio, nuovo, match):
    t = _testo(CASI[nome])
    assert vecchio in t, vecchio
    with pytest.raises(XmlNonImportabile, match=match):
        importa_xml(t.replace(vecchio, nuovo).encode())


def test_date_non_valide_nei_quadri_nuovi():
    t = _xml(_caso_titoli_con_continuazioni(), CTX_BOZZA).decode()
    assert "<suc:DataDocumento>31122024</suc:DataDocumento>" in t
    with pytest.raises(XmlNonImportabile, match="ggmmaaaa"):
        importa_xml(t.replace("31122024", "2024-12-31").encode())
    with pytest.raises(XmlNonImportabile, match="inesistente"):
        importa_xml(t.replace("31122024", "31022024").encode())
    t = _testo(caso_azienda)
    with pytest.raises(XmlNonImportabile, match="ggmmaaaa"):
        importa_xml(t.replace("<suc:DataDeposito>30062025", "<suc:DataDeposito>30-06-2025").encode())


# ------------------------------------------------------------------------- coerenza di ordine, province, EI, casi particolari
def test_righi_fuori_ordine_non_si_importano():
    root = etree.fromstring(_xml(caso_titoli()))
    mod = root.xpath("//suc:QuadroEO/suc:Modulo", namespaces=NS)[0]
    primo, secondo = mod.xpath("suc:Titoli", namespaces=NS)
    mod.remove(primo)
    mod.append(primo)
    with pytest.raises(XmlNonImportabile, match="ordine"):
        importa_xml(etree.tostring(root))


def test_provincia_tavolare_non_ricreabile():
    t = _testo(caso_tavolare)
    assert t.count("<reg:Provincia>BZ</reg:Provincia>") == 2
    with pytest.raises(XmlNonImportabile, match="provincia 'BL'"):
        importa_xml(t.replace("<reg:Provincia>BZ</reg:Provincia>", "<reg:Provincia>BL</reg:Provincia>").encode())


def test_casi_particolari_volture_e_valori_non_previsti():
    # con EB/EC la casella «non dar corso alle volture» e' una scelta del dichiarante: importata come casi_particolari, che
    # l'esportazione riscrive (2026-11-06: prima veniva rifiutata)
    t = _testo(caso_voltura)
    casella = "<suc:CasiParticolari><suc:CasiParticolari>1</suc:CasiParticolari><suc:FirmaDichiarante>1</suc:FirmaDichiarante></suc:CasiParticolari>"
    assert "'casi_particolari': True" in repr(importa_xml(t.replace("<suc:FirmaModello>", casella + "<suc:FirmaModello>", 1).encode()))
    senza_firma = "<suc:CasiParticolari><suc:CasiParticolari>1</suc:CasiParticolari><suc:FirmaDichiarante>0</suc:FirmaDichiarante></suc:CasiParticolari>"
    with pytest.raises(XmlNonImportabile, match="CasiParticolari"):
        importa_xml(t.replace("<suc:FirmaModello>", senza_firma + "<suc:FirmaModello>", 1).encode())
    t = _testo(caso_tavolare)
    assert "<suc:CasiParticolari>" in t
    importa_xml(t.encode())
    with pytest.raises(XmlNonImportabile, match="CasiParticolari"):
        importa_xml(t.replace("<suc:CasiParticolari>1</suc:CasiParticolari>", "<suc:CasiParticolari>2</suc:CasiParticolari>", 1).encode())


def _senza(t: str, frammento: str) -> str:
    assert frammento in t, frammento
    return t.replace(frammento, "", 1)


def test_ei_incoerente_con_i_beni():
    t = _testo(caso_voltura)
    i, f = t.index("<suc:QuadroEI_new>"), t.index("</suc:QuadroEI_new>") + len("</suc:QuadroEI_new>")
    with pytest.raises(XmlNonImportabile, match="QuadroEI_new assente"):
        importa_xml((t[:i] + t[f:]).encode())
    with pytest.raises(XmlNonImportabile, match="senza immobili"):
        importa_xml(_senza(_senza(t, "<suc:DiscordanzaDatiIntestatario>1</suc:DiscordanzaDatiIntestatario>"),
                           "<suc:PassaggiSenzaAttiLegali>1</suc:PassaggiSenzaAttiLegali>").encode())
    sez_i = re.search(r"<suc:SezioneI_AttiLegali>.*?</suc:SezioneI_AttiLegali>", t, re.S).group(0)
    with pytest.raises(XmlNonImportabile, match="sezione I"):
        importa_xml(t.replace(sez_i, "").encode())
    with pytest.raises(XmlNonImportabile, match="sezione I"):
        importa_xml(t.replace("<suc:FlagAttiLegali>1<", "<suc:FlagAttiLegali>0<").encode())


def test_ei_immobile_non_corrispondente_ai_beni():
    root = etree.fromstring(_xml(caso_voltura()))
    foglio = root.xpath("//suc:QuadroEI_new//suc:Immobile/suc:DatiCatastali/*[local-name()='Foglio']", namespaces=NS)[0]
    foglio.text = "101"
    with pytest.raises(XmlNonImportabile, match="0 beni"):
        importa_xml(etree.tostring(root))


def test_ei_senza_estremi_o_senza_firma_o_presentatore_diverso():
    t = _testo(caso_voltura)
    for tag in ("EstremiTrascrizione", "EstremiRegistrazione"):
        t = re.sub(rf"<suc:{tag}>.*?</suc:{tag}>", "", t, flags=re.S)
    with pytest.raises(XmlNonImportabile, match="nessun estremo"):
        importa_xml(t.encode())
    t = _testo(caso_voltura)
    i = t.index("<suc:SezioneII_DatiIntestatario>")
    sezione_fine = t.index("</suc:SezioneII_DatiIntestatario>", i)
    t2 = t[:i] + t[i:sezione_fine].replace("<suc:FirmaDichiarante>1</suc:FirmaDichiarante>", "") + t[sezione_fine:]
    with pytest.raises(XmlNonImportabile, match="firma del dichiarante"):
        importa_xml(t2.encode())
    t = _testo(caso_voltura)
    i = t.index("<suc:QuadroEI_new>")
    with pytest.raises(XmlNonImportabile, match="presentatore"):
        importa_xml((t[:i] + t[i:].replace("<reg:Nome>ANNA</reg:Nome>", "<reg:Nome>ANNO</reg:Nome>", 1)).encode())


def test_ei_estremo_incompleto():
    t = _testo(caso_voltura)
    with pytest.raises(XmlNonImportabile, match="UfficioTrascrizione assente"):
        importa_xml(_senza(t, "<suc:UfficioTrascrizione>RM10</suc:UfficioTrascrizione>").encode())


def test_ei_sezioni_in_ordine_diverso_da_quello_degli_id():
    """Con piu' immobili l'EI e' scritto nell'ordine degli id originali; gli id importati seguono EB poi EC: se l'ordine
    non coincide la riesportazione sarebbe diversa e il file si rifiuta (invece di riprodurlo cambiato)."""
    with pytest.raises(XmlNonImportabile, match="ordine degli identificativi"):
        importa_xml(_xml(_caso_voltura_due(False)))


def _sezioni_ei(root):
    return root.xpath("//suc:QuadroEI_new//suc:SezioneII_DatiIntestatario", namespaces=NS)


def test_ei_con_sezioni_di_meno_o_duplicate_non_si_importa():
    root = etree.fromstring(_xml(_caso_voltura_due(True)))
    assert len(_sezioni_ei(root)) == 2
    secondo = _sezioni_ei(root)[1]
    secondo.getparent().remove(secondo)                                  # un immobile con discordanza senza la sua sezione
    with pytest.raises(XmlNonImportabile, match="1 sezioni II per 2 immobili"):
        importa_xml(etree.tostring(root))
    root = etree.fromstring(_xml(_caso_voltura_due(True)))
    prima, seconda = _sezioni_ei(root)                                    # la seconda sezione rimanda allo stesso immobile della prima
    seconda.replace(seconda.xpath("suc:Immobile", namespaces=NS)[0], copy.deepcopy(prima.xpath("suc:Immobile", namespaces=NS)[0]))
    with pytest.raises(XmlNonImportabile, match="corrisponde a 0 beni"):
        importa_xml(etree.tostring(root))


def test_ei_immobile_ambiguo_fra_due_beni_identici():
    d = caso_voltura()
    casa = next(b for b in d["beni"] if b["id"] == "b_casa0001")
    _aggiungi(d, {**{k: v for k, v in casa.items() if k not in ("id", "provenienza")}, "id": "b_casa0002"},
              dict(d["opzioni"]["telematico"]["beni"]["b_casa0001"]))
    es = esporta_xml(d, CTX)
    assert es.xml is not None, (es.errori, es.non_supportato)
    with pytest.raises(XmlNonImportabile, match="corrisponde a 2 beni"):
        importa_xml(es.xml)


def test_ei_con_piu_estremi_e_sezioni_si_riproduce(sv):
    xml, r, dati, nuovo = _giro(sv, _caso_voltura_due(True))
    assert r["importato"]["voltura"] == 2 and nuovo.xml == xml


# ----------------------------------------------------------------- nessuna perdita silenziosa
CAMPO_IGNOTO = "CampoSignificativoNonLetto"


def _foglie(root, quadri, senza_derivate=False):
    """Nodi foglia con testo; ``senza_derivate`` esclude i valori che l'esportazione ricalcola (QuotaValore)."""
    for q in quadri:
        for e in root.xpath(f"//suc:{q}//*[not(*)]", namespaces=NS):
            if (e.text or "").strip() and not (senza_derivate and etree.QName(e).localname == "QuotaValore"):
                yield e


@pytest.mark.parametrize("nome,quadri", [("EO", ["QuadroEO"]), ("EP-EQ", ["QuadroEP", "QuadroEQ"]), ("EN", ["QuadroEN"]),
                                         ("EL-EM", ["QuadroEL", "QuadroEM"]), ("EI", ["QuadroEI_new"])])
def test_elemento_sconosciuto_in_ogni_punto_e_un_errore(nome, quadri):
    """In ogni nodo foglia di ogni quadro nuovo si aggiunge un fratello con testo non previsto: l'importazione lo rifiuta
    nominandolo (mai scartato)."""
    base = etree.fromstring(_xml(CASI[nome]()))
    n = len(list(_foglie(base, quadri)))
    assert n > 10
    for k in range(n):
        root = etree.fromstring(etree.tostring(base))
        foglia = list(_foglie(root, quadri))[k]
        etree.SubElement(foglia.getparent(), f"{{{SUC}}}{CAMPO_IGNOTO}").text = "7"
        with pytest.raises(XmlNonImportabile, match=CAMPO_IGNOTO):
            importa_xml(etree.tostring(root))


@pytest.mark.parametrize("tag,quadro,contenitore", [
    ("ValoreEsente", "QuadroEO", "Titoli"), ("Agevolazioni", "QuadroEN", "Aziende"), ("Inventario", "QuadroEN", "Aziende"),
    ("RenditaProposta", "QuadroEM", "FabbricatiTavolare"), ("Matricola", "QuadroEP", "Aeromobili"),
    ("Cantiere", "QuadroEQ", "Navi")])
def test_campo_noto_all_esportazione_ma_non_letto_e_un_errore(tag, quadro, contenitore):
    root = etree.fromstring(_xml({"QuadroEO": caso_titoli, "QuadroEN": caso_azienda, "QuadroEM": caso_tavolare,
                                  "QuadroEP": caso_mezzi, "QuadroEQ": caso_mezzi}[quadro]()))
    riga = root.xpath(f"//suc:{quadro}//suc:{contenitore}", namespaces=NS)[0]
    etree.SubElement(riga, f"{{{SUC}}}{tag}").text = "X"
    with pytest.raises(XmlNonImportabile, match=tag):
        importa_xml(etree.tostring(root))


def _modifica(testo: str) -> str:
    """Cambia il valore di una foglia (il risultato puo' non essere valido): numeri +1, centesimi +1,00, date al giorno 15."""
    if re.fullmatch(r"\d+,\d\d", testo):
        return f"{int(testo.replace(',', '')) + 100:03d}"[:-2] + "," + f"{int(testo.replace(',', '')) + 100:03d}"[-2:]
    if re.fullmatch(r"\d{8}", testo):
        return ("16" if testo[:2] == "15" else "15") + testo[2:]
    if re.fullmatch(r"\d+", testo):
        return str(int(testo) + 1)
    return testo[:-1] + "Z" if testo[-1:] != "Z" else testo[:-1] + "Y"


@pytest.mark.parametrize("nome,quadri", [("EO", ["QuadroEO"]), ("EP-EQ", ["QuadroEP", "QuadroEQ"]), ("EN", ["QuadroEN"]),
                                         ("EL-EM", ["QuadroEL", "QuadroEM"]), ("EI", ["QuadroEI_new"])])
def test_la_modifica_di_ogni_campo_non_sparisce_in_silenzio(sv, nome, quadri):
    """Per ogni foglia dei quadri nuovi si cambia il valore: o l'importazione/riesportazione segnala un errore, oppure la
    modifica e' visibile nel file riesportato (che non torna mai uguale all'originale a insaputa dell'utente)."""
    originale = CASI[nome]()
    base = etree.fromstring(_xml(originale))
    n = len(list(_foglie(base, quadri, True)))
    silenziosi = []
    for k in range(n):
        root = etree.fromstring(etree.tostring(base))
        foglia = list(_foglie(root, quadri, True))[k]
        percorso = root.getroottree().getpath(foglia)
        foglia.text = _modifica(foglia.text.strip())
        modificato = etree.tostring(root, xml_declaration=True, encoding="UTF-8")
        try:
            r = sv.importa_xml_telematico(modificato)
        except Exception:
            continue                                           # errore esplicito: ammesso
        dati = sv.leggi(r["pratica_id"])["dati"]
        dati["documenti_ref"] = originale["documenti_ref"]
        dati["opzioni"]["telematico"]["dichiarazione"]["dichiara_copie_conformi"] = True
        es = esporta_xml(dati, CTX)
        if es.xml is None:
            continue                                           # errore dell'esportazione: ammesso
        if es.xml == _xml(originale):
            silenziosi.append(percorso)
    assert silenziosi == []


def test_nessuna_perdita_nel_quadro_nuovo_in_presenza_di_un_quadro_gia_importato():
    """Regressione: l'elemento non letto dentro EB/EC resta un errore anche con i quadri nuovi presenti."""
    root = etree.fromstring(_xml(caso_titoli()))
    dv = root.xpath("//suc:QuadroEC//suc:Devoluzione", namespaces=NS)[0]
    etree.SubElement(dv, f"{{{SUC}}}Agevolazioni").text = "P"
    with pytest.raises(XmlNonImportabile, match="Agevolazioni"):
        importa_xml(etree.tostring(root))
