"""Controllo ufficiale SUC13 (area 3).

- I lettori del diagnostico sono provati su REGISTRAZIONI di esecuzioni reali del componente ufficiale 2.3.1 su file
  sintetici (src/successioni/collegamenti/fixture/controllo_reale_20261101/manifest.json).
- L'adattatore con esecutore iniettato produce sempre l'esito `simulazione`, anche con diagnostici veri o positivi.
- `test_reale_*` esegue il JAR ufficiale solo se SUCCESSIONI_CONTROLLI_SUC13 punta ai JAR (altrimenti e' saltato).
"""
import json
import os
import shutil
from pathlib import Path

import pytest

import successioni.collegamenti.controllo as C
from successioni.archivio import Archivio
from successioni.collegamenti.base import Esito
from successioni.errori import DatiNonValidi

FIX = Path(C.__file__).parent / "fixture" / "controllo_reale_20261101"

# SIMULAZIONE: diagnostico positivo costruito a mano secondo il tracciato dedotto da Visual.coda (nessun record di
# errore; riepilogo: 1 elaborata, 1 senza segnalazioni). NON e' un'uscita del componente ufficiale.
DGN_POSITIVO_SIMULATO = (
    "0USUC1301" + " " * 50 + "2.3.1   11/03/2026" + " " * 28 + "\n"
    "0" + "*" * 16 + " " * 69 + "in/x.xml" + "\n"
    "9     1     1     0     0     0     0     0" + " " * 62 + "\n")
LOG_VALIDO = (FIX / "frontespizio_logSchema.xml").read_bytes()


def leggi(n):
    return (FIX / n).read_bytes()


# ----------------------------------------------------------------------------------- lettori
def test_jar_richiesti_dal_jnlp_ufficiale():
    jar = C.jar_richiesti()
    assert len(jar) == 15 and jar[0] == "controlliXMLREG2013.jar"
    assert {"Supporto.jar", "ResSUC13.jar", "SUCdom.jar", "esito.jar"} <= set(jar)
    assert "calcoloHash.jar" not in jar  # commentato nel JNLP


def test_simboli_gravita_come_visual_impostaasterischi():
    assert [C.simbolo_gravita(g) for g in (4, 8, 12, 14, 15, 16, 23, 24, 30, 0)] == [
        "(*)", "(**)", "(**E)", "(***C)", "(***)", "(***)", "(***)", "(****)", "(****)", ""]


def test_dgn_reale_frontespizio_incompleto():
    d = C.leggi_dgn(C.decodifica(leggi("frontespizio.dgn")))
    assert d["versione_controllo"] == "2.3.1" and d["data_versione"] == "11/03/2026"
    assert d["riepilogo"]["elaborate"] == 1 and d["riepilogo"]["scartate_errori_bloccanti"] == 1
    assert len(d["diagnostici"]) == 8 and not d["righe_non_riconosciute"]
    simboli = [x["simbolo"] for x in d["diagnostici"]]
    assert simboli.count("(***)") == 7 and simboli.count("(*)") == 1
    cf = next(x for x in d["diagnostici"] if x["campo"] == "XXB02")
    assert cf["codice"] == "1013" and cf["valori"] == ["BBBBBB00B00B000B"] and cf["identificativo"] == "00001"


def test_dgn_reale_fornitura_non_valida():
    d = C.leggi_dgn(C.decodifica(leggi("minimo.dgn")))
    assert d["diagnostici"][0]["simbolo"] == "(****)" and d["riepilogo"]["elaborate"] == 0
    ef = C.leggi_esito_fornitura(leggi("minimo_logSchema.xml"))
    assert ef["conforme_xsd"] is True  # l'uscita ufficiale rispetta esitoFornitura_v3.xsd delle fonti
    assert ef["esito_xsd"]["valido"] is False
    assert "TipoFornitore" in ef["esito_xsd"]["diagnostici"][0]["Message"]
    stato, motivi = C.valuta(d, ef)
    assert stato == "negativo" and any("schema" in m for m in motivi)


def test_wri_reale_e_coerenza_con_dgn():
    w = C.leggi_wri(C.decodifica(leggi("frontespizio.wri")))
    assert w["versione_controllo"] == "2.3.1"
    assert w["riepilogo"]["elaborate"] == 1 and w["riepilogo"]["scartate_errori_bloccanti"] == 1
    testi = [b["testo"] for b in w["blocchi"]]
    assert "Quadro EG obbligatorio" in testi and len(w["blocchi"]) == 8
    d = C.leggi_dgn(C.decodifica(leggi("frontespizio.dgn")))
    assert all(d["riepilogo"][k] == v for k, v in w["riepilogo"].items())


def test_valuta_positivo_simulato_e_casi_limite():
    d = C.leggi_dgn(DGN_POSITIVO_SIMULATO)
    assert d["riepilogo"]["senza_segnalazioni"] == 1
    assert C.valuta(d, C.leggi_esito_fornitura(LOG_VALIDO)) == ("positivo", [])
    assert C.valuta(None, None)[0] == "non_verificabile"
    assert C.valuta(None, C.leggi_esito_fornitura(LOG_VALIDO))[0] == "non_verificabile"


# ----------------------------------------------------------------------------------- adattatore
def ambiente_finto(tmp_path) -> C.ConfigControllo:
    cart = tmp_path / "jar"
    cart.mkdir()
    for n in C.jar_richiesti():
        (cart / n).write_bytes(b"finto " + n.encode())
    return C.ConfigControllo(java="java-finto", cartella_jar=cart, timeout_s=5)


class EsecutoreFinto:
    """Sostituisce Java: copia nella cartella di lavoro i file indicati (registrazioni o simulazioni)."""

    def __init__(self, dgn: bytes | None, log: bytes | None, wri: bytes | None = None, scaduto=False):
        self.dgn, self.log, self.wri, self.scaduto = dgn, log, wri, scaduto
        self.chiamate = []

    def __call__(self, argv, cwd, timeout):
        self.chiamate.append(argv)
        if argv[1:] == ["-version"]:
            return C.Processo(0, b"", b'openjdk version "finto"', 0.01)
        if C.CLASSE_CONTROLLO in argv:
            uscita = Path(cwd) / argv[argv.index(C.CLASSE_CONTROLLO) + 2]
            if self.scaduto:
                return C.Processo(None, b"", b"", timeout, scaduto=True)
            if self.dgn:
                uscita.with_suffix(".dgn").write_bytes(self.dgn)
            if self.log:
                (uscita.parent / (uscita.stem + "_logSchema.xml")).write_bytes(self.log)
            return C.Processo(0, b"end EsitoControllo\n", b"Caused by: java.lang.NoClassDefFoundError: "
                                                          b"javax/annotation/PostConstruct\n", 0.5)
        if C.CLASSE_RAPPORTO in argv and self.wri:
            (Path(cwd) / argv[argv.index(C.CLASSE_RAPPORTO) + 1]).with_suffix(".wri").write_bytes(self.wri)
        return C.Processo(0, b"Esecuzione .Fine\n", b"", 0.1)


@pytest.fixture
def arch(tmp_path):
    return Archivio(tmp_path / "dati")


def test_adattatore_con_esecutore_finto_e_sempre_simulazione(arch, tmp_path):
    es = EsecutoreFinto(leggi("frontespizio.dgn"), leggi("frontespizio_logSchema.xml"), leggi("frontespizio.wri"))
    ctl = C.ControlloJar(arch, ambiente_finto(tmp_path), esecutore=es)
    r = ctl.esegui(FIX / "frontespizio.xml", pratica_id="pr_1", impronta_dichiarativa="i1", chiave="c1")
    assert r.esito is Esito.SIMULAZIONE and r.stato == "completato"
    assert r.dettaglio["stato_controllo"] == "negativo"
    j = ctl.job.leggi(r.job_id)["risultato"]
    assert j["versione_controllo"] == "2.3.1" and j["riepilogo"]["scartate_errori_bloccanti"] == 1
    assert any("print-model" in a for a in j["avvertenze"])
    ruoli = {a["ruolo"] for a in r.artefatti}
    assert {"input_controllo", "diagnostico_dgn", "esito_schema", "rapporto_wri", "stdout_controllo"} <= ruoli
    assert j["ambiente"]["jar"][0]["nome"] == "controlliXMLREG2013.jar" and len(j["ambiente"]["jar"]) == 15
    # cartella di lavoro rimossa: il nome reale e' <job_id>-<uuid> (registrato in cartella_lavoro)
    assert j["cartella_lavoro"].startswith(f"lavoro/controlli/{r.job_id}-")
    assert not (arch.base / j["cartella_lavoro"]).exists()
    assert not list((arch.base / "lavoro" / "controlli").glob(r.job_id + "*"))
    n = len(es.chiamate)
    r2 = ctl.esegui(FIX / "frontespizio.xml", pratica_id="pr_1", impronta_dichiarativa="i1", chiave="c1")
    assert r2.job_id == r.job_id and len(es.chiamate) == n  # richiesta ripetuta: nessuna nuova esecuzione


def test_positivo_simulato_non_diventa_mai_passato(arch, tmp_path):
    es = EsecutoreFinto(DGN_POSITIVO_SIMULATO.encode(), LOG_VALIDO)
    r = C.ControlloJar(arch, ambiente_finto(tmp_path), esecutore=es).esegui(FIX / "frontespizio.xml")
    assert r.dettaglio["stato_controllo"] == "positivo" and r.esito is Esito.SIMULAZIONE


def test_dcm_consumo_copia_lavoro_non_perde_input_originale(arch, tmp_path):
    class ConsumaCopia(EsecutoreFinto):
        def __call__(self, argv, cwd, timeout):
            p = super().__call__(argv, cwd, timeout)
            if C.CLASSE_CONTROLLO in argv:
                i = argv.index(C.CLASSE_CONTROLLO)
                (Path(cwd) / argv[i + 3]).write_bytes(b'DCM sintetico')
                (Path(cwd) / argv[i + 1]).unlink()
            return p

    originale = (FIX / 'frontespizio.xml').read_bytes()
    ctl = C.ControlloJar(arch, ambiente_finto(tmp_path), esecutore=ConsumaCopia(DGN_POSITIVO_SIMULATO.encode(), LOG_VALIDO))
    r = ctl.esegui(FIX / 'frontespizio.xml', produci_dcm=True)
    assert r.stato == 'completato' and r.esito is Esito.SIMULAZIONE
    reg = ctl.job.leggi(r.job_id)['risultato']
    assert reg['copia_lavoro_consumata'] and reg['input_deposito_invariato']
    assert not reg['input_modificato_dal_componente']
    art = next(a for a in r.artefatti if a['ruolo'] == 'input_controllo')
    assert ctl.deposito.leggi(art) == originale


def test_tempo_scaduto_non_verificabile(arch, tmp_path):
    r = C.ControlloJar(arch, ambiente_finto(tmp_path), esecutore=EsecutoreFinto(None, None, scaduto=True)).esegui(
        FIX / "frontespizio.xml")
    assert r.stato == "errore_esecuzione" and r.dettaglio["stato_controllo"] == "non_verificabile"


def test_componente_assente_passaggio_manuale_tracciato(arch, tmp_path):
    cfg = C.ConfigControllo(java=None, cartella_jar=tmp_path / "manca")
    ctl = C.ControlloJar(arch, cfg)
    r = ctl.esegui(FIX / "frontespizio.xml", pratica_id="pr_1")
    assert r.esito is Esito.DA_COLLAUDARE and r.stato == "attesa_diagnostico"
    assert C.ENV_JAR in r.azione_richiesta and "Requisito di automazione" in r.azione_richiesta
    assert r.dettaglio["stato_controllo"] == "non_eseguito"
    # l'utente esegue il controllo ufficiale e registra i file originali prodotti (qui: la registrazione reale del
    # 2026-11-01: il .wri e' datato prima del job di oggi e viene rifiutato come esito di un'esportazione precedente)
    with pytest.raises(DatiNonValidi, match="prima dell'esportazione"):
        ctl.registra_diagnostico(r.job_id, dgn=leggi("frontespizio.dgn"), log_schema=leggi(
            "frontespizio_logSchema.xml"), wri=leggi("frontespizio.wri"), ambiente_dichiarato={"os": "Windows 11"})
    # il .dgn registrato nomina la copia di lavoro di un controllo di un altro archivio: nome non riconosciuto, il CF
    # del defunto da solo non basta -> serve la conferma esplicita
    with pytest.raises(DatiNonValidi, match="conferma"):
        ctl.registra_diagnostico(r.job_id, dgn=leggi("frontespizio.dgn"), log_schema=leggi(
            "frontespizio_logSchema.xml"), wri=leggi("frontespizio.wri"), non_prima_di="2026-11-01T09:00:00+00:00")
    r2 = ctl.registra_diagnostico(r.job_id, dgn=leggi("frontespizio.dgn"), log_schema=leggi(
        "frontespizio_logSchema.xml"), wri=leggi("frontespizio.wri"), ambiente_dichiarato={"os": "Windows 11"},
        non_prima_di="2026-11-01T09:00:00+00:00",   # file corrente esportato il giorno del controllo
        conferma_associazione=True)
    assert r2.stato == "completato" and r2.esito is Esito.FALLITO and r2.dettaglio["stato_controllo"] == "negativo"
    j = ctl.job.leggi(r.job_id)["risultato"]
    assert j["modalita"] == "manuale_tracciato" and j["requisito_automazione"] == "aperto"


def test_manuale_rifiuta_diagnostico_di_un_altro_file(arch, tmp_path):
    altro = tmp_path / "altro.xml"
    altro.write_bytes(leggi("frontespizio.xml").replace(b"<suc:CodiceFiscaleDefunto>BBBBBB00B00B000B",
                                                        b"<suc:CodiceFiscaleDefunto>ZZZZZZ00Z00Z000Z"))
    ctl = C.ControlloManuale(arch)
    r = ctl.esegui(altro)
    assert r.esito is Esito.DA_COLLAUDARE
    with pytest.raises(DatiNonValidi):
        ctl.registra_diagnostico(r.job_id, dgn=leggi("frontespizio.dgn"), log_schema=LOG_VALIDO)
    assert ctl.leggi(r.job_id).stato == "attesa_diagnostico"


def test_manuale_diagnostico_senza_riferimenti_richiede_conferma_e_non_e_passato(arch):
    ctl = C.ControlloManuale(arch)
    r = ctl.esegui(FIX / "frontespizio.xml")
    # SIMULAZIONE: diagnostico positivo senza record e con un nome di file diverso nell'intestazione
    with pytest.raises(DatiNonValidi):
        ctl.registra_diagnostico(r.job_id, dgn=DGN_POSITIVO_SIMULATO.encode(), log_schema=LOG_VALIDO)
    r2 = ctl.registra_diagnostico(r.job_id, dgn=DGN_POSITIVO_SIMULATO.encode(), log_schema=LOG_VALIDO,
                                  conferma_associazione=True)
    assert r2.dettaglio["stato_controllo"] == "positivo" and r2.esito is Esito.DA_COLLAUDARE
    # con il nome giusto nell'intestazione l'associazione e' verificata dal contenuto. LIMITE (documentato): il
    # percorso manuale si fida dei file originali forniti dall'utente; un .dgn alterato non e' riconoscibile.
    r3 = ctl.esegui(FIX / "frontespizio.xml", chiave="altro")
    dgn = DGN_POSITIVO_SIMULATO.replace("in/x.xml", "in/frontespizio.xml")
    assert ctl.registra_diagnostico(r3.job_id, dgn=dgn.encode(), log_schema=LOG_VALIDO).esito is Esito.PASSATO


def test_fabbrica_sceglie_la_modalita(arch, tmp_path):
    assert isinstance(C.controllo_ufficiale(arch, C.ConfigControllo(java=None)), C.ControlloManuale)
    assert isinstance(C.controllo_ufficiale(arch, ambiente_finto(tmp_path)), C.ControlloJar)


def test_registrazione_reale_documentata():
    m = json.loads((FIX / "manifest.json").read_text(encoding="utf-8"))
    assert m["casi"]["frontespizio"]["versione_controllo"] == "2.3.1"
    assert len(m["ambiente"]["jar"]) == 15 and "openjdk" in m["ambiente"]["java"].lower()


# ----------------------------------------------------------------------------- prova reale facoltativa
@pytest.mark.skipif(not os.environ.get(C.ENV_JAR) or not shutil.which(os.environ.get(C.ENV_JAVA) or "java"),
                    reason="JAR del controllo SUC13 non configurati (SUCCESSIONI_CONTROLLI_SUC13)")
@pytest.mark.java
def test_reale_controllo_ufficiale_su_file_sintetico(arch):
    ctl = C.ControlloJar(arch)
    assert ctl.diagnostica()["pronto"], ctl.diagnostica()["problemi"]
    r = ctl.esegui(FIX / "frontespizio.xml")
    j = ctl.job.leggi(r.job_id)["risultato"]
    assert r.esito is Esito.FALLITO and j["stato_controllo"] == "negativo"
    assert j["versione_controllo"] == "2.3.1" and j["riepilogo"]["scartate_errori_bloccanti"] == 1
    assert j["input_modificato_dal_componente"] is False and j["esito_fornitura"]["conforme_xsd"] is True
