"""Revisione 2 dell'importazione dei file telematici SUC13 (2026-11-07): tolleranza senza perdite silenziose. Dati SINTETICI
(costruiti dagli export di tests/telematico_casi.py).

Punti: 1 sostitutiva (codice, estremi, imposte versate); 2 quota di possesso decimale (PossessoNumeratore cm:DatoVP_Type);
3 ordine dei righi (avviso invece del rifiuto); 4 agevolazioni/riduzioni delle devoluzioni e sezioni II/IV del quadro EH;
5 vecchio QuadroEI; 6 commenti, istruzioni di elaborazione, contenuto misto, elementi non previsti; 7 valori fuori XSD,
caselle, codici fiscali, input testuale; 8 firma del modello e impegno a trasmettere.
"""
import copy
from datetime import date

import pytest
from lxml import etree

import telematico_casi as T
from successioni.servizio import Servizio, nuovi_dati
from successioni.telematico.esporta import esporta_xml
from successioni.telematico.importa import NS, XmlNonImportabile, importa_xml
from successioni.telematico.xsd import valida_xsd
import test_sostitutiva_vbis as VB

SUC = NS["suc"]
CTX = T.contesto_caso_a10(data_riferimento=date(2025, 9, 1))


def _xml(d, ctx=CTX) -> bytes:
    es = esporta_xml(d, ctx)
    assert es.completo and es.xml, ([e.messaggio for e in es.errori], es.non_supportato, [m.messaggio for m in es.quadri_mancanti])
    return es.xml


def _ricrea(r: dict, orig: dict) -> dict:
    """Pratica ricreata dalle operazioni dell'importazione, con gli allegati (che si riacquisiscono) dell'originale."""
    dati = nuovi_dati()
    for i, op in enumerate(r["operazioni"]):
        Servizio._applica(dati, op, "inserito", "gui", i)
    dati["documenti_ref"] = copy.deepcopy(orig.get("documenti_ref", []))
    dati["opzioni"]["telematico"]["dichiarazione"]["dichiara_copie_conformi"] = True
    return dati


def _andata_ritorno(d, ctx=CTX, xml: bytes | None = None):
    xml = xml or _xml(d, ctx)
    r = importa_xml(xml, data_riferimento=ctx.data_riferimento)
    es = esporta_xml(_ricrea(r, d), ctx)
    return r, xml, es


def _radice(xml: bytes):
    return etree.fromstring(xml)


def _dich_importata(r):
    return next(o for o in r["operazioni"] if o.get("sezione") == "opzioni")["campi"]


# ---------------------------------------------------------------- 1. dichiarazione sostitutiva
@pytest.mark.parametrize("codice", ["1", "2"])
def test_sostitutiva_andata_e_ritorno_identica(codice):
    d = VB.caso(codice, ipotecaria_versata="100", catastale_versata="50", successione_versata="1000")
    ctx = T.contesto_caso_a10(data_riferimento=date(2026, 3, 9))
    r, xml, es = _andata_ritorno(d, ctx)
    opz = _dich_importata(r)
    assert opz["tipo_dichiarazione"] == "sostitutiva"
    dich = opz["telematico"]["dichiarazione"]
    assert {k: dich[k] for k in ("codice_sostitutiva", "prima_anno", "prima_volume", "prima_numero", "ipotecaria_versata",
                                 "catastale_versata", "successione_versata")} == {
        "codice_sostitutiva": codice, "prima_anno": "2026", "prima_volume": "88888", "prima_numero": "123",
        "ipotecaria_versata": "100", "catastale_versata": "50", "successione_versata": "1000"}
    assert es.errori == [] and es.xml == xml
    assert not [a for a in r["avvisi"] if "ImportoDaVersare" in a or "QuadroEF" in a], r["avvisi"]


def test_sostitutiva_codice_non_ammesso_e_doppio_tipo():
    xml = _xml(VB.caso("2"), T.contesto_caso_a10(data_riferimento=date(2026, 3, 9)))
    with pytest.raises(XmlNonImportabile, match="DichiarazioneSostitutiva: codice '4'"):
        importa_xml(xml.replace(b"<suc:DichiarazioneSostitutiva>2<", b"<suc:DichiarazioneSostitutiva>4<"))
    with pytest.raises(XmlNonImportabile, match="entrambe presenti"):
        importa_xml(xml.replace(b"<suc:DichiarazioneSostitutiva>", b"<suc:PrimaDichiarazione>1</suc:PrimaDichiarazione>"
                                                                   b"<suc:DichiarazioneSostitutiva>"))


# ---------------------------------------------------------------- 2. quota di possesso decimale
def _con_possesso(xml: bytes, num: str, den: str) -> bytes:
    root = _radice(xml)
    p = root.xpath("//suc:QuadroEC//suc:Fabbricati/suc:Possesso", namespaces=NS)[0]
    p.find(f"{{{SUC}}}PossessoNumeratore").text = num
    p.find(f"{{{SUC}}}PossessoDenominatore").text = den
    return etree.tostring(root)


def test_quota_decimale_convertita_esattamente_e_riesportata_valida():
    d = T.caso_a10()
    xml = _con_possesso(_xml(d), "20,66", "100")
    r = importa_xml(xml, data_riferimento=CTX.data_riferimento)
    bene = next(o["campi"] for o in r["operazioni"] if o.get("coll") == "beni" and o["campi"]["tipo"] == "fabbricato")
    assert bene["quota_defunto"] == {"num": 2066, "den": 10000}
    assert any("20,66/100 con numeratore decimale importata come 2066/10000" in a and "2066,00/10000" in a for a in r["avvisi"])
    es = esporta_xml(_ricrea(r, d), CTX)
    assert es.xml is not None and es.errori == [], es.errori
    assert valida_xsd(es.xml) == []                     # il testo riprodotto e' accettato dall'XSD
    assert b"<suc:PossessoNumeratore>2066,00</suc:PossessoNumeratore>" in es.xml
    assert b"<suc:PossessoDenominatore>10000</suc:PossessoDenominatore>" in es.xml


@pytest.mark.parametrize("num,den,motivo", [("1,00", "0", "denominatore zero"), ("3,00", "2", "maggiore del denominatore"),
                                            ("0,00", "1", "nulla"), ("1,234567", "999", "al massimo 6 cifre"),
                                            ("-1,00", "2", "numero non valido"), ("1E2", "1000", "numero non valido")])
def test_quota_fuori_dominio_e_un_errore(num, den, motivo):
    with pytest.raises(XmlNonImportabile, match=motivo):
        importa_xml(_con_possesso(_xml(T.caso_a10()), num, den))


def test_quota_decimale_ridotta_se_il_denominatore_supera_sei_cifre():
    r = importa_xml(_con_possesso(_xml(T.caso_a10()), "12,50", "100000"))
    bene = next(o["campi"] for o in r["operazioni"] if o.get("coll") == "beni" and o["campi"]["tipo"] == "fabbricato")
    assert bene["quota_defunto"] == {"num": 1, "den": 8000}          # 1250/10000000 ridotta


# ---------------------------------------------------------------- 3. ordine dei righi
def test_fabbricati_in_ordine_diverso_avviso_e_riesportazione_nell_ordine_dell_export():
    d = T.caso_a10()
    T.aggiungi_fabbricato(d, "b_casa0002", "C2", "5000", "9")
    xml = _xml(d)
    root = _radice(xml)
    mod = root.xpath("//suc:QuadroEC/suc:Modulo", namespaces=NS)[0]
    primo = mod.xpath("suc:Fabbricati", namespaces=NS)[0]
    mod.remove(primo)
    mod.append(primo)
    for pc in root.xpath("//suc:QuadroED//suc:ProgressivoCespite[suc:Quadro='EC']", namespaces=NS):
        pc.find(f"{{{SUC}}}Rigo").text = "2"          # un file coerente aggiorna il riferimento del quadro ED al rigo spostato
    scambiato = etree.tostring(root, xml_declaration=True, encoding="UTF-8")
    r, _, es = _andata_ritorno(d, xml=scambiato)
    assert any(a.startswith("QuadroEC: i righi del file non sono nell'ordine") and "2 beni su 2" in a for a in r["avvisi"])
    assert es.errori == [] and es.xml == xml          # la riesportazione riscrive i righi nel proprio ordine


def test_titoli_riordinati_riesportazione_identica_all_export():
    d = T.caso_titoli()
    xml = _xml(d)
    root = _radice(xml)
    mod = root.xpath("//suc:QuadroEO/suc:Modulo", namespaces=NS)[0]
    primo = mod.xpath("suc:Titoli", namespaces=NS)[0]
    mod.remove(primo)
    mod.append(primo)
    r, _, es = _andata_ritorno(d, xml=etree.tostring(root))
    assert any(a.startswith("QuadroEO: i righi del file") for a in r["avvisi"])
    assert es.errori == [] and es.xml == xml


# ---------------------------------------------------------------- 4. agevolazioni e riduzioni, quadro EH
def test_prima_casa_andata_e_ritorno_identica():
    d = T.caso_prima_casa()
    r, xml, es = _andata_ritorno(d)
    tel = _dich_importata(r)["telematico"]
    assert list(tel["devoluzioni"].values()) == [{"agevolazioni": "P"}]
    assert tel["dichiarazione"]["prima_casa"] == T.PRIMA_CASA_DICH
    assert not any("SezioneII" in n for n in r["non_importato"]), r["non_importato"]
    assert es.errori == [] and es.xml == xml


def test_sezione_ii_eh_diversa_dalla_ricostruita_e_un_avviso():
    xml = _xml(T.caso_prima_casa())
    root = _radice(xml)
    f = root.xpath("//suc:SezioneII_AgevPrimaCasa/suc:ImmobilePrincipale//reg:Foglio", namespaces=NS)[0]
    f.text = "999"
    r = importa_xml(etree.tostring(root), data_riferimento=CTX.data_riferimento)
    assert any(a.startswith("QuadroEH SezioneII_AgevPrimaCasa riesportata diversa dall'originale") and "999" in a
               for a in r["avvisi"]), r["avvisi"]


def test_riduzioni_della_devoluzione_importate():
    root = _radice(_xml(T.caso_a10()))
    dv = root.xpath("//suc:QuadroEC//suc:Devoluzione", namespaces=NS)[0]
    etree.SubElement(dv, f"{{{SUC}}}Riduzioni").text = "1"
    tel = _dich_importata(importa_xml(etree.tostring(root)))["telematico"]
    assert list(tel["devoluzioni"].values()) == [{"riduzioni": "1"}]


# ---------------------------------------------------------------- 5. quadro EI del modello precedente
def test_vecchio_quadro_ei_altri_quadri_importati_e_contenuto_elencato():
    xml = _xml(T.caso_voltura()).replace(b"QuadroEI_new", b"QuadroEI")
    r = importa_xml(xml)
    assert r["importato"]["fabbricati"] == 1 and r["importato"]["terreni"] == 1 and "voltura" not in r["importato"]
    voce = next(n for n in r["non_importato"] if n.startswith("QuadroEI (modello precedente"))
    assert "RegistroParticolare = 12345" in voce
    assert any("QuadroEI del modello precedente" in a for a in r["avvisi"])
    assert any("va completata con gli estremi del quadro EI precedente" in a for a in r["avvisi"])


# ---------------------------------------------------------------- 6. commenti, istruzioni di elaborazione, contenuto misto
def test_commenti_e_pi_non_troncano_il_valore():
    xml = _xml(T.caso_a10()).replace(f"<suc:CodiceFiscaleDefunto>{T.CF_DEFUNTO}".encode(),
                                     f"<suc:CodiceFiscaleDefunto>{T.CF_DEFUNTO[:8]}<!-- nota -->{T.CF_DEFUNTO[8:12]}"
                                     f"<?elab x?>{T.CF_DEFUNTO[12:]}".encode())
    r = importa_xml(xml)
    defunto = next(o["campi"] for o in r["operazioni"] if o.get("id") == "p_defunto1")
    assert defunto["codice_fiscale"] == T.CF_DEFUNTO
    assert any(a.startswith("2 commenti o istruzioni di elaborazione tolti") for a in r["avvisi"])


def test_foglia_con_solo_commento_non_sfugge_al_controllo():
    # prima: un commento rendeva l'elemento «non foglia» (len > 0) e il valore sfuggiva al controllo «mai scartato in silenzio»
    root = _radice(_xml(T.caso_a10()))
    dv = root.xpath("//suc:QuadroEC//suc:Devoluzione", namespaces=NS)[0]
    e = etree.SubElement(dv, f"{{{SUC}}}ElementoNonLetto")
    e.append(etree.Comment("c"))
    e[0].tail = "X"
    with pytest.raises(XmlNonImportabile, match="ElementoNonLetto"):
        importa_xml(etree.tostring(root))


def test_contenuto_misto_e_un_errore():
    root = _radice(_xml(T.caso_a10()))
    q = root.xpath("//suc:QuadroEC//suc:Devoluzione/suc:Quota", namespaces=NS)[0]
    q.text = "testo vagante"
    with pytest.raises(XmlNonImportabile, match="contenuto misto"):
        importa_xml(etree.tostring(root))


def test_elemento_non_quadro_nella_dichiarazione_elencato():
    root = _radice(_xml(T.caso_a10()))
    d = root.xpath("//suc:Dichiarazione", namespaces=NS)[0]
    x = etree.SubElement(d, f"{{{SUC}}}Annotazioni")
    etree.SubElement(x, f"{{{SUC}}}Nota").text = "dato estraneo"
    r = importa_xml(etree.tostring(root))
    assert any(n.startswith("Annotazioni: elemento non previsto nella dichiarazione") and "Nota = dato estraneo" in n
               for n in r["non_importato"]), r["non_importato"]


# ---------------------------------------------------------------- 7. valori fuori XSD, caselle, CF, input testuale
@pytest.mark.parametrize("elemento", ["DevoluzionePerLegge", "PrimaDichiarazione"])
def test_casella_con_valore_non_ammesso_e_un_errore(elemento):
    xml = _xml(T.caso_a10())
    assert f"<suc:{elemento}>1<".encode() in xml
    with pytest.raises(XmlNonImportabile, match=f"{elemento}: casella con valore '2'"):
        importa_xml(xml.replace(f"<suc:{elemento}>1<".encode(), f"<suc:{elemento}>2<".encode()))


def test_firma_dichiarante_non_ammessa_e_zero_con_avviso():
    xml = _xml(T.caso_a10())
    root = _radice(xml)
    root.xpath("//suc:FirmaModello/suc:FirmaDichiarante", namespaces=NS)[0].text = "si"
    with pytest.raises(XmlNonImportabile, match="FirmaModello/FirmaDichiarante: casella con valore 'si'"):
        importa_xml(etree.tostring(root))
    r = importa_xml(xml.replace(b"<suc:DevoluzionePerLegge>1<", b"<suc:DevoluzionePerLegge>0<"))
    assert any("DevoluzionePerLegge: casella con valore 0" in a for a in r["avvisi"])


@pytest.mark.parametrize("valore", ["1E3", "-1000", "1 000", "1.000,00"])
def test_numero_fuori_tracciato_e_un_errore(valore):
    root = _radice(_xml(T.caso_a10()))
    root.xpath("//suc:QuadroEC//suc:Fabbricati/suc:Valore", namespaces=NS)[0].text = valore
    with pytest.raises(XmlNonImportabile, match="numero non valido"):
        importa_xml(etree.tostring(root))


def test_codice_fiscale_minuscolo_normalizzato_e_duplicato_in_ea_rifiutato():
    xml = _xml(T.caso_a10())
    r = importa_xml(xml.replace(f">{T.CF_ANNA}<".encode(), f">{T.CF_ANNA.lower()}<".encode()))
    cf = [o["campi"].get("codice_fiscale") for o in r["operazioni"] if o.get("coll") == "persone"]
    assert T.CF_ANNA in cf and T.CF_ANNA.lower() not in cf
    with pytest.raises(XmlNonImportabile, match="codice fiscale gia' presente nel quadro EA con lo stesso tipo"):
        importa_xml(xml.replace(f">{T.CF_LUCA}<".encode(), f">{T.CF_ANNA}<".encode()))


def test_testo_con_dichiarazione_di_codifica():
    xml = _xml(T.caso_a10())
    with pytest.raises(XmlNonImportabile, match="dichiarazione di codifica"):
        importa_xml(xml.decode("utf-8"))
    senza = xml.decode("utf-8").split("?>", 1)[1]
    assert importa_xml(senza)["importato"]["eredi"] == 2


# ---------------------------------------------------------------- 8. firma del modello e impegno a trasmettere
def test_impegno_a_trasmettere_elencato_non_scartato():
    root = _radice(_xml(T.caso_a10()))
    fr = root.xpath("//suc:Frontespizio", namespaces=NS)[0]
    imp = etree.SubElement(fr, f"{{{SUC}}}ImpegnoATrasmettere")
    for tag, v in (("CFintermediario", "12345678903"), ("ImpegnoATrasmettere", "1"), ("DataImpegno", "01022026"),
                   ("FirmaIntermediario", "1")):
        etree.SubElement(imp, f"{{{NS['reg']}}}{tag}").text = v
    r = importa_xml(etree.tostring(root))
    voce = next(n for n in r["non_importato"] if n.startswith("Frontespizio ImpegnoATrasmettere"))
    assert "impostazioni locali" in voce and "CFintermediario = 12345678903" in voce and "DataImpegno = 01022026" in voce


# ---------------------------------------------------------------- altri dati che l'esportazione scrive e l'importazione ora legge
# (emersi dai file reali dello studio: residenza estera e rappresentazione in EA, beneficio d'inventario, beni esteri)
@pytest.mark.parametrize("nome", ["legge", "opzione", "inventario", "res1", "res2"])
def test_caselle_del_frontespizio_andata_e_ritorno(nome):
    import test_frontespizio as FR
    d = FR.caso_casella(nome)
    cf = d["opzioni"]["telematico"]["dichiarazione"]["versamento"]["cf_titolare"]
    ctx = T.contesto_caso_a10(cf_fornitore=cf, data_riferimento=FR.TEMPESTIVO)
    r, xml, es = _andata_ritorno(d, ctx)
    assert es.errori == [] and es.xml == xml, (es.errori, es.non_supportato)


def test_residenza_estera_del_soggetto_ea_andata_e_ritorno():
    import test_soggetti_ea as SE
    d = SE.caso_estero("029", "FRANCIA")
    r, xml, es = _andata_ritorno(d, T.contesto_caso_a10())
    assert es.errori == [] and es.xml == xml, (es.errori, es.non_supportato)


def test_bene_estero_er_andata_e_ritorno():
    import test_beni_esteri as BE
    d = T.caso_a10()
    er = next(b for b in d["beni"] if b["id"] == "b_conto001")
    er["bene_estero"], er["imposta_estera"] = "1", "400"
    BE.con_certificazione(d)
    r, xml, es = _andata_ritorno(d, BE.ctx())
    assert es.errori == [] and es.xml == xml, (es.errori, es.non_supportato)


@pytest.mark.parametrize("codici,eh", [({"d_terranna": "A"}, "EH_A"), ({"d_terranna": "C"}, "EH_FLAG"),
                                       ({"d_casaanna": "D"}, "EH_FLAG")])
def test_agevolazioni_e_sezione_iv_eh_andata_e_ritorno(codici, eh):
    import test_agevolazioni as AGT
    d = AGT.caso(codici, {"riduzioni_art25": getattr(AGT, eh)})
    r, xml, es = _andata_ritorno(d, T.contesto_caso_a10())
    tel = _dich_importata(r)["telematico"]
    assert sorted(v["agevolazioni"] for v in tel["devoluzioni"].values()) == sorted(codici.values())
    assert tel["dichiarazione"]["riduzioni_art25"] == getattr(AGT, eh)
    assert es.errori == [] and es.xml == xml, (es.errori, es.non_supportato)
