"""Quadri EF, EG, EH e prova A10 con il controllo ufficiale SUC13 2.3.1 eseguito IN LOCALE (dati sintetici).

- Senza variabili d'ambiente: il file prodotto oggi dall'export e' confrontato byte per byte con quello registrato
  in tests/fixture_telematico/controllo_20261101/ (sottoposto al componente il 2026-11-01), e i diagnostici originali
  registrati (.dgn/.wri/_logSchema.xml) sono letti con l'adattatore dell'area 3 (``collegamenti.controllo``).
- Con SUCCESSIONI_CONTROLLI_SUC13 (cartella dei 15 JAR): il componente viene rieseguito sul caso base (atteso: nessuno
  scarto) e su due negativi predisposti (atteso: scarto con il messaggio registrato). Il componente usa
  javax.xml.bind.DatatypeConverter per gli allegati EG: serve Java 8 (SUCCESSIONI_JAVA) oppure, con Java >= 11,
  il JAR jaxb-api indicato in SUCCESSIONI_CONTROLLI_CLASSPATH_EXTRA; altrimenti la prova e' saltata con il motivo.

Esito di queste prove: 'controllo locale'. Non e' una trasmissione, non e' una prova con i servizi dell'Agenzia e non
sostituisce il collaudo su Desktop Telematico (Windows).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from lxml import etree

from successioni.collegamenti import controllo as C
from successioni.telematico import fonti, xsd
from successioni.telematico.esporta import esporta_xml
from successioni.telematico.identificativi import genera_cf_sintetico

from telematico_casi import (ALLEGATI_A10, CF_ANNA, IBAN_SINTETICO, caso_a10, caso_completo, contesto,
                             contesto_caso_a10)

FIX = Path(__file__).parent / "fixture_telematico"
REG = FIX / "controllo_20261101"
NS = {"tm": fonti.NS_TM, "suc": fonti.NS_SUC, "reg": fonti.NS_REG}
D = "/tm:Messaggio/tm:Contenuto/suc:Fornitura/suc:Dichiarazione"


def _a10():
    return esporta_xml(caso_a10(), contesto_caso_a10())


def _testi(doc, xp):
    return doc.xpath(xp, namespaces=NS)


# ------------------------------------------------------------------------------------------- export del caso base
def test_caso_a10_completo_e_identico_al_file_controllato():
    es = _a10()
    assert es.errori == [] and es.non_supportato == [] and es.quadri_mancanti == []
    assert es.completo is True and xsd.valida_xsd(es.xml) == []
    # stesso file sottoposto al controllo ufficiale il 2026-11-01 (se cambia l'export va rifatta la registrazione)
    assert es.xml == (REG / "a10_positivo.xml").read_bytes()
    man = json.loads((REG / "manifest.json").read_text(encoding="utf-8"))
    assert man["casi"]["a10_positivo"]["file"]["a10_positivo.xml"] == hashlib.sha256(es.xml).hexdigest()
    doc = etree.fromstring(es.xml)
    caselle = {e.tag.split("}")[1] for e in _testi(doc, f"{D}/suc:Frontespizio/suc:FirmaModello/*")}
    assert caselle == {"CasellaEA", "CasellaEB", "CasellaEC", "CasellaED", "CasellaEE", "CasellaEF", "CasellaEG",
                       "CasellaEH", "CasellaER", "FirmaDichiarante"}


def test_ef_importi_e_fonti():
    es = _a10()
    doc = etree.fromstring(es.xml)
    ef = f"{D}/suc:QuadroEF"
    # immobili: casa 126000 x 1/2 + 1/2, terreno 15000 x 1/2 + 1/2 -> imponibile 141000 (somma dei 'Valore quota')
    assert _testi(doc, f"{ef}/suc:SezioneI_ImpostaIpotecaria/suc:ImpostaProporzionale/*/text()") == ["141000", "2820"]
    assert _testi(doc, f"{ef}/suc:SezioneI_ImpostaIpotecaria/suc:ImpostaIpotecariaDaVersare/text()") == ["2820"]
    assert _testi(doc, f"{ef}/suc:SezioneII_ImpostaCatastale/suc:ImpostaProporzionale/*/text()") == ["141000", "1410"]
    assert _testi(doc, f"{ef}/suc:SezioneIII_TassaIpotecaria/*/text()") == ["1", "120"]
    assert _testi(doc, f"{ef}/suc:SezioneIV_ImpostaBollo/*/text()") == ["1", "85"]
    # due figli sotto franchigia: imposta di successione non dovuta (Fascicolo I p. 47, col. 1)
    assert _testi(doc, f"{ef}/suc:SezioneVBis_ImpostaSuccessione/suc:ImpostaNonDovuta/text()") == ["1"]
    assert _testi(doc, f"{ef}/suc:TotaleDaVersare/text()") == ["4435,00"]
    assert _testi(doc, f"{D}/suc:Frontespizio/suc:ImportoDaVersare/text()") == ["4435,00"]
    assert _testi(doc, f"{D}/suc:Frontespizio/suc:Versamento/*/text()") == [IBAN_SINTETICO, CF_ANNA]
    calcoli = es.mappa["quadro:EF"]["calcoli"]
    assert "p. PDF 40" in calcoli["EF1"]["fonte"] and "p. PDF 44" in calcoli["EF15"]["fonte"]


def test_eg_allegati_dal_modulo_documenti():
    es = _a10()
    doc = etree.fromstring(es.xml)
    eg = f"{D}/suc:QuadroEG"
    assert _testi(doc, f"{eg}/suc:AlberoGenealogico/suc:AlberoGenealogicoNum/text()") == ["1"]
    assert _testi(doc, f"{eg}/suc:DocumentiPassivita/suc:DocumentiPassivitaNum/text()") == ["1"]
    # FileName maiuscolo e senza trattino basso (cm:DatoAN_Type), contenuto identico al file
    assert _testi(doc, f"{eg}/suc:AlberoGenealogico/suc:AlberoGenealogicoAll/reg:FileName/text()") == \
        ["ALBERO-GENEALOGICO.PDF"]
    dati = _testi(doc, f"{eg}/suc:AlberoGenealogico/suc:AlberoGenealogicoAll/reg:ImageData/text()")[0]
    assert base64.b64decode(dati) == Path(ALLEGATI_A10["al_albero"]["percorso"]).read_bytes()
    assert es.mappa["dr_albero1"]["rigo"] == "EG6" and es.mappa["dr_passiv1"]["rigo"] == "EG5"
    assert any(a.codice == "PDFA_NON_VERIFICATO_DALL_EXPORT" for a in es.avvisi)


def test_eh_coerente_con_frontespizio_ed_ea():
    doc = etree.fromstring(_a10().xml)
    s1 = f"{D}/suc:QuadroEH/suc:PrimoModulo/suc:SezioneI_DichSost"
    assert _testi(doc, f"{s1}/suc:Presentatore/suc:CodiceFiscale/text()") == [CF_ANNA]
    assert _testi(doc, f"{s1}/suc:DatiDefunto/suc:Decesso/suc:DataDecesso/text()") == \
        _testi(doc, f"{D}/suc:Frontespizio/suc:DatiDefunto/suc:UlterioriDati/suc:DataDecesso/text()")
    assert _testi(doc, f"{s1}/suc:Eredi/suc:CodiceFiscale/text()") == \
        _testi(doc, f"{D}/suc:QuadroEA/suc:Modulo/suc:Soggetto/suc:CodiceFiscale/text()")
    for flag in ("Dichiarante/suc:PresenzaDichiarante", "Testamento/suc:FlagAssenzaTestamento",
                 "Interdetti/suc:FlagAssenzaInterdetti", "Rinuncia/suc:FlagAssenzaRinuncia", "FlagPassivita",
                 "FirmaDichiarante"):
        assert _testi(doc, f"{s1}/suc:{flag}/text()") == ["1"], flag


# ------------------------------------------------------------------------------- regole che l'export applica gia'
def test_errori_predisposti_rilevati_prima_del_controllo():
    d = caso_a10()
    d["persone"][0]["codice_fiscale"] = "RSSMRA40A01H501W"  # carattere di controllo errato
    es = esporta_xml(d, contesto_caso_a10())
    e = {x.percorso: x for x in es.errori}["persone[p_defunto1].codice_fiscale"]
    assert "carattere di controllo errato (atteso K)" in e.messaggio and "checkCF_PIVA.jar" in e.messaggio

    d = caso_a10()
    for dv in d["devoluzioni"]:
        if dv["bene_id"] == "b_conto001":
            dv["quota"] = {"num": 1, "den": 3} if dv["persona_id"] == "p_anna0001" else {"num": 2, "den": 3}
    es = esporta_xml(d, contesto_caso_a10())
    e = {x.percorso: x for x in es.errori}["beni[b_conto001]"]
    assert e.codice == "QUOTA_DI_LEGGE" and "Allegato 5" in e.fonte and es.xml is None

    d = caso_a10()
    sup = d["opzioni"]["telematico"]["passivita"]["ps_mutuo01"]
    del sup["ripartizione"]
    d["passivita"][1]["persona_id"] = "p_luca0001"  # mutuo (tipo 3) tutto a un figlio: non ammesso per legge
    es = esporta_xml(d, contesto_caso_a10())
    assert {x.codice for x in es.errori} == {"QUOTA_DI_LEGGE"}

    d = caso_a10()
    del d["opzioni"]["telematico"]["dichiarazione"]["versamento"]
    es = esporta_xml(d, contesto_caso_a10())
    assert [x.percorso for x in es.errori] == ["opzioni.telematico.dichiarazione.versamento"]

    es = esporta_xml(caso_a10(), contesto(allegati={}))  # file degli allegati non forniti
    assert {x.codice for x in es.errori} == {"ALLEGATO_NON_DISPONIBILE"}


def test_fornitore_diverso_richiede_documento_identita():
    es = esporta_xml(caso_a10(), contesto_caso_a10(tipo_fornitore="10", cf_fornitore="12345678901",
                                                   impegno_codice="2", data_impegno="2026-10-30"))
    assert es.errori == [] and es.completo is False
    assert [m.percorso for m in es.quadri_mancanti] == ["quadro[EG].DocumentiIdentita"]


def test_ef_casi_fuori_perimetro_non_generati():
    d = caso_a10()  # immobili in due comuni: circoscrizione dall'elenco delle conservatorie (non nelle fonti)
    d["opzioni"]["telematico"]["beni"]["b_terr0001"]["codice_comune"] = "F205"
    es = esporta_xml(d, contesto_caso_a10())
    assert es.completo is False and es.xml is None
    m = [x for x in es.quadri_mancanti if x.percorso == "quadro[EF]"]
    assert m and "conservatorie" in m[0].messaggio and "p. PDF 39" in m[0].fonte

    d = caso_a10()  # soli terreni: regola dei valori fiscali (Fascicolo I p. 40) non coperta
    d["beni"] = [b for b in d["beni"] if b["id"] != "b_casa0001"]
    d["devoluzioni"] = [x for x in d["devoluzioni"] if x["bene_id"] != "b_casa0001"]
    d["passivita"] = [p for p in d["passivita"] if p["id"] != "ps_mutuo01"]
    del d["opzioni"]["telematico"]["beni"]["b_casa0001"], d["opzioni"]["telematico"]["passivita"]["ps_mutuo01"]
    es = esporta_xml(d, contesto_caso_a10())
    assert any("soli terreni" in x.messaggio for x in es.quadri_mancanti if x.percorso == "quadro[EF]")


def test_imposta_dovuta_richiede_tempistica_e_va_nel_totale():
    d = caso_a10()  # conto da 2.400.000: ciascun figlio oltre la franchigia di 1.000.000
    d["beni"][2]["valore"] = "2400000"
    es = esporta_xml(d, contesto_caso_a10())
    assert [x.percorso for x in es.errori] == ["opzioni.telematico.dichiarazione.tempistica_pagamento"]
    d["opzioni"]["telematico"]["dichiarazione"]["tempistica_pagamento"] = "2"
    es = esporta_xml(d, contesto_caso_a10())
    assert es.errori == [] and es.completo
    doc = etree.fromstring(es.xml)
    vbis = f"{D}/suc:QuadroEF/suc:SezioneVBis_ImpostaSuccessione/suc:ImpostaCalcolata"
    imposta = int(_testi(doc, f"{vbis}/suc:Imposta/text()")[0])
    assert imposta == es.mappa["calcolo:EF18bis"]["imposta"] > 10
    assert _testi(doc, f"{D}/suc:QuadroEF/suc:TotaleDaVersare/text()") == [f"{4435 + imposta},00"]


def test_arrotondamento_valore_quota_tre_figli():
    d = caso_completo()
    tel = d["opzioni"]["telematico"]
    pid = "p_carla001"
    d["persone"].append({"id": pid, "_origine": {}, "cognome": "Rossi", "nome": "Carla", "ruolo": "erede",
                         "codice_fiscale": genera_cf_sintetico("Rossi", "Carla", "F", "1974-03-03", "H501"),
                         "data_nascita": "1974-03-03", "luogo_nascita": "Roma"})
    tel["persone"][pid] = {"sesso": "F", "provincia_nascita": "RM", "grado_parentela": "02"}
    d["devoluzioni"] = [{"id": f"d_{b[2:6]}{p[2:6]}", "_origine": {}, "bene_id": b, "persona_id": p, "quota": "1/3",
                         "diritto": "1"} for b in ("b_casa0001", "b_terr0001", "b_conto001")
                        for p in ("p_anna0001", "p_luca0001", pid)]
    tel["passivita"]["ps_mutuo01"]["ripartizione"] = [{"persona_id": p, "quota": "1/3"}
                                                      for p in ("p_anna0001", "p_luca0001", pid)]
    es = esporta_xml(d, contesto(scopo="bozza_tecnica"))
    assert es.errori == [] and es.non_supportato == []
    doc = etree.fromstring(es.xml)
    assert _testi(doc, f"{D}/suc:QuadroER//suc:QuotaValore/text()") == ["6666,67"] * 3
    assert len([a for a in es.avvisi if a.codice == "ARROTONDAMENTO_VALORE_QUOTA"]) == 3


# --------------------------------------------------------------------------- diagnostici originali registrati
ATTESI = {
    "a10_positivo": ("positivo", [("3345", 4)], "La dichiarazione pu"),
    "neg_cf_defunto": ("negativo", [("1013", 16), ("3345", 4)], "Codice fiscale del defunto - Codice Fiscale errato"),
    "neg_importo_da_versare": ("negativo", [("3345", 4), ("3376", 16)], "Importo da versare non ammesso"),
}


def _leggi_registrazione(nome: str) -> tuple[str, dict, str]:
    dgn = C.leggi_dgn(C.decodifica((REG / f"{nome}.dgn").read_bytes()))
    ef = C.leggi_esito_fornitura((REG / f"{nome}_logSchema.xml").read_bytes())
    stato, _ = C.valuta(dgn, ef)
    return stato, dgn, C.decodifica((REG / f"{nome}.wri").read_bytes())


@pytest.mark.parametrize("nome", sorted(ATTESI))
def test_registrazioni_del_controllo_ufficiale(nome):
    man = json.loads((REG / "manifest.json").read_text(encoding="utf-8"))
    for f, h in man["casi"][nome]["file"].items():
        assert hashlib.sha256((REG / f).read_bytes()).hexdigest() == h, f
    stato, dgn, wri = _leggi_registrazione(nome)
    atteso_stato, codici, testo = ATTESI[nome]
    assert stato == atteso_stato
    assert dgn["versione_controllo"] == "2.3.1"
    assert sorted((d["codice"], d["gravita"]) for d in dgn["diagnostici"]) == codici
    assert testo in wri
    if nome == "a10_positivo":
        assert dgn["riepilogo"]["scartate_errori_bloccanti"] == 0 and "scartata" not in wri


# ------------------------------------------------------------------------------ esecuzione reale facoltativa
JAR = os.environ.get("SUCCESSIONI_CONTROLLI_SUC13")
JAVA = os.environ.get("SUCCESSIONI_JAVA") or shutil.which("java")
EXTRA = os.environ.get("SUCCESSIONI_CONTROLLI_CLASSPATH_EXTRA")


def _java_major() -> int | None:
    try:
        r = subprocess.run([JAVA, "-version"], capture_output=True, text=True, timeout=60,
                           env={**os.environ, "JAVA_TOOL_OPTIONS": ""})
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r'version "(\d+)(?:\.(\d+))?', r.stderr)
    if not m:
        return None
    return int(m.group(2)) if m.group(1) == "1" else int(m.group(1))


def _motivo_salto() -> str | None:
    if not JAR or not Path(JAR).is_dir():
        return "componenti del controllo ufficiale non configurati (SUCCESSIONI_CONTROLLI_SUC13)"
    if not JAVA:
        return "Java non trovato (SUCCESSIONI_JAVA)"
    major = _java_major()
    if major is None:
        return "versione di Java non determinabile"
    if major >= 11 and not EXTRA:
        return (f"Java {major}: il componente 2.3.1 usa javax.xml.bind.DatatypeConverter per gli allegati EG (assente "
                "da Java 11): indicare Java 8 in SUCCESSIONI_JAVA oppure jaxb-api in "
                "SUCCESSIONI_CONTROLLI_CLASSPATH_EXTRA")
    return None


def _esegui(xml: bytes, lavoro: Path) -> tuple[str, dict, str, bool]:
    """Stessi comandi di docs/COLLEGAMENTI.md §1; diagnostici letti con collegamenti.controllo."""
    for d in ("in", "out", "tmp"):
        (lavoro / d).mkdir(parents=True, exist_ok=True)
    (lavoro / "in" / "F.xml").write_bytes(xml)
    cp = os.pathsep.join([str(Path(JAR) / "*")] + ([EXTRA] if EXTRA else []))
    env = {**os.environ, "JAVA_TOOL_OPTIONS": ""}
    base = [JAVA, "-Djava.awt.headless=true", f"-Djava.io.tmpdir={lavoro / 'tmp'}", "-cp", cp]
    subprocess.run(base + [C.CLASSE_CONTROLLO, "in/F.xml", "out/F.xml", "out/F.dcm"], cwd=lavoro, env=env,
                   capture_output=True, timeout=600, check=False)
    subprocess.run(base + [C.CLASSE_RAPPORTO, "out/F.dgn", "1"], cwd=lavoro, env=env, capture_output=True,
                   timeout=600, check=False)
    assert (lavoro / "in" / "F.xml").read_bytes() == xml  # il componente non modifica l'ingresso
    dgn = C.leggi_dgn(C.decodifica((lavoro / "out" / "F.dgn").read_bytes()))
    ef = C.leggi_esito_fornitura((lavoro / "out" / "F_logSchema.xml").read_bytes())
    stato, _ = C.valuta(dgn, ef)
    return stato, dgn, C.decodifica((lavoro / "out" / "F.wri").read_bytes()), (lavoro / "out" / "F.dcm").exists()


@pytest.mark.skipif(_motivo_salto() is not None, reason=_motivo_salto() or "")
@pytest.mark.parametrize("nome", sorted(ATTESI))
def test_reale_controllo_ufficiale_locale(nome, tmp_path):
    if nome == "a10_positivo":
        xml = _a10().xml  # il file prodotto ora dall'export
    else:
        xml = (REG / f"{nome}.xml").read_bytes()  # negativo predisposto (registrato)
    stato, dgn, wri, dcm = _esegui(xml, tmp_path)
    atteso_stato, codici, testo = ATTESI[nome]
    assert stato == atteso_stato, (stato, dgn["diagnostici"])
    assert sorted((d["codice"], d["gravita"]) for d in dgn["diagnostici"]) == codici
    assert testo in wri
    assert dcm is (nome == "a10_positivo")
